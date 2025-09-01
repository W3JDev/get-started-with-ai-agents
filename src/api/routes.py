# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

import json
import logging
import os
import secrets
import uuid
from collections.abc import AsyncGenerator
from typing import Optional

import fastapi
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from services.azure_openai_service import AzureOpenAIService
from services.blob_storage_service import BlobStorageService
from services.cosmos_db_service import CosmosDBService
from services.rag_service import RAGService

# Create a logger for this module
logger = logging.getLogger("azureaiapp")

# Set the log level for the azure HTTP logging policy to WARNING (or ERROR)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

tracer = trace.get_tracer(__name__)

# Define the directory for your templates.
directory = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=directory)

# Create a new FastAPI router
router = fastapi.APIRouter()

security = HTTPBasic()

username = os.getenv("WEB_APP_USERNAME")
password = os.getenv("WEB_APP_PASSWORD")
basic_auth = username and password

def authenticate(credentials: Optional[HTTPBasicCredentials] = Depends(security)) -> None:

    if not basic_auth:
        logger.info("Skipping authentication: WEB_APP_USERNAME or WEB_APP_PASSWORD not set.")
        return
    
    correct_username = secrets.compare_digest(credentials.username, username)
    correct_password = secrets.compare_digest(credentials.password, password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return

auth_dependency = Depends(authenticate) if basic_auth else None


def get_openai_service(request: Request) -> AzureOpenAIService:
    return request.app.state.openai_service

def get_cosmos_service(request: Request) -> CosmosDBService:
    return request.app.state.cosmos_service

def get_blob_service(request: Request) -> BlobStorageService:
    return request.app.state.blob_service

def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service

def get_app_insights_conn_str(request: Request) -> str:
    if hasattr(request.app.state, "application_insights_connection_string"):
        return request.app.state.application_insights_connection_string
    else:
        return None

def serialize_sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, _ = auth_dependency):
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
        }
    )


async def chat_stream_response(
    user_message: str,
    thread_id: str,
    rag_service: RAGService,
    cosmos_service: CosmosDBService,
    carrier: dict[str, str]
) -> AsyncGenerator[str, None]:
    """Stream chat response using RAG service."""
    ctx = TraceContextTextMapPropagator().extract(carrier=carrier)
    with tracer.start_as_current_span('chat_stream_response', context=ctx):
        logger.info(f"Processing chat request for thread_id={thread_id}")
        try:
            # Get conversation history
            conversation_history = await cosmos_service.get_messages(thread_id)
            
            # Add user message to conversation
            user_msg = {
                "role": "user",
                "content": user_message
            }
            await cosmos_service.add_message(thread_id, user_msg)
            
            # Yield user message confirmation
            yield serialize_sse_event({
                'type': 'user_message',
                'content': user_message
            })
            
            # Generate response using RAG
            response_text = await rag_service.generate_response_with_context(
                user_message, conversation_history
            )
            
            # Add assistant response to conversation
            assistant_msg = {
                "role": "assistant", 
                "content": response_text
            }
            await cosmos_service.add_message(thread_id, assistant_msg)
            
            # Yield assistant response
            yield serialize_sse_event({
                'type': 'completed_message',
                'content': response_text,
                'annotations': []  # Keep compatibility with frontend
            })
            
            # Yield stream end
            yield serialize_sse_event({'type': "stream_end"})
            
        except Exception as e:
            logger.exception(f"Exception in chat stream: {e}")
            yield serialize_sse_event({'type': "error", 'message': str(e)})


@router.get("/chat/history")
async def history(
    request: Request,
    cosmos_service: CosmosDBService = Depends(get_cosmos_service),
    _ = auth_dependency
):
    with tracer.start_as_current_span("chat_history"):
        # Retrieve the thread ID from the cookies (if available).
        thread_id = request.cookies.get('thread_id')

        # Create new thread if none exists
        if not thread_id:
            thread_id = str(uuid.uuid4())
            logger.info(f"Creating new thread: {thread_id}")
        else:
            logger.info(f"Using existing thread: {thread_id}")

        try:
            # Get messages from Cosmos DB
            messages = await cosmos_service.get_messages(thread_id)
            
            # Format messages for frontend
            formatted_messages = []
            for msg in messages:
                formatted_msg = {
                    'content': msg.get('content', ''),
                    'role': msg.get('role'),
                    'created_at': msg.get('created_at', ''),
                    'annotations': []  # Keep compatibility with frontend
                }
                formatted_messages.append(formatted_msg)
            
            logger.info(f"Retrieved {len(formatted_messages)} messages for thread: {thread_id}")
            response = JSONResponse(content=formatted_messages)
            
            # Update cookies to persist the thread ID
            response.set_cookie("thread_id", thread_id)
            return response
            
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting chat history: {e}")


