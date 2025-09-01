# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

import logging
import os
from typing import Optional

from openai import AsyncAzureOpenAI

logger = logging.getLogger("azureaiapp")


class AzureOpenAIService:
    """Service for interacting with Azure OpenAI directly."""
    
    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        if not self.endpoint or not self.api_key:
            raise ValueError("Azure OpenAI endpoint and API key must be provided")
        
        self.client = AsyncAzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint
        )
        
        logger.info(f"Initialized Azure OpenAI service with endpoint: {self.endpoint}")
    
    async def chat_completion(
        self, 
        messages: list[dict], 
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """Create a chat completion using Azure OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise
    
    async def create_embeddings(self, text: str, model: str = "text-embedding-3-small"):
        """Create embeddings for text using Azure OpenAI."""
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embeddings: {e}")
            raise
    
    async def close(self):
        """Close the Azure OpenAI client."""
        if hasattr(self.client, 'close'):
            await self.client.close()