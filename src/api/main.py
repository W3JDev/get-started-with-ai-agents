# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

import contextlib
import os

import fastapi
from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from logging_config import configure_logging
from services.azure_openai_service import AzureOpenAIService
from services.blob_storage_service import BlobStorageService
from services.cosmos_db_service import CosmosDBService
from services.rag_service import RAGService

enable_trace = False
logger = None

@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    """Application lifespan manager for initializing and cleaning up services."""
    
    # Initialize services
    openai_service = None
    cosmos_service = None
    blob_service = None
    rag_service = None
    
    try:
        # Initialize Azure OpenAI service
        openai_service = AzureOpenAIService()
        logger.info("Initialized Azure OpenAI service")
        
        # Initialize Cosmos DB service
        cosmos_service = CosmosDBService()
        await cosmos_service.initialize()
        logger.info("Initialized Cosmos DB service")
        
        # Initialize Blob Storage service
        blob_service = BlobStorageService()
        await blob_service.initialize()
        logger.info("Initialized Blob Storage service")
        
        # Initialize RAG service
        rag_service = RAGService(openai_service, cosmos_service, blob_service)
        logger.info("Initialized RAG service")
        
        # Configure Application Insights if enabled
        if enable_trace:
            try:
                from azure.monitor.opentelemetry import configure_azure_monitor
                # Use connection string from environment if available
                connection_string = os.getenv("APPLICATION_INSIGHTS_CONNECTION_STRING")
                if connection_string:
                    configure_azure_monitor(connection_string=connection_string)
                    app.state.application_insights_connection_string = connection_string
                    logger.info("Configured Application Insights for tracing.")
                else:
                    logger.warning("Application Insights connection string not found")
            except ImportError:
                logger.error("Required libraries for tracing not installed.")
                logger.error("Please make sure azure-monitor-opentelemetry is installed.")
        
        # Store services in app state
        app.state.openai_service = openai_service
        app.state.cosmos_service = cosmos_service
        app.state.blob_service = blob_service
        app.state.rag_service = rag_service
        
        logger.info("All services initialized successfully")
        
        yield

    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise RuntimeError(f"Error during startup: {e}")

    finally:
        # Clean up services
        try:
            if rag_service:
                logger.info("RAG service cleanup completed")
            if blob_service:
                await blob_service.close()
                logger.info("Closed Blob Storage service")
            if cosmos_service:
                await cosmos_service.close()
                logger.info("Closed Cosmos DB service")
            if openai_service:
                await openai_service.close()
                logger.info("Closed Azure OpenAI service")
        except Exception:
            logger.error("Error during cleanup", exc_info=True)


def create_app():
    if not os.getenv("RUNNING_IN_PRODUCTION"):
        load_dotenv(override=True)

    global logger
    logger = configure_logging(os.getenv("APP_LOG_FILE", ""))

    enable_trace_string = os.getenv("ENABLE_AZURE_MONITOR_TRACING", "")
    global enable_trace
    enable_trace = False
    if enable_trace_string == "":
        enable_trace = False
    else:
        enable_trace = str(enable_trace_string).lower() == "true"
    if enable_trace:
        logger.info("Tracing is enabled.")
        try:
            import importlib.util
            if importlib.util.find_spec("azure.monitor.opentelemetry") is not None:
                from azure.monitor.opentelemetry import configure_azure_monitor  # noqa: F401
        except ModuleNotFoundError:
            logger.error("Required libraries for tracing not installed.")
            logger.error("Please make sure azure-monitor-opentelemetry is installed.")
            exit()
    else:
        logger.info("Tracing is not enabled")

    directory = os.path.join(os.path.dirname(__file__), "static")
    app = fastapi.FastAPI(lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=directory), name="static")
    
    # Mount React static files
    # Uncomment the following lines if you have a React frontend
    # react_directory = os.path.join(os.path.dirname(__file__), "static/react")
    # app.mount("/static/react", StaticFiles(directory=react_directory), name="react")

    from . import routes  # Import routes
    app.include_router(routes.router)

    # Global exception handler for any unhandled exceptions
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception occurred", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    return app
