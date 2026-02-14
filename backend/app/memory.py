"""Enhanced memory management with user profiles and persistent storage."""

import json
import os
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

from .models import UserProfile, UserProfileUpdate


class MemoryManager:
    """
    Manages user profiles, conversation history, and session context.
    Uses SQLite for persistent storage.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize memory manager with SQLite backend.
        
        Args:
            storage_path: Path to SQLite database (default: ./memory.db)
        """
        self.db_path = storage_path or os.getenv("MEMORY_DB_PATH", "./memory.db")
        self.session_context: Dict[str, Dict] = {}
        
        # Initialize database
        self._init_db()
        print(f"🧠 Memory manager initialized (SQLite: {self.db_path})")
    
    def _init_db(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    query TEXT,
                    response_summary TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user 
                ON conversations(user_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_session 
                ON conversations(session_id)
            """)
            
            # Phase 3: Schedules table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    title TEXT,
                    age_group TEXT,
                    duration_hours INTEGER,
                    activities TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_schedules_user_date 
                ON schedules(user_id, date)
            """)
            
            # Phase 3: Weather cache table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weather_cache (
                    location TEXT NOT NULL,
                    date TEXT NOT NULL,
                    data TEXT NOT NULL,
                    cached_at TEXT NOT NULL,
                    PRIMARY KEY (location, date)
                )
            """)
            
            conn.commit()
    
    def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get existing profile or create new one."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM user_profiles WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if row:
                data = json.loads(row[0])
                return UserProfile(**data)
            else:
                # Create new profile
                profile = UserProfile(user_id=user_id)
                self._save_profile(profile)
                return profile
    
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile if it exists."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM user_profiles WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if row:
                data = json.loads(row[0])
                return UserProfile(**data)
            return None
    
    def update_profile(self, user_id: str, update: UserProfileUpdate) -> UserProfile:
        """Update user profile with new data."""
        profile = self.get_or_create_profile(user_id)
        
        # Update fields from the update model
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        
        profile.updated_at = datetime.now().isoformat()
        self._save_profile(profile)
        return profile
    
    def _save_profile(self, profile: UserProfile):
        """Save profile to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO user_profiles 
                   (user_id, data, created_at, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    profile.user_id,
                    json.dumps(profile.model_dump()),
                    profile.created_at,
                    profile.updated_at
                )
            )
            conn.commit()
    
    def add_interaction(
        self, 
        user_id: str, 
        query: str, 
        response_summary: str = "",
        session_id: Optional[str] = None
    ):
        """Record a conversation interaction."""
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO conversations 
                   (user_id, session_id, query, response_summary, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, session_id, query, response_summary, timestamp)
            )
            conn.commit()
        
        # Update profile with interaction count and patterns
        profile = self.get_or_create_profile(user_id)
        profile.last_interaction = timestamp
        profile.interaction_count += 1
        
        # Extract patterns from query
        self._extract_patterns(profile, query)
        
        self._save_profile(profile)
    
    def _extract_patterns(self, profile: UserProfile, query: str):
        """Extract insights from query to update profile."""
        query_lower = query.lower()
        
        # Age groups
        age_patterns = {
            "5 year": "5-6 years",
            "6 year": "6-7 years",
            "7 year": "7-8 years",
            "8 year": "8-9 years",
            "9 year": "9-10 years",
            "10 year": "10-11 years",
            "preschool": "3-5 years",
            "elementary": "5-10 years"
        }
        
        for pattern, age_group in age_patterns.items():
            if pattern in query_lower:
                profile.common_age_groups[age_group] = profile.common_age_groups.get(age_group, 0) + 1
        
        # Activity types
        activity_types = ["art", "craft", "science", "cooking", "physical", "game", "outdoor", "indoor", "sensory", "stem"]
        for activity_type in activity_types:
            if activity_type in query_lower:
                profile.favorite_activity_types[activity_type] = profile.favorite_activity_types.get(activity_type, 0) + 1
        
        # Preferences (only if not explicitly set)
        if profile.prefers_outdoor is None and ("outdoor" in query_lower or "outside" in query_lower):
            # Don't auto-set, just track frequency
            pass
    
    def get_conversation_history(
        self, 
        user_id: str, 
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get recent conversation history for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if session_id:
                rows = conn.execute(
                    """SELECT * FROM conversations 
                       WHERE user_id = ? AND session_id = ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (user_id, session_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM conversations 
                       WHERE user_id = ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (user_id, limit)
                ).fetchall()
            
            return [dict(row) for row in rows]
    
    def get_user_context_for_prompt(self, user_id: str) -> str:
        """Get user context formatted for LLM prompts."""
        profile = self.get_profile(user_id)
        if profile:
            return profile.to_prompt_context()
        return ""
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get user statistics."""
        profile = self.get_profile(user_id)
        if not profile:
            return {"interactions": 0}
        
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            schedule_count = conn.execute(
                "SELECT COUNT(*) FROM schedules WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            return {
                "interactions": row[0] if row else 0,
                "saved_schedules": schedule_count[0] if schedule_count else 0,
                "profile_interaction_count": profile.interaction_count,
                "common_age_groups": profile.common_age_groups,
                "favorite_activity_types": profile.favorite_activity_types,
                "preferences_set": bool(profile.default_age_group or profile.program_type)
            }
