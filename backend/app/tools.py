"""
Tools for function calling.
These are capabilities the AI can invoke to interact with external systems.
"""

import os
import json
from typing import Dict, List, Optional, Callable
from datetime import datetime


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
        List of tool schemas
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "search_activities",
                "description": "Search the activity database for activities matching criteria",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query describing what kind of activities are needed"
                        },
                        "activity_type": {
                            "type": "string",
                            "enum": ["Art", "Craft", "Science", "Cooking", "Physical", "Game", "Music", "Drama"],
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
                "name": "check_weather",
                "description": "Check the weather forecast for planning outdoor activities",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location for weather check (default: user's location)"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days to forecast",
                            "default": 1
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_activity",
                "description": "Generate a new activity idea based on constraints",
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
                        "duration": {
                            "type": "string",
                            "description": "Expected duration (e.g., '30 minutes', '1 hour')"
                        }
                    },
                    "required": ["description"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_to_schedule",
                "description": "Add an activity to the current schedule being built",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "activity_id": {
                            "type": "string",
                            "description": "ID of the activity to add"
                        },
                        "time_slot": {
                            "type": "string",
                            "description": "Time slot (e.g., '9:00 AM', 'afternoon')"
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for the activity (YYYY-MM-DD)"
                        }
                    },
                    "required": ["activity_id", "time_slot"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_user_preferences",
                "description": "Get the user's preferences and planning patterns",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]


def execute_tool(tool_name: str, parameters: Dict) -> Dict:
    """
    Execute a tool by name.
    
    Args:
        tool_name: Name of the tool to execute
        parameters: Tool parameters
    
    Returns:
        Tool execution result
    """
    if tool_name in tools:
        try:
            return tools[tool_name](**parameters)
        except Exception as e:
            return {"error": str(e)}
    else:
        return {"error": f"Unknown tool: {tool_name}"}


# Tool implementations

@register_tool("search_activities")
def search_activities_tool(
    query: str,
    activity_type: Optional[str] = None,
    age_group: Optional[str] = None,
    limit: int = 5
) -> Dict:
    """
    Search for activities.
    
    Note: This is a placeholder. In the real implementation,
    this would call the vector store.
    """
    return {
        "status": "success",
        "query": query,
        "filters": {
            "type": activity_type,
            "age_group": age_group
        },
        "results": [],
        "note": "This is a placeholder. Real implementation would query Pinecone."
    }


@register_tool("check_weather")
def check_weather_tool(
    location: Optional[str] = None,
    days: int = 1
) -> Dict:
    """
    Check weather forecast.
    
    Placeholder implementation. Would integrate with weather API.
    """
    # Default to Lansing, MI if no location provided
    location = location or "Lansing, MI"
    
    return {
        "status": "success",
        "location": location,
        "forecast": [
            {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "condition": "sunny",  # Placeholder
                "temperature": 72,
                "outdoor_friendly": True,
                "note": "Weather data is simulated. Integrate with OpenWeatherMap or similar."
            }
        ]
    }


@register_tool("generate_activity")
def generate_activity_tool(
    description: str,
    age_group: Optional[str] = None,
    supplies: Optional[List[str]] = None,
    duration: Optional[str] = None
) -> Dict:
    """
    Generate a new activity.
    
    Placeholder. Real implementation would call LLM to generate.
    """
    return {
        "status": "success",
        "generated": {
            "title": f"Generated: {description[:30]}...",
            "description": description,
            "target_age": age_group or "All ages",
            "supplies_needed": supplies or ["Paper", "Markers"],
            "estimated_duration": duration or "30 minutes",
            "note": "This is a placeholder. Real implementation would use LLM generation."
        }
    }


@register_tool("add_to_schedule")
def add_to_schedule_tool(
    activity_id: str,
    time_slot: str,
    date: Optional[str] = None
) -> Dict:
    """
    Add activity to schedule.
    
    Placeholder. Would integrate with scheduling system.
    """
    return {
        "status": "success",
        "activity_id": activity_id,
        "scheduled_for": {
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "time": time_slot
        },
        "note": "Activity added to schedule (placeholder)"
    }


@register_tool("get_user_preferences")
def get_user_preferences_tool() -> Dict:
    """Get user preferences."""
    return {
        "status": "success",
        "preferences": {
            "default_age_group": "8-10 years",
            "preferred_activity_types": ["Art", "Science", "Physical"],
            "typical_schedule": {
                "start_time": "9:00 AM",
                "end_time": "3:00 PM"
            },
            "planning_preferences": {
                "low_prep_preferred": True,
                "outdoor_when_possible": True
            }
        },
        "note": "Placeholder preferences. Real implementation would fetch from memory."
    }