@router.get("/agent")
async def get_chat_agent(request: Request):
    """Get agent information - return mock data for compatibility."""
    return JSONResponse(content={
        "id": "direct-openai-agent",
        "name": "Azure OpenAI Agent",
        "model": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
        "description": "AI Agent using direct Azure OpenAI integration"
    })


@router.post("/chat")
async def chat(
    request: Request,
    cosmos_service: CosmosDBService = Depends(get_cosmos_service),
    rag_service: RAGService = Depends(get_rag_service),
    app_insights_conn_str: str = Depends(get_app_insights_conn_str),
    _ = auth_dependency
):
    # Retrieve the thread ID from the cookies (if available).
    thread_id = request.cookies.get('thread_id')

    with tracer.start_as_current_span("chat_request"):
        carrier = {}        
        TraceContextTextMapPropagator().inject(carrier)
        
        # Create new thread if none exists
        if not thread_id:
            thread_id = str(uuid.uuid4())
            logger.info(f"Creating new thread for chat: {thread_id}")

        # Parse the JSON from the request.
        try:
            user_message_data = await request.json()
            user_message = user_message_data.get('message', '')
        except Exception as e:
            logger.error(f"Invalid JSON in request: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON in request: {e}")

        logger.info(f"Processing chat message: {user_message}")

        # Set the Server-Sent Events (SSE) response headers.
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
        logger.info(f"Starting streaming response for thread ID {thread_id}")

        # Create the streaming response using the generator.
        response = StreamingResponse(
            chat_stream_response(user_message, thread_id, rag_service, cosmos_service, carrier),
            headers=headers
        )

        # Update cookies to persist the thread ID.
        response.set_cookie("thread_id", thread_id)
        return response


@router.post("/upload")
async def upload_file(
    request: Request,
    blob_service: BlobStorageService = Depends(get_blob_service),
    cosmos_service: CosmosDBService = Depends(get_cosmos_service),
    rag_service: RAGService = Depends(get_rag_service),
    _ = auth_dependency
):
    """Upload a file and process it for knowledge base."""
    try:
        form = await request.form()
        file = form.get("file")
        
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        file_content = await file.read()
        filename = file.filename
        content_type = file.content_type or "application/octet-stream"
        
        # Upload to blob storage
        file_metadata = await blob_service.upload_file(
            file_content, filename, content_type
        )
        
        # Store file metadata in Cosmos DB
        await cosmos_service.store_file_metadata(
            file_metadata["id"], file_metadata
        )
        
        # Process text files for RAG
        if content_type.startswith("text/") or filename.endswith((".txt", ".md", ".py", ".js", ".json")):
            try:
                text_content = file_content.decode('utf-8')
                await rag_service.process_document(
                    text_content, filename, file_metadata["id"]
                )
                logger.info(f"Processed file for RAG: {filename}")
            except Exception as e:
                logger.warning(f"Could not process file for RAG: {e}")
        
        return JSONResponse({
            "success": True,
            "file": {
                "id": file_metadata["id"],
                "name": filename,
                "contentType": content_type,
                "size": len(file_content),
                "url": file_metadata["url"]
            }
        })
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e}")


@router.get("/config/azure")
async def get_azure_config(_ = auth_dependency):
    """Get Azure configuration for frontend use"""
    try:
        subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
        resource_group = os.environ.get("AZURE_RESOURCE_GROUP", "")
        location = os.environ.get("AZURE_LOCATION", "")
        
        return JSONResponse({
            "subscriptionId": subscription_id,
            "resourceGroup": resource_group,
            "location": location,
            "resourceName": "direct-openai-agent",
            "projectName": "ai-agent",
            "wsid": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        })
    except Exception as e:
        logger.error(f"Error getting Azure config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Azure configuration")