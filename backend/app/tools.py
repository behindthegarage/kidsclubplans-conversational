"""
Tools for function calling.
These are capabilities the AI can invoke to interact with external systems.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta

from .models import (
    WeatherData, Schedule, ScheduleActivity, ToolResult,
    ActivitySearchConstraints
)
from .weather import check_weather, get_weather_client

logger = logging.getLogger("kcp.tools")

# Tool registry
tools: Dict[str, Callable] = {}


def register_tool(name: str):
    """Decorator to register a tool."""
    def decorator(func: Callable):
        tools[name] = func
        return func
    return decorator


def get_available_tools() -> List[Dict]:
    """
    Get tool definitions for OpenAI/Anthropic function calling.
    
    Returns:
        List of tool schemas in OpenAI format
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "check_weather",
                "description": "Check the weather forecast for planning outdoor activities. Returns temperature, conditions, and whether outdoor activities are suitable.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location for weather check (e.g., 'Lansing, MI', 'Detroit, MI'). Default: Lansing, MI"
                        },
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format. Default: today"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_activities_with_constraints",
                "description": "Search the activity database with multiple constraints including age group, duration, supplies available, and indoor/outdoor preference.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "age_group": {
                            "type": "string",
                            "description": "Target age group (e.g., '5-6 years', '8-10 years', '8-year-olds')"
                        },
                        "duration_minutes": {
                            "type": "integer",
                            "description": "Desired activity duration in minutes (5-300)"
                        },
                        "supplies_available": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of supplies the user has available (e.g., ['paper', 'markers', 'scissors'])"
                        },
                        "indoor_outdoor": {
                            "type": "string",
                            "enum": ["indoor", "outdoor", "either"],
                            "description": "Whether the activity should be indoor, outdoor, or either"
                        },
                        "theme": {
                            "type": "string",
                            "description": "Optional theme for activities (e.g., 'space', 'animals', 'holiday')"
                        },
                        "low_prep_only": {
                            "type": "boolean",
                            "description": "If true, only return activities that require minimal preparation",
                            "default": False
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5
                        }
                    },
                    "required": ["age_group"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_activities",
                "description": "Simple search for activities matching a query. Use search_activities_with_constraints for more specific filtering.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query describing what kind of activities are needed"
                        },
                        "activity_type": {
                            "type": "string",
                            "enum": ["Art", "Craft", "Science", "Cooking", "Physical", "Game", "Music", "Drama", "STEM", "Outdoor Game", "Indoor Game"],
                            "description": "Optional filter by activity type"
                        },
                        "age_group": {
                            "type": "string",
                            "description": "Target age group (e.g., '5-6 years', '8-10 years')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_schedule",
                "description": "Generate a complete daily schedule with activities, transitions, and breaks. Weather-aware for outdoor/indoor switching.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format for the schedule"
                        },
                        "age_group": {
                            "type": "string",
                            "description": "Target age group (e.g., '8-year-olds', '5-6 years')"
                        },
                        "duration_hours": {
                            "type": "integer",
                            "description": "Total duration of the schedule in hours (1-12)"
                        },
                        "preferences": {
                            "type": "object",
                            "description": "Planning preferences",
                            "properties": {
                                "start_time": {
                                    "type": "string",
                                    "description": "Start time (e.g., '09:00')"
                                },
                                "theme": {
                                    "type": "string",
                                    "description": "Optional theme for activities"
                                },
                                "low_prep": {
                                    "type": "boolean",
                                    "description": "Prefer low-prep activities"
                                },
                                "include_outdoor": {
                                    "type": "boolean",
                                    "description": "Include outdoor activities if weather permits"
                                },
                                "supplies_available": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Supplies the user has available"
                                },
                                "break_times": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Preferred break times (e.g., ['10:30', '14:00'])"
                                }
                            }
                        },
                        "location": {
                            "type": "string",
                            "description": "Location for weather consideration (default: Lansing, MI)"
                        }
                    },
                    "required": ["date", "age_group", "duration_hours"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_activity",
                "description": "Generate a new activity idea based on constraints when no existing activities match. Creates a complete activity with instructions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Description of what kind of activity to create"
                        },
                        "age_group": {
                            "type": "string",
                            "description": "Target age group"
                        },
                        "supplies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Available supplies"
                        },
                        "duration_minutes": {
                            "type": "integer",
                            "description": "Expected duration in minutes"
                        },
                        "indoor_outdoor": {
                            "type": "string",
                            "enum": ["indoor", "outdoor", "either"],
                            "description": "Where the activity takes place"
                        }
                    },
                    "required": ["description", "age_group"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_user_preferences",
                "description": "Get the current user's preferences and planning patterns from their profile",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]


