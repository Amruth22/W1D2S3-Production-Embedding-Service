import os
import numpy as np
import chromadb
from chromadb.config import Settings
import hashlib
import logging
from functools import lru_cache
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from google import genai
from google.genai.types import EmbedContentConfig

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, collection_name: str = "documents", cache_size: int = 1000):
        """Initialize embedding service with Chroma and LRU cache"""
        # Load environment variables
        load_dotenv()
        
        # Initialize Gemini client
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-embedding-001"
        self.dimension = 3072
        
        # Initialize Chroma client
        self.chroma_client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection_name = collection_name
        try:
            self.collection = self.chroma_client.get_collection(name=collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"description": "Document embeddings collection"}
            )
            logger.info(f"Created new collection: {collection_name}")
        
        # Cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_size = cache_size
        
        logger.info("EmbeddingService initialized successfully")
    
    def _create_text_hash(self, text: str) -> str:
        """Create a hash for text to use as document ID"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    @lru_cache(maxsize=1000)
    def _generate_embedding_cached(self, text_hash: str, text: str) -> Optional[np.ndarray]:
        """Generate embedding with LRU cache"""
        self.cache_misses += 1
        try:
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=[text],
                config=EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=self.dimension,
                    title="Document Embedding"
                )
            )
            
            # Handle different response structures
            if hasattr(response, 'embedding'):
                embedding = np.array(response.embedding.values, dtype=np.float32)
            elif hasattr(response, 'embeddings') and len(response.embeddings) > 0:
                embedding = np.array(response.embeddings[0].values, dtype=np.float32)
            else:
                logger.error(f"Unexpected response structure: {response}")
                return None
            
            logger.debug(f"Generated embedding for text hash: {text_hash}")
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text with caching"""
        text_hash = self._create_text_hash(text)
        
        # Check if embedding is cached
        try:
            # This will hit the LRU cache if available
            embedding = self._generate_embedding_cached(text_hash, text)
            if embedding is not None:
                # Check if it was a cache hit by checking cache info
                cache_info = self._generate_embedding_cached.cache_info()
                if cache_info.hits > self.cache_hits:
                    self.cache_hits = cache_info.hits
                    logger.debug(f"Cache hit for text: {text[:50]}...")
                
                return embedding
        except Exception as e:
            logger.error(f"Error in cached embedding generation: {e}")
        
        return None
    
    def add_document(self, text: str, metadata: Optional[Dict] = None) -> Optional[str]:
        """Add document to Chroma collection"""
        try:
            # Generate embedding
            embedding = self.generate_embedding(text)
            if embedding is None:
                return None
            
            # Create document ID
            doc_id = self._create_text_hash(text)
            
            # Prepare metadata
            doc_metadata = metadata or {}
            doc_metadata.update({
                "text_length": len(text),
                "text_preview": text[:100] + "..." if len(text) > 100 else text
            })
            
            # Add to collection
            self.collection.add(
                embeddings=[embedding.tolist()],
                documents=[text],
                metadatas=[doc_metadata],
                ids=[doc_id]
            )
            
            logger.info(f"Added document with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return None
    
    def search_similar(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            if query_embedding is None:
                return []
            
            # Search in collection
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=min(k, self.collection.count())
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    result = {
                        "id": results['ids'][0][i],
                        "text": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i],
                        "similarity_score": 1 / (1 + results['distances'][0][i])
                    }
                    formatted_results.append(result)
            
            logger.info(f"Search returned {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "embedding_dimension": self.dimension,
                "model": self.model_name
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}
    
    def reset_collection(self) -> bool:
        """Reset the collection (delete all documents)"""
        try:
            # Delete existing collection
            self.chroma_client.delete_collection(name=self.collection_name)
            
            # Create new collection
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "Document embeddings collection"}
            )
            
            logger.info(f"Collection {self.collection_name} reset successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_info = self._generate_embedding_cached.cache_info()
        return {
            "cache_hits": cache_info.hits,
            "cache_misses": cache_info.misses,
            "cache_size": cache_info.currsize,
            "cache_maxsize": cache_info.maxsize,
            "hit_rate": cache_info.hits / (cache_info.hits + cache_info.misses) if (cache_info.hits + cache_info.misses) > 0 else 0
        }
    
    def clear_cache(self):
        """Clear the LRU cache"""
        self._generate_embedding_cached.cache_clear()
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("Cache cleared successfully")
    
    def test_connection(self) -> Dict[str, bool]:
        """Test connections to external services"""
        results = {}
        
        # Test Gemini API
        try:
            test_embedding = self.generate_embedding("test connection")
            results["gemini"] = test_embedding is not None
        except Exception as e:
            logger.error(f"Gemini API test failed: {e}")
            results["gemini"] = False
        
        # Test Chroma DB
        try:
            count = self.collection.count()
            results["chroma"] = True
        except Exception as e:
            logger.error(f"Chroma DB test failed: {e}")
            results["chroma"] = False
        
        return results