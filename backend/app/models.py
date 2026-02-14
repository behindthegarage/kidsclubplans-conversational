"""Database models for user profiles and preferences."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """User profile with preferences and patterns."""
    
    user_id: str = Field(..., description="Unique user identifier (from session cookie)")
    
    # Basic preferences
    default_age_group: Optional[str] = Field(None, description="e.g., '8-10 year olds'")
    program_type: Optional[str] = Field(None, description="before_care, after_care, full_day")
    group_size: Optional[int] = Field(None, ge=1, le=100)
    
    # Activity preferences
    prefers_low_prep: bool = Field(False, description="Prefer minimal setup activities")
    prefers_outdoor: Optional[bool] = Field(None, description="Outdoor preference (None = no preference)")
    prefers_indoor: Optional[bool] = Field(None, description="Indoor preference")
    preferred_duration_minutes: Optional[int] = Field(None, ge=5, le=120)
    
    # Supply constraints (what they typically have)
    typical_supplies: list[str] = Field(default_factory=list, description="Common supplies available")
    
    # Schedule patterns
    usual_break_times: list[str] = Field(default_factory=list, description="e.g., ['10:00', '14:00']")
    typical_activity_length: Optional[str] = Field(None, description="30 min, 1 hour, etc.")
    
    # Tracked patterns (auto-learned)
    common_age_groups: dict[str, int] = Field(default_factory=dict, description="Frequency of age groups mentioned")
    favorite_activity_types: dict[str, int] = Field(default_factory=dict, description="Frequency of activity types")
    
    # Metadata
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_interaction: Optional[str] = None
    interaction_count: int = 0
    
    def to_prompt_context(self) -> str:
        """Convert profile to a context string for LLM prompts."""
        parts = []
        
        if self.default_age_group:
            parts.append(f"User typically plans activities for: {self.default_age_group}")
        
        if self.program_type:
            parts.append(f"Program type: {self.program_type.replace('_', ' ')}")
        
        if self.group_size:
            parts.append(f"Typical group size: {self.group_size} children")
        
        if self.prefers_low_prep:
            parts.append("User prefers LOW-PREP activities (minimal setup time)")
        
        if self.prefers_outdoor:
            parts.append("User prefers OUTDOOR activities when weather permits")
        elif self.prefers_indoor:
            parts.append("User prefers INDOOR activities")
        
        if self.preferred_duration_minutes:
            parts.append(f"Preferred activity duration: {self.preferred_duration_minutes} minutes")
        
        if self.typical_supplies:
            supplies_str = ", ".join(self.typical_supplies[:5])
            parts.append(f"User typically has these supplies: {supplies_str}")
        
        # Top activity types
        if self.favorite_activity_types:
            top_types = sorted(self.favorite_activity_types.items(), key=lambda x: x[1], reverse=True)[:3]
            types_str = ", ".join([t[0] for t in top_types])
            parts.append(f"User frequently requests: {types_str} activities")
        
        if parts:
            return "\n".join(["User Profile:"] + [f"- {p}" for p in parts])
        return ""


class UserProfileUpdate(BaseModel):
    """Update model for user profile (all fields optional)."""
    
    default_age_group: Optional[str] = None
    program_type: Optional[str] = None
    group_size: Optional[int] = Field(None, ge=1, le=100)
    prefers_low_prep: Optional[bool] = None
    prefers_outdoor: Optional[bool] = None
    prefers_indoor: Optional[bool] = None
    preferred_duration_minutes: Optional[int] = Field(None, ge=5, le=120)
    typical_supplies: Optional[list[str]] = None
    usual_break_times: Optional[list[str]] = None
    typical_activity_length: Optional[str] = None
