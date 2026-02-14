"""
RAG (Retrieval-Augmented Generation) module.
Handles vector search with Pinecone for activity retrieval.
"""

import os
from typing import List, Dict, Optional
import json

# Try to import Pinecone
try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    print("⚠️ Pinecone not installed. Vector search will be disabled.")

# Try to import OpenAI for embeddings
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class VectorStore:
    """Wrapper around Pinecone for activity search."""
    
    def __init__(self, api_key: str, index_name: str, openai_key: str):
        self.api_key = api_key
        self.index_name = index_name
        self.openai_key = openai_key
        
        if not PINECONE_AVAILABLE:
            raise ImportError("Pinecone package not installed. Run: pip install pinecone")
        
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
        
        # Initialize clients
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(index_name)
        self.openai_client = OpenAI(api_key=openai_key)
        
        print(f"✅ Connected to Pinecone index: {index_name}")
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-large",  # 3072 dimensions to match index
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return []
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for activities matching the query.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            filter_dict: Optional metadata filters (e.g., {"type": "Art"})
        
        Returns:
            List of activity dictionaries with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = self.get_embedding(query)
            
            if not query_embedding:
                return []
            
            # Query Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
            
            # Format results
            activities = []
            for match in results.matches:
                activity = {
                    "id": match.id,
                    "score": float(match.score),
                    **(match.metadata or {})
                }
                activities.append(activity)
            
            return activities
            
        except Exception as e:
            print(f"Search error: {e}")
            return []


def initialize_vector_store() -> Optional[VectorStore]:
    """
    Initialize the vector store from environment variables.
    
    Expected environment variables:
    - PINECONE_API_KEY
    - PINECONE_INDEX_NAME
    - OPENAI_API_KEY
    """
    pinecone_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not all([pinecone_key, index_name, openai_key]):
        print("⚠️ Missing environment variables for vector store:")
        print("   PINECONE_API_KEY, PINECONE_INDEX_NAME, OPENAI_API_KEY")
        return None
    
    try:
        return VectorStore(pinecone_key, index_name, openai_key)
    except Exception as e:
        print(f"⚠️ Could not initialize vector store: {e}")
        return None


def search_activities(
    vector_store: VectorStore,
    query: str,
    limit: int = 5,
    activity_type: Optional[str] = None
) -> List[Dict]:
    """
    Convenience function to search activities with optional filtering.
    
    Args:
        vector_store: Initialized VectorStore instance
        query: Search query
        limit: Max results
        activity_type: Optional filter by activity type (Art, Craft, Science, etc.)
    
    Returns:
        List of matching activities
    """
    if not vector_store:
        return []
    
    filter_dict = None
    if activity_type:
        filter_dict = {"type": activity_type}
    
    return vector_store.search(query, top_k=limit, filter_dict=filter_dict)


def format_activity_for_display(activity: Dict) -> str:
    """Format an activity for display in chat."""
    title = activity.get("title", "Untitled Activity")
    description = activity.get("description", "")
    activity_type = activity.get("type", "")
    supplies = activity.get("supplies", "")
    
    formatted = f"**{title}**"
    if activity_type:
        formatted += f" ({activity_type})"
    formatted += f"\n{description[:200]}..."
    
    if supplies:
        formatted += f"\nSupplies: {supplies[:100]}..."
    
    return formatted
