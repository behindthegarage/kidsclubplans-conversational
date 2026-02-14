"""Database models for user profiles, schedules, and preferences."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# Schedule Models
# =============================================================================

class ScheduleActivity(BaseModel):
    """An activity within a schedule with timing information."""
    activity_id: Optional[str] = Field(None, description="ID from activity database if available")
    title: str = Field(..., description="Activity title")
    description: Optional[str] = None
    start_time: str = Field(..., description="Start time (e.g., '09:00')")
    end_time: str = Field(..., description="End time (e.g., '10:30')")
    duration_minutes: int = Field(..., ge=5, le=300)
    activity_type: Optional[str] = None
    supplies_needed: Optional[List[str]] = None
    indoor_outdoor: Optional[str] = Field(None, description="indoor, outdoor, or either")
    notes: Optional[str] = None


class Schedule(BaseModel):
    """A complete daily schedule."""
    id: Optional[str] = None
    user_id: str
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    title: Optional[str] = None
    age_group: Optional[str] = None
    duration_hours: Optional[int] = None
    activities: List[ScheduleActivity] = Field(default_factory=list)
    weather_considered: Optional[Dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ScheduleCreateRequest(BaseModel):
    """Request to create a new schedule."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    title: Optional[str] = None
    age_group: Optional[str] = None
    duration_hours: Optional[int] = None
    activities: List[ScheduleActivity] = Field(default_factory=list)
    preferences: Optional[Dict[str, Any]] = None


# =============================================================================
# Weather Models
# =============================================================================

class WeatherData(BaseModel):
    """Weather information for activity planning."""
    location: str
    date: str
    temperature_f: Optional[float] = None
    temperature_c: Optional[float] = None
    conditions: str = Field(..., description="e.g., 'sunny', 'cloudy', 'rain'")
    description: Optional[str] = None
    precipitation_chance: Optional[int] = Field(None, ge=0, le=100)
    humidity: Optional[int] = Field(None, ge=0, le=100)
    wind_speed: Optional[float] = None
    outdoor_suitable: bool = Field(True, description="Whether outdoor activities are suitable")
    uv_index: Optional[float] = None
    cached_at: Optional[str] = None


class WeatherRequest(BaseModel):
    """Request to check weather."""
    location: str = Field(default="Lansing, MI", description="Location for weather check")
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format (default: today)")


# =============================================================================
# Tool Result Models
# =============================================================================

class ToolResult(BaseModel):
    """Result of a tool execution."""
    tool_name: str
    parameters: Dict[str, Any]
    result: Dict[str, Any]
    success: bool = True
    error_message: Optional[str] = None
    executed_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# Activity Search Models
# =============================================================================

class ActivitySearchConstraints(BaseModel):
    """Constraints for searching activities."""
    age_group: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=5, le=300)
    supplies_available: Optional[List[str]] = None
    indoor_outdoor: Optional[str] = Field(None, description="indoor, outdoor, or either")
    theme: Optional[str] = None
    low_prep_only: bool = False
    limit: int = Field(default=5, ge=1, le=20)


class ScheduleGenerateRequest(BaseModel):
    """Request to generate a schedule."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    age_group: str
    duration_hours: int = Field(..., ge=1, le=12)
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    location: Optional[str] = "Lansing, MI"
    include_weather: bool = True


# =============================================================================
# User Profile Models
# =============================================================================

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
