# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

import logging

import numpy as np

from .azure_openai_service import AzureOpenAIService
from .blob_storage_service import BlobStorageService
from .cosmos_db_service import CosmosDBService

logger = logging.getLogger("azureaiapp")


class RAGService:
    """Simple RAG (Retrieval-Augmented Generation) service using embeddings."""
    
    def __init__(
        self, 
        openai_service: AzureOpenAIService,
        cosmos_service: CosmosDBService,
        blob_service: BlobStorageService
    ):
        self.openai_service = openai_service
        self.cosmos_service = cosmos_service
        self.blob_service = blob_service
        
        logger.info("Initialized RAG service")
    
    async def process_document(self, file_content: str, filename: str, file_id: str) -> list[dict]:
        """Process a document and create embeddings for chunks."""
        try:
            # Simple text chunking (split by paragraphs or sentences)
            chunks = self._chunk_text(file_content)
            
            embeddings_data = []
            for i, chunk in enumerate(chunks):
                # Create embedding for chunk
                embedding = await self.openai_service.create_embeddings(chunk)
                
                chunk_data = {
                    "chunk_id": f"{file_id}_{i}",
                    "file_id": file_id,
                    "filename": filename,
                    "content": chunk,
                    "embedding": embedding,
                    "chunk_index": i
                }
                embeddings_data.append(chunk_data)
            
            # Store embeddings in Cosmos DB (using files partition)
            await self._store_embeddings(embeddings_data)
            
            logger.info(f"Processed {len(chunks)} chunks for file: {filename}")
            return embeddings_data
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            raise
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to end at a sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                boundary = max(last_period, last_newline)
                
                if boundary > start + chunk_size // 2:  # Only adjust if boundary is reasonable
                    chunk = chunk[:boundary + 1]
                    end = start + len(chunk)
            
            chunks.append(chunk.strip())
            start = end - overlap if end < len(text) else end
        
        return [chunk for chunk in chunks if chunk]  # Remove empty chunks
    
    async def _store_embeddings(self, embeddings_data: list[dict]):
        """Store embeddings in Cosmos DB."""
        try:
            for chunk_data in embeddings_data:
                doc = {
                    "id": chunk_data["chunk_id"],
                    "thread_id": "embeddings",  # Special partition for embeddings
                    "type": "embedding",
                    "file_id": chunk_data["file_id"],
                    "filename": chunk_data["filename"],
                    "content": chunk_data["content"],
                    "embedding": chunk_data["embedding"],
                    "chunk_index": chunk_data["chunk_index"]
                }
                
                # Store in Cosmos DB
                await self.cosmos_service.container.create_item(body=doc)
            
            logger.info(f"Stored {len(embeddings_data)} embeddings in Cosmos DB")
        except Exception as e:
            logger.error(f"Error storing embeddings: {e}")
            raise
    
    async def search_similar_content(self, query: str, top_k: int = 5) -> list[dict]:
        """Search for similar content using embeddings."""
        try:
            # Create embedding for query
            query_embedding = await self.openai_service.create_embeddings(query)
            
            # Get all embeddings from Cosmos DB
            query_sql = "SELECT * FROM c WHERE c.type = 'embedding'"
            items = []
            async for item in self.cosmos_service.container.query_items(
                query=query_sql,
                partition_key="embeddings"
            ):
                items.append(item)
            
            if not items:
                logger.info("No embeddings found for similarity search")
                return []
            
            # Calculate similarity scores
            similarities = []
            for item in items:
                embedding = np.array(item["embedding"])
                query_emb = np.array(query_embedding)
                
                # Cosine similarity
                similarity = np.dot(query_emb, embedding) / (
                    np.linalg.norm(query_emb) * np.linalg.norm(embedding)
                )
                
                similarities.append({
                    "content": item["content"],
                    "filename": item["filename"],
                    "file_id": item["file_id"],
                    "chunk_id": item["id"],
                    "similarity": float(similarity)
                })
            
            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            top_results = similarities[:top_k]
            
            logger.info(f"Found {len(top_results)} similar chunks for query")
            return top_results
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            raise
    
    async def generate_response_with_context(
        self, 
        user_query: str, 
        conversation_history: list[dict],
        max_context_chunks: int = 3
    ) -> str:
        """Generate a response using RAG with conversation context."""
        try:
            # Search for relevant content
            relevant_chunks = await self.search_similar_content(user_query, max_context_chunks)
            
            # Build context from relevant chunks
            context_parts = []
            for chunk in relevant_chunks:
                context_parts.append(f"From {chunk['filename']}:\n{chunk['content']}")
            
            context_text = "\n\n".join(context_parts) if context_parts else "No relevant context found."
            
            # Build messages for OpenAI
            messages = [
                {
                    "role": "system",
                    "content": f"""You are a helpful AI assistant. Use the following context to answer user questions. 
                    If the context doesn't contain relevant information, say so and provide a general response.
                    
                    Context:
                    {context_text}"""
                }
            ]
            
            # Add conversation history (keep last 10 messages to avoid token limits)
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            for msg in recent_history:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg.get("content", "")
                    })
            
            # Add current user query
            messages.append({
                "role": "user",
                "content": user_query
            })
            
            # Generate response
            response = await self.openai_service.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            response_text = response.choices[0].message.content
            
            # Add citations if relevant chunks were found
            if relevant_chunks:
                citations = list(set([chunk["filename"] for chunk in relevant_chunks]))
                response_text += f"\n\nSources: {', '.join(citations)}"
            
            logger.info("Generated response with RAG context")
            return response_text
        except Exception as e:
            logger.error(f"Error generating response with context: {e}")
            raise