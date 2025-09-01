# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

import logging
import os
import uuid
from typing import BinaryIO, Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient

logger = logging.getLogger("azureaiapp")


class BlobStorageService:
    """Service for managing file uploads and knowledge base in Azure Blob Storage."""
    
    def __init__(self):
        self.account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "knowledge-base")
        
        if not self.account_name or not self.account_key:
            raise ValueError("Azure Storage account name and key must be provided")
        
        connection_string = (
            f"DefaultEndpointsProtocol=https;AccountName={self.account_name};"
            f"AccountKey={self.account_key};EndpointSuffix=core.windows.net"
        )
        self.client = BlobServiceClient.from_connection_string(connection_string)
        
        logger.info(f"Initialized Blob Storage service with account: {self.account_name}")
    
    async def initialize(self):
        """Initialize container if it doesn't exist."""
        try:
            container_client = self.client.get_container_client(self.container_name)
            await container_client.create_container()
            logger.info(f"Created container: {self.container_name}")
        except Exception as e:
            if "ContainerAlreadyExists" in str(e):
                logger.info(f"Container already exists: {self.container_name}")
            else:
                logger.error(f"Error creating container: {e}")
                raise
    
    async def upload_file(
        self, 
        file_content: BinaryIO, 
        filename: str, 
        content_type: str = "application/octet-stream"
    ) -> dict:
        """Upload a file to blob storage."""
        try:
            # Generate unique blob name
            file_id = str(uuid.uuid4())
            blob_name = f"{file_id}_{filename}"
            
            blob_client = self.client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload file
            await blob_client.upload_blob(
                file_content,
                content_type=content_type,
                overwrite=True
            )
            
            # Get blob URL
            blob_url = blob_client.url
            
            file_metadata = {
                "id": file_id,
                "filename": filename,
                "blob_name": blob_name,
                "content_type": content_type,
                "url": blob_url,
                "size": file_content.seek(0, 2) if hasattr(file_content, 'seek') else None
            }
            
            if hasattr(file_content, 'seek'):
                file_content.seek(0)  # Reset file pointer
            
            logger.info(f"Uploaded file: {filename} as {blob_name}")
            return file_metadata
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    async def download_file(self, blob_name: str) -> bytes:
        """Download a file from blob storage."""
        try:
            blob_client = self.client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            download_stream = await blob_client.download_blob()
            content = await download_stream.readall()
            
            logger.info(f"Downloaded file: {blob_name}")
            return content
        except ResourceNotFoundError:
            logger.error(f"File not found: {blob_name}")
            raise
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise
    
    async def get_file_url(self, blob_name: str) -> str:
        """Get the URL for a file in blob storage."""
        try:
            blob_client = self.client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            return blob_client.url
        except Exception as e:
            logger.error(f"Error getting file URL: {e}")
            raise
    
    async def delete_file(self, blob_name: str) -> bool:
        """Delete a file from blob storage."""
        try:
            blob_client = self.client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            await blob_client.delete_blob()
            logger.info(f"Deleted file: {blob_name}")
            return True
        except ResourceNotFoundError:
            logger.warning(f"File not found for deletion: {blob_name}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            raise
    
    async def list_files(self, prefix: Optional[str] = None) -> list[dict]:
        """List files in blob storage."""
        try:
            container_client = self.client.get_container_client(self.container_name)
            
            files = []
            async for blob in container_client.list_blobs(name_starts_with=prefix):
                file_info = {
                    "name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None,
                    "last_modified": blob.last_modified.isoformat() if blob.last_modified else None,
                    "url": f"{container_client.url}/{blob.name}"
                }
                files.append(file_info)
            
            logger.info(f"Listed {len(files)} files from blob storage")
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise
    
    async def close(self):
        """Close the blob storage client."""
        if self.client:
            await self.client.close()