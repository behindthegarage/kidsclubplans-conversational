"""
Memory management for conversations and user context.
Handles both short-term (session) and long-term (persistent) memory.
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class MemoryManager:
    """
    Manages user memory and conversation context.
    
    This is a simple in-memory implementation. For production,
    this should be backed by Redis or a database.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize memory manager.
        
        Args:
            storage_path: Path to store persistent memory (JSON file)
        """
        self.storage_path = storage_path or os.getenv("MEMORY_STORAGE_PATH", "./memory.json")
        
        # In-memory storage
        self.user_profiles: Dict[str, Dict] = defaultdict(dict)
        self.conversations: Dict[str, List[Dict]] = defaultdict(list)
        self.session_context: Dict[str, Dict] = {}
        
        # Load existing memory if available
        self._load_memory()
        
        print(f"🧠 Memory manager initialized (storage: {self.storage_path})")
    
    def _load_memory(self):
        """Load persistent memory from disk."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.user_profiles = defaultdict(dict, data.get("profiles", {}))
                    print(f"📚 Loaded {len(self.user_profiles)} user profiles")
            except Exception as e:
                print(f"⚠️ Could not load memory: {e}")
    
    def _save_memory(self):
        """Save persistent memory to disk."""
        try:
            data = {
                "profiles": dict(self.user_profiles),
                "last_saved": datetime.now().isoformat()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save memory: {e}")
    
    def get_user_context(self, user_id: str) -> Dict:
        """
        Get context about a user for personalization.
        
        Returns:
            Dict with preferences, patterns, history summary
        """
        profile = self.user_profiles.get(user_id, {})
        
        return {
            "preferences": profile.get("preferences", {}),
            "common_age_groups": profile.get("common_age_groups", []),
            "favorite_activity_types": profile.get("favorite_activity_types", []),
            "typical_schedule": profile.get("typical_schedule", {}),
            "last_interaction": profile.get("last_interaction")
        }
    
    def add_interaction(
        self, 
        user_id: str, 
        query: str, 
        context: List[Dict],
        session_id: Optional[str] = None
    ):
        """
        Record an interaction for learning user patterns.
        
        Args:
            user_id: Unique user identifier
            query: The user's query
            context: Activities that were relevant
            session_id: Optional session identifier
        """
        timestamp = datetime.now().isoformat()
        
        # Add to conversation history
        interaction = {
            "timestamp": timestamp,
            "query": query,
            "activity_count": len(context),
            "session_id": session_id
        }
        
        self.conversations[user_id].append(interaction)
        
        # Update user profile based on query
        self._update_profile_from_query(user_id, query, context)
        
        # Save periodically (every 10 interactions)
        if len(self.conversations[user_id]) % 10 == 0:
            self._save_memory()
    
    def _update_profile_from_query(self, user_id: str, query: str, context: List[Dict]):
        """
        Extract insights from query to update user profile.
        
        This is a simple keyword-based approach. In production,
        this could use LLM extraction.
        """
        profile = self.user_profiles[user_id]
        
        # Update last interaction
        profile["last_interaction"] = datetime.now().isoformat()
        
        # Track preferences based on keywords in query
        query_lower = query.lower()
        
        # Age groups
        age_keywords = {
            "5": "5-6 years",
            "6": "6-7 years", 
            "7": "7-8 years",
            "8": "8-9 years",
            "9": "9-10 years",
            "10": "10-11 years",
            "preschool": "3-5 years",
            "elementary": "5-10 years"
        }
        
        if "age_groups" not in profile:
            profile["age_groups"] = defaultdict(int)
        
        for keyword, age_group in age_keywords.items():
            if keyword in query_lower:
                profile["age_groups"][age_group] += 1
        
        # Activity types mentioned
        activity_types = ["art", "craft", "science", "cooking", "physical", "game", "outdoor", "indoor"]
        
        if "favorite_activity_types" not in profile:
            profile["favorite_activity_types"] = defaultdict(int)
        
        for activity_type in activity_types:
            if activity_type in query_lower:
                profile["favorite_activity_types"][activity_type] += 1
        
        # Preferences (outdoor/indoor, low prep, etc.)
        if "preferences" not in profile:
            profile["preferences"] = {}
        
        if "outdoor" in query_lower or "outside" in query_lower:
            profile["preferences"]["prefers_outdoor"] = True
        
        if "indoor" in query_lower or "inside" in query_lower:
            profile["preferences"]["prefers_indoor"] = True
        
        if "low prep" in query_lower or "easy" in query_lower or "simple" in query_lower:
            profile["preferences"]["prefers_low_prep"] = True
    
    def get_conversation_history(
        self, 
        user_id: str, 
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get recent conversation history for a user."""
        history = self.conversations.get(user_id, [])
        
        if session_id:
            history = [h for h in history if h.get("session_id") == session_id]
        
        return history[-limit:]
    
    def set_session_context(self, session_id: str, context: Dict):
        """Set temporary context for a session (e.g., current schedule being built)."""
        self.session_context[session_id] = {
            "data": context,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_session_context(self, session_id: str) -> Optional[Dict]:
        """Get temporary context for a session."""
        ctx = self.session_context.get(session_id)
        if ctx:
            # Check if context is stale (older than 1 hour)
            ctx_time = datetime.fromisoformat(ctx["timestamp"])
            if datetime.now() - ctx_time > timedelta(hours=1):
                del self.session_context[session_id]
                return None
            return ctx["data"]
        return None
    
    def clear_session_context(self, session_id: str):
        """Clear temporary session context."""
        if session_id in self.session_context:
            del self.session_context[session_id]


# Simple in-memory fallback for testing
class SimpleMemoryManager:
    """Ultra-simple memory for testing without persistence."""
    
    def __init__(self):
        self.users = {}
    
    def get_user_context(self, user_id: str) -> Dict:
        return self.users.get(user_id, {})
    
    def add_interaction(self, user_id: str, query: str, context: List[Dict], session_id=None):
        if user_id not in self.users:
            self.users[user_id] = {"interactions": 0}
        self.users[user_id]["interactions"] += 1
    
    def get_conversation_history(self, user_id: str, session_id=None, limit=10):
        return []