def execute_tool(tool_name: str, parameters: Dict, context: Optional[Dict] = None) -> ToolResult:
    """
    Execute a tool by name.
    
    Args:
        tool_name: Name of the tool to execute
        parameters: Tool parameters
        context: Optional context (user_id, memory_manager, vector_store, etc.)
    
    Returns:
        Tool execution result
    """
    logger.info(f"Executing tool: {tool_name} with params: {parameters}")
    
    if tool_name not in tools:
        return ToolResult(
            tool_name=tool_name,
            parameters=parameters,
            result={},
            success=False,
            error_message=f"Unknown tool: {tool_name}"
        )
    
    try:
        # Pass context if the tool accepts it
        if context:
            result = tools[tool_name](**parameters, _context=context)
        else:
            result = tools[tool_name](**parameters)
        
        return ToolResult(
            tool_name=tool_name,
            parameters=parameters,
            result=result if isinstance(result, dict) else {"result": result},
            success=True
        )
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return ToolResult(
            tool_name=tool_name,
            parameters=parameters,
            result={},
            success=False,
            error_message=str(e)
        )


# =============================================================================
# Tool Implementations
# =============================================================================

@register_tool("check_weather")
def check_weather_tool(
    location: Optional[str] = None,
    date: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Check weather forecast.
    
    Returns weather data suitable for activity planning decisions.
    """
    weather = check_weather(location or "Lansing, MI", date)
    
    # Add planning-specific guidance
    planning_note = ""
    if weather.outdoor_suitable:
        if weather.conditions == "sunny":
            planning_note = "Great day for outdoor activities!"
        else:
            planning_note = "Outdoor activities are suitable today."
    else:
        if weather.conditions in ["rain", "snow", "storm"]:
            planning_note = f"Indoor activities recommended due to {weather.conditions}."
        elif weather.temperature_f and weather.temperature_f < 32:
            planning_note = "Very cold - keep activities indoors or brief outdoor periods."
        elif weather.temperature_f and weather.temperature_f > 90:
            planning_note = "Very hot - stay hydrated and prefer indoor/cool activities."
        else:
            planning_note = "Indoor activities recommended for today."
    
    return {
        "location": weather.location,
        "date": weather.date,
        "temperature": {
            "fahrenheit": weather.temperature_f,
            "celsius": weather.temperature_c
        },
        "conditions": weather.conditions,
        "description": weather.description,
        "precipitation_chance": weather.precipitation_chance,
        "humidity": weather.humidity,
        "wind_speed": weather.wind_speed,
        "outdoor_suitable": weather.outdoor_suitable,
        "planning_note": planning_note
    }


@register_tool("search_activities")
def search_activities_tool(
    query: str,
    activity_type: Optional[str] = None,
    age_group: Optional[str] = None,
    limit: int = 5,
    _context: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Search for activities in the database.
    """
    vector_store = _context.get("vector_store") if _context else None
    
    if not vector_store:
        return {
            "success": False,
            "error": "Vector store not available",
            "activities": []
        }
    
    try:
        # Import here to avoid circular dependency
        from .rag import search_activities as rag_search
        
        # Build enhanced query with age group context
        enhanced_query = query
        if age_group:
            enhanced_query = f"{query} for {age_group}"
        
        activities = rag_search(
            vector_store=vector_store,
            query=enhanced_query,
            limit=limit,
            activity_type=activity_type
        )
        
        # Format activities for response
        formatted = []
        for act in activities:
            formatted.append({
                "id": act.get("id"),
                "title": act.get("title", "Untitled"),
                "type": act.get("type"),
                "description": act.get("description"),
                "age_group": act.get("development_age_group"),
                "supplies": act.get("supplies"),
                "score": act.get("score"),
                "match_quality": "high" if act.get("score", 0) > 0.8 else "medium" if act.get("score", 0) > 0.6 else "low"
            })
        
        return {
            "success": True,
            "query": query,
            "age_group": age_group,
            "activity_type": activity_type,
            "count": len(formatted),
            "activities": formatted
        }
        
    except Exception as e:
        logger.error(f"Activity search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "activities": []
        }


@register_tool("search_activities_with_constraints")
def search_activities_with_constraints_tool(
    age_group: str,
    duration_minutes: Optional[int] = None,
    supplies_available: Optional[List[str]] = None,
    indoor_outdoor: Optional[str] = None,
    theme: Optional[str] = None,
    low_prep_only: bool = False,
    limit: int = 5,
    _context: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Search activities with multiple constraints.
    Enhanced RAG with fallback to generation if no matches found.
    """
    vector_store = _context.get("vector_store") if _context else None
    
    # Build search query from constraints
    query_parts = []
    if theme:
        query_parts.append(theme)
    if indoor_outdoor == "indoor":
        query_parts.append("indoor")
    elif indoor_outdoor == "outdoor":
        query_parts.append("outdoor")
    if low_prep_only:
        query_parts.append("low prep easy setup")
    
    query = " ".join(query_parts) if query_parts else "activities"
    
    results = []
    
    # Try database search if available
    if vector_store:
        try:
            from .rag import search_activities as rag_search
            
            enhanced_query = f"{query} for {age_group}"
            if duration_minutes:
                enhanced_query += f" {duration_minutes} minutes"
            
            activities = rag_search(vector_store, enhanced_query, limit=limit * 2)  # Get more for filtering
            
            # Filter by supplies if specified
            if supplies_available and activities:
                filtered = []
                for act in activities:
                    supplies_needed = act.get("supplies", "")
                    if supplies_needed:
                        # Check if user has at least some of the supplies
                        supplies_lower = [s.lower() for s in supplies_available]
                        has_supplies = any(
                            supply.lower() in supplies_lower 
                            for supply in supplies_needed.split(",")
                        )
                        if has_supplies or not supplies_needed:
                            filtered.append(act)
                    else:
                        filtered.append(act)
                activities = filtered
            
            # Format results
            for act in activities[:limit]:
                results.append({
                    "id": act.get("id"),
                    "title": act.get("title", "Untitled"),
                    "type": act.get("type"),
                    "description": act.get("description"),
                    "age_group": act.get("development_age_group"),
                    "supplies": act.get("supplies"),
                    "instructions": act.get("instructions"),
                    "score": act.get("score"),
                    "source": "database"
                })
                
        except Exception as e:
            logger.error(f"Constraint search failed: {e}")
    
    # If no results found, suggest generating a new activity
    should_generate = len(results) == 0 or (len(results) < 2 and low_prep_only)
    
    return {
        "success": True,
        "constraints": {
            "age_group": age_group,
            "duration_minutes": duration_minutes,
            "supplies_available": supplies_available,
            "indoor_outdoor": indoor_outdoor,
            "theme": theme,
            "low_prep_only": low_prep_only
        },
        "count": len(results),
        "activities": results,
        "fallback_suggested": should_generate,
        "fallback_message": "No matching activities found in database. Consider using generate_activity to create a custom activity." if should_generate else None
    }


@register_tool("generate_schedule")
def generate_schedule_tool(
    date: str,
    age_group: str,
    duration_hours: int,
    preferences: Optional[Dict[str, Any]] = None,
    location: Optional[str] = None,
    _context: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate a complete daily schedule with activities and timing.
    Weather-aware for outdoor/indoor decisions.
    """
    preferences = preferences or {}
    location = location or "Lansing, MI"
    
    # Check weather first
    weather_data = check_weather(location, date)
    
    # Determine if we can include outdoor activities
    outdoor_friendly = weather_data.outdoor_suitable and preferences.get("include_outdoor", True)
    
    # Parse age group for better search
    age_num = _extract_age_number(age_group)
    
    # Search for activities
    vector_store = _context.get("vector_store") if _context else None
    activities_pool = []
    
    if vector_store:
        from .rag import search_activities as rag_search
        
        # Search for different types of activities
        search_queries = [
            f"opening circle morning activities {age_group}",
            f"active games physical activities {age_group}",
            f"art craft creative activities {age_group}",
            f"STEM science activities {age_group}",
            f"calm quiet activities {age_group}",
            f"closing wrap up activities {age_group}"
        ]
        
        if preferences.get("theme"):
            search_queries.append(f"{preferences['theme']} activities {age_group}")
        
        for query in search_queries:
            try:
                acts = rag_search(vector_store, query, limit=3)
                for act in acts:
                    if act.get("id") not in [a.get("id") for a in activities_pool]:
                        activities_pool.append(act)
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
    
    # Build the schedule
    schedule = _build_schedule(
        date=date,
        age_group=age_group,
        duration_hours=duration_hours,
        preferences=preferences,
        weather=weather_data,
        activities_pool=activities_pool
    )
    
    return {
        "success": True,
        "schedule": {
            "date": date,
            "age_group": age_group,
            "duration_hours": duration_hours,
            "location": location,
            "weather": {
                "conditions": weather_data.conditions,
                "temperature_f": weather_data.temperature_f,
                "outdoor_suitable": weather_data.outdoor_suitable,
                "planning_note": _get_weather_planning_note(weather_data)
            },
            "activities": [act.model_dump() for act in schedule.activities],
            "total_activities": len(schedule.activities),
            "indoor_outdoor_mix": _calculate_mix(schedule.activities)
        }
    }


@register_tool("generate_activity")
def generate_activity_tool(
    description: str,
    age_group: str,
    supplies: Optional[List[str]] = None,
    duration_minutes: Optional[int] = None,
    indoor_outdoor: Optional[str] = "either",
    **kwargs
) -> Dict[str, Any]:
    """
    Generate a new activity idea.
    Note: This is a template generator. In production, this would call an LLM.
    """
    # Generate a plausible activity based on inputs
    supplies = supplies or ["paper", "markers", "scissors"]
    duration = duration_minutes or 30
    
    # Simple activity templates based on theme
    activity_templates = {
        "space": {
            "title": "Space Explorer Mission",
            "description": f"An imaginative {duration}-minute space adventure where children become astronauts exploring new planets.",
            "supplies": ", ".join(supplies[:4]),
            "instructions": f"1. Set up a 'space station' area. 2. Give each child a 'mission' to complete. 3. Use {supplies[0] if supplies else 'materials'} to create space artifacts. 4. Share discoveries with the group.",
            "indoor_outdoor": "indoor"
        },
        "animal": {
            "title": "Animal Habitat Designers",
            "description": f"Children design and build habitats for their favorite animals over {duration} minutes.",
            "supplies": ", ".join(supplies[:4]),
            "instructions": f"1. Choose an animal. 2. Research (or recall) its habitat needs. 3. Use {supplies[0] if supplies else 'materials'} to create the habitat. 4. Present to the group.",
            "indoor_outdoor": "indoor"
        },
        "art": {
            "title": f"Creative Expression Studio ({duration} min)",
            "description": f"Open-ended art exploration for {age_group} using available materials.",
            "supplies": ", ".join(supplies[:4]),
            "instructions": f"1. Set up art stations. 2. Introduce materials. 3. Allow free exploration for {duration} minutes. 4. Gallery walk to share creations.",
            "indoor_outdoor": "either"
        },
        "science": {
            "title": "Young Scientists Lab",
            "description": f"Hands-on science exploration perfect for {age_group} in {duration} minutes.",
            "supplies": ", ".join(supplies[:4]),
            "instructions": f"1. Present the challenge/question. 2. Gather materials. 3. Experiment and observe. 4. Discuss findings as a group.",
            "indoor_outdoor": "indoor"
        }
    }
    
    # Find best template match
    description_lower = description.lower()
    template = None
    
    for key, tmpl in activity_templates.items():
        if key in description_lower:
            template = tmpl
            break
    
    if not template:
        # Default template
        template = {
            "title": f"Custom Activity: {description[:30]}...",
            "description": f"A {duration}-minute activity designed for {age_group}.",
            "supplies": ", ".join(supplies[:4]),
            "instructions": f"1. Introduce the activity. 2. Gather materials ({', '.join(supplies[:3])}). 3. Engage children for {duration} minutes. 4. Reflect and share.",
            "indoor_outdoor": indoor_outdoor
        }
    
    return {
        "success": True,
        "generated": True,
        "activity": {
            "title": template["title"],
            "description": template["description"],
            "target_age": age_group,
            "duration_minutes": duration,
            "supplies_needed": template["supplies"],
            "instructions": template["instructions"],
            "indoor_outdoor": template["indoor_outdoor"],
            "source": "generated"
        }
    }


@register_tool("get_user_preferences")
def get_user_preferences_tool(
    _context: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """Get user preferences from memory manager."""
    memory_manager = _context.get("memory_manager") if _context else None
    user_id = _context.get("user_id") if _context else None
    
    if memory_manager and user_id:
        profile = memory_manager.get_profile(user_id)
        if profile:
            return {
                "success": True,
                "preferences": {
                    "default_age_group": profile.default_age_group,
                    "program_type": profile.program_type,
                    "group_size": profile.group_size,
                    "prefers_low_prep": profile.prefers_low_prep,
                    "prefers_outdoor": profile.prefers_outdoor,
                    "typical_supplies": profile.typical_supplies,
                    "usual_break_times": profile.usual_break_times,
                    "favorite_activity_types": profile.favorite_activity_types
                }
            }
    
    # Default preferences
    return {
        "success": True,
        "preferences": {
            "default_age_group": None,
            "program_type": None,
            "group_size": None,
            "prefers_low_prep": False,
            "prefers_outdoor": None,
            "typical_supplies": [],
            "usual_break_times": [],
            "favorite_activity_types": {}
        },
        "note": "No user profile found. Using defaults."
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _extract_age_number(age_group: str) -> int:
    """Extract an age number from age group string."""
    import re
    numbers = re.findall(r'\d+', age_group)
    if numbers:
        return int(numbers[0])
    return 8  # Default


def _get_weather_planning_note(weather: WeatherData) -> str:
    """Generate a planning note based on weather."""
    if not weather.outdoor_suitable:
        if weather.conditions in ["rain", "snow", "storm"]:
            return f"Indoor activities recommended - {weather.conditions} expected."
        return "Indoor activities recommended due to weather conditions."
    
    if weather.temperature_f and weather.temperature_f > 85:
        return "Hot day - ensure hydration and shade for outdoor activities."
    
    return "Great day for a mix of indoor and outdoor activities!"


def _calculate_mix(activities: List[ScheduleActivity]) -> Dict[str, int]:
    """Calculate the indoor/outdoor mix of activities."""
    indoor = sum(1 for a in activities if a.indoor_outdoor == "indoor")
    outdoor = sum(1 for a in activities if a.indoor_outdoor == "outdoor")
    either = sum(1 for a in activities if a.indoor_outdoor in ["either", None])
    
    return {
        "indoor": indoor,
        "outdoor": outdoor,
        "either": either
    }


def _build_schedule(
    date: str,
    age_group: str,
    duration_hours: int,
    preferences: Dict[str, Any],
    weather: WeatherData,
    activities_pool: List[Dict]
) -> Schedule:
    """Build a complete schedule with timing."""
    
    start_time_str = preferences.get("start_time", "09:00")
    break_times = preferences.get("break_times", ["10:30", "14:00"])
    
    # Parse start time
    start_hour, start_minute = map(int, start_time_str.split(":"))
    current_time = datetime.strptime(f"{date} {start_time_str}", "%Y-%m-%d %H:%M")
    end_time = current_time + timedelta(hours=duration_hours)
    
    activities = []
    activity_idx = 0
    
    # Add opening circle (10 min)
    activities.append(ScheduleActivity(
        title="Opening Circle & Check-in",
        description="Welcome, attendance, and daily announcements",
        start_time=current_time.strftime("%H:%M"),
        end_time=(current_time + timedelta(minutes=10)).strftime("%H:%M"),
        duration_minutes=10,
        activity_type="Social-Emotional",
        indoor_outdoor="indoor"
    ))
    current_time += timedelta(minutes=10)
    
    # Add transition buffer (5 min)
    current_time += timedelta(minutes=5)
    
    # Fill with activities from pool
    outdoor_friendly = weather.outdoor_suitable
    theme = preferences.get("theme", "").lower()
    
    while current_time < end_time - timedelta(minutes=20):
        # Check if it's break time
        current_time_str = current_time.strftime("%H:%M")
        for bt in break_times:
            if abs((datetime.strptime(bt, "%H:%M") - datetime.strptime(current_time_str, "%H:%M")).total_seconds()) < 900:  # Within 15 min
                # Add break
                activities.append(ScheduleActivity(
                    title="Break / Snack Time",
                    description="Restroom, water, and snack break",
                    start_time=current_time.strftime("%H:%M"),
                    end_time=(current_time + timedelta(minutes=15)).strftime("%H:%M"),
                    duration_minutes=15,
                    activity_type="Break",
                    indoor_outdoor="indoor"
                ))
                current_time += timedelta(minutes=15)
                current_time += timedelta(minutes=5)  # Transition
                break
        
        if current_time >= end_time - timedelta(minutes=20):
            break
        
        # Find a suitable activity
        selected = None
        for act in activities_pool[activity_idx:]:
            activity_idx += 1
            act_type = (act.get("type") or "").lower()
            
            # Check outdoor suitability
            is_outdoor = "outdoor" in act_type or "field" in act_type
            if is_outdoor and not outdoor_friendly:
                continue
            
            selected = act
            break
        
        if not selected and activities_pool:
            # Wrap around or use generic
            selected = activities_pool[activity_idx % len(activities_pool)]
            activity_idx += 1
        
        if selected:
            duration = 30  # Default 30 min
            if age_group and "5" in age_group:
                duration = 20  # Shorter for younger kids
            
            activities.append(ScheduleActivity(
                activity_id=str(selected.get("id")),
                title=selected.get("title", "Activity"),
                description=selected.get("description", "")[:100] + "..." if selected.get("description") else None,
                start_time=current_time.strftime("%H:%M"),
                end_time=(current_time + timedelta(minutes=duration)).strftime("%H:%M"),
                duration_minutes=duration,
                activity_type=selected.get("type"),
                indoor_outdoor="outdoor" if "outdoor" in (selected.get("type") or "").lower() else "indoor"
            ))
            current_time += timedelta(minutes=duration)
        else:
            # Add filler activity
            activities.append(ScheduleActivity(
                title="Free Play",
                description="Child-directed play and exploration",
                start_time=current_time.strftime("%H:%M"),
                end_time=(current_time + timedelta(minutes=30)).strftime("%H:%M"),
                duration_minutes=30,
                activity_type="Free Play",
                indoor_outdoor="either"
            ))
            current_time += timedelta(minutes=30)
        
        # Add transition
        current_time += timedelta(minutes=5)
    
    # Add closing circle (10 min)
    if current_time <= end_time:
        activities.append(ScheduleActivity(
            title="Closing Circle & Reflection",
            description="Share highlights of the day and say goodbye",
            start_time=current_time.strftime("%H:%M"),
            end_time=(current_time + timedelta(minutes=10)).strftime("%H:%M"),
            duration_minutes=10,
            activity_type="Social-Emotional",
            indoor_outdoor="indoor"
        ))
    
    return Schedule(
        user_id="temp",
        date=date,
        title=f"Schedule for {date}",
        age_group=age_group,
        duration_hours=duration_hours,
        activities=activities,
        weather_considered={
            "conditions": weather.conditions,
            "outdoor_suitable": weather.outdoor_suitable
        }
    )
