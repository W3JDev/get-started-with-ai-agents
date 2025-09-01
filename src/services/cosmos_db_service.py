# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

import logging
import os
from datetime import datetime
from typing import Optional

from azure.cosmos import PartitionKey
from azure.cosmos.aio import CosmosClient

logger = logging.getLogger("azureaiapp")


class CosmosDBService:
    """Service for managing conversation history and metadata in Cosmos DB."""
    
    def __init__(self):
        self.endpoint = os.getenv("AZURE_COSMOSDB_ENDPOINT")
        self.key = os.getenv("AZURE_COSMOSDB_KEY")
        self.database_name = os.getenv("AZURE_COSMOSDB_DATABASE_NAME", "ai-agent-db")
        self.container_name = os.getenv("AZURE_COSMOSDB_CONTAINER_NAME", "conversations")
        
        if not self.endpoint or not self.key:
            raise ValueError("Cosmos DB endpoint and key must be provided")
        
        self.client = CosmosClient(self.endpoint, self.key)
        self.database = None
        self.container = None
        
        logger.info(f"Initialized Cosmos DB service with endpoint: {self.endpoint}")
    
    async def initialize(self):
        """Initialize database and container."""
        try:
            # Create database if it doesn't exist
            self.database = await self.client.create_database_if_not_exists(
                id=self.database_name
            )
            
            # Create container if it doesn't exist
            self.container = await self.database.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/thread_id"),
                offer_throughput=400
            )
            
            logger.info(f"Initialized Cosmos DB database: {self.database_name}, container: {self.container_name}")
        except Exception as e:
            logger.error(f"Error initializing Cosmos DB: {e}")
            raise
    
    async def create_thread(self, thread_id: str) -> dict:
        """Create a new conversation thread."""
        try:
            thread_doc = {
                "id": thread_id,
                "thread_id": thread_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "messages": []
            }
            
            result = await self.container.create_item(body=thread_doc)
            logger.info(f"Created new thread: {thread_id}")
            return result
        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            raise
    
    async def get_thread(self, thread_id: str) -> Optional[dict]:
        """Get a conversation thread by ID."""
        try:
            result = await self.container.read_item(
                item=thread_id,
                partition_key=thread_id
            )
            return result
        except Exception:
            logger.debug(f"Thread not found: {thread_id}")
            return None
    
    async def add_message(self, thread_id: str, message: dict) -> dict:
        """Add a message to a conversation thread."""
        try:
            # Get existing thread or create new one
            thread = await self.get_thread(thread_id)
            if not thread:
                thread = await self.create_thread(thread_id)
            
            # Add timestamp and ID to message
            message_with_metadata = {
                **message,
                "id": f"{thread_id}_{len(thread.get('messages', []))}",
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Update thread with new message
            thread["messages"].append(message_with_metadata)
            thread["updated_at"] = datetime.utcnow().isoformat()
            
            await self.container.replace_item(
                item=thread_id,
                body=thread
            )
            
            logger.info(f"Added message to thread: {thread_id}")
            return message_with_metadata
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise
    
    async def get_messages(self, thread_id: str) -> list[dict]:
        """Get all messages from a conversation thread."""
        try:
            thread = await self.get_thread(thread_id)
            if thread:
                return thread.get("messages", [])
            return []
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            raise
    
    async def store_file_metadata(self, file_id: str, metadata: dict) -> dict:
        """Store file metadata for knowledge base."""
        try:
            file_doc = {
                "id": file_id,
                "thread_id": "files",  # Special partition for files
                "type": "file_metadata",
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = await self.container.create_item(body=file_doc)
            logger.info(f"Stored file metadata: {file_id}")
            return result
        except Exception as e:
            logger.error(f"Error storing file metadata: {e}")
            raise
    
    async def get_file_metadata(self, file_id: str) -> Optional[dict]:
        """Get file metadata by ID."""
        try:
            result = await self.container.read_item(
                item=file_id,
                partition_key="files"
            )
            return result.get("metadata")
        except Exception:
            logger.debug(f"File metadata not found: {file_id}")
            return None
    
    async def close(self):
        """Close the Cosmos DB client."""
        if self.client:
            await self.client.close()