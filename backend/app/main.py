"""
KidsClubPlans Conversational Backend
FastAPI app with streaming chat via Server-Sent Events
"""

import json
import logging
import os
import re
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .chat import ChatRequest as EngineChatRequest
from .chat import Message as EngineMessage
from .chat import chat_endpoint
from .memory import MemoryManager
from .models import (
    UserProfile,
    UserProfileUpdate,
    Schedule,
    ScheduleCreateRequest,
    WeatherRequest,
    ScheduleGenerateRequest
)
from .observability import (
    classify_error,
    configure_logging,
    log_event,
    metrics,
    request_id_ctx,
)
from .rag import initialize_vector_store
from .safety import (
    chat_rate_limiter, 
    normalize_text, 
    SlidingWindowRateLimiter,
    sanitize_activity_title,
    sanitize_activity_description,
    sanitize_schedule_title,
    sanitize_activity_data,
    sanitize_text_input
)

load_dotenv()
configure_logging()
logger = logging.getLogger("kcp.api")


# Global instances (single architecture)
vector_store = None
memory_manager: Optional[MemoryManager] = None

# Rate limiters for save endpoints (PR7 security)
# More permissive than chat but still prevent abuse
schedule_save_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)  # 10 saves/min
activity_save_limiter = SlidingWindowRateLimiter(max_requests=15, window_seconds=60)  # 15 saves/min
delete_schedule_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)  # 10 deletes/min


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global vector_store, memory_manager

    # Fail-fast env checks for core runtime
    missing = [
        name
        for name in ["OPENAI_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX_NAME"]
        if not os.getenv(name)
    ]
    if missing:
        metrics.incr("startup_errors_total")
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    vector_store = initialize_vector_store()
    memory_manager = MemoryManager()
    log_event(logger, logging.INFO, "startup_complete", vector_store_initialized=vector_store is not None)

    yield

    log_event(logger, logging.INFO, "shutdown_complete")


app = FastAPI(
    title="KidsClubPlans Conversational API",
    description="AI-powered activity planning assistant with RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    token = request_id_ctx.set(req_id)
    started = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        metrics.incr("http_requests_total")
        metrics.incr("http_errors_total")
        metrics.incr(f"error_type_{classify_error(exc)}_total")
        log_event(
            logger,
            logging.ERROR,
            "request_failed",
            method=request.method,
            path=request.url.path,
            error_type=classify_error(exc),
            error=str(exc),
        )
        request_id_ctx.reset(token)
        raise

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    response.headers["X-Request-Id"] = req_id
    metrics.incr("http_requests_total")
    if response.status_code >= 500:
        metrics.incr("http_errors_total")

    log_event(
        logger,
        logging.INFO,
        "request_complete",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=elapsed_ms,
    )

    request_id_ctx.reset(token)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    error_type = classify_error(exc)
    metrics.incr("unhandled_exceptions_total")
    metrics.incr(f"error_type_{error_type}_total")
    log_event(logger, logging.ERROR, "unhandled_exception", error_type=error_type, error=str(exc))
    return Response(
        content=json.dumps({"error": {"type": error_type, "message": "Internal server error"}}),
        status_code=500,
        media_type="application/json",
    )


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None


class ActivitySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    activity_type: Optional[str] = None


def _get_or_create_session_user_id(request: Request) -> tuple[str, bool]:
    """Derive trusted user identity from signed-ish session cookie (server-side trust boundary)."""
    sid = request.cookies.get("kcp_sid")
    if sid:
        return sid, False
    return str(uuid.uuid4()), True


@app.get("/")
async def root():
    return {"status": "ok", "service": "kidsclubplans-conversational-api"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "vector_store_initialized": vector_store is not None,
        "memory_initialized": memory_manager is not None,
    }


@app.get("/metrics")
async def metrics_snapshot():
    """Basic in-memory metrics snapshot (PR7 hook point)."""
    return {"metrics": metrics.snapshot()}


@app.post("/chat")
async def chat_stream(request: ChatRequest, http_request: Request):
    """
    Streaming chat endpoint using SSE.

    Stream contract (PR2):
    - {"type": "content", "data": {"content": "..."}}
    - {"type": "activity", "data": {...activity...}}
    - {"type": "tool_call", "data": {...}}
    - {"type": "done", "data": {"conversation_id": "..."}}
    - {"type": "error", "data": {"message": "..."}}
    """
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")

    conversation_id = request.conversation_id or str(uuid.uuid4())
    trusted_user_id, is_new_session = _get_or_create_session_user_id(http_request)

    allowed, retry_after = chat_rate_limiter.allow(trusted_user_id)
    if not allowed:
        metrics.incr("rate_limited_requests_total")
        log_event(
            logger,
            logging.WARNING,
            "chat_rate_limited",
            conversation_id=conversation_id,
            retry_after=retry_after,
        )
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry in {retry_after}s")

    request.message = normalize_text(request.message)

    metrics.incr("chat_requests_total")
    log_event(
        logger,
        logging.INFO,
        "chat_request_received",
        conversation_id=conversation_id,
        new_session=is_new_session,
        message_chars=len(request.message),
    )

    engine_request = EngineChatRequest(
        messages=[EngineMessage(role="user", content=request.message)],
        user_id=trusted_user_id,
        session_id=conversation_id,
        conversation_id=conversation_id,
        stream=True,
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for chunk in chat_endpoint(engine_request, vector_store, memory_manager):
                yield chunk
        except Exception as e:
            error_type = classify_error(e)
            metrics.incr("chat_stream_errors_total")
            metrics.incr(f"error_type_{error_type}_total")
            log_event(
                logger,
                logging.ERROR,
                "chat_stream_failed",
                conversation_id=conversation_id,
                error_type=error_type,
                error=str(e),
            )
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e), 'error_type': error_type}})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'data': {'conversation_id': conversation_id}})}\n\n"

    response = StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

    if is_new_session:
        response.set_cookie(
            key="kcp_sid",
            value=trusted_user_id,
            httponly=True,
            samesite="lax",
            secure=os.getenv("ENVIRONMENT") == "production",
            max_age=60 * 60 * 24 * 30,
        )

    return response


@app.post("/activities/search")
async def search_activities(request: ActivitySearchRequest):
    """Search activities using vector store"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not initialized")

    try:
        from .rag import search_activities as do_search

        activities = do_search(
            vector_store=vector_store,
            query=request.query,
            limit=request.top_k,
            activity_type=request.activity_type,
        )
        return {"activities": activities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, http_request: Request):
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")

    trusted_user_id, _ = _get_or_create_session_user_id(http_request)
    history = memory_manager.get_conversation_history(user_id=trusted_user_id, session_id=conversation_id)
    return {"conversation_id": conversation_id, "messages": history}


@app.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str):
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")

    memory_manager.clear_session_context(conversation_id)
    return {"message": "Conversation context cleared"}


# Profile endpoints for Phase 2: Context & Memory
@app.get("/api/profile")
async def get_profile(http_request: Request):
    """Get current user's profile."""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    trusted_user_id, _ = _get_or_create_session_user_id(http_request)
    profile = memory_manager.get_profile(trusted_user_id)
    
    if profile:
        return profile.model_dump()
    return {"message": "No profile found. Create one with POST /api/profile"}


@app.post("/api/profile")
async def create_or_update_profile(request: UserProfileUpdate, http_request: Request):
    """Create or update user profile."""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    trusted_user_id, _ = _get_or_create_session_user_id(http_request)
    profile = memory_manager.update_profile(trusted_user_id, request)
    
    log_event(
        logger,
        logging.INFO,
        "profile_updated",
        user_id=trusted_user_id,
        fields_updated=list(request.model_dump(exclude_unset=True).keys())
    )
    
    return profile.model_dump()


@app.get("/api/profile/stats")
async def get_profile_stats(http_request: Request):
    """Get user statistics and learned patterns."""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    trusted_user_id, _ = _get_or_create_session_user_id(http_request)
    stats = memory_manager.get_user_stats(trusted_user_id)
    return stats


@app.get("/api/conversations")
async def get_user_conversations(http_request: Request, limit: int = 20):
    """Get user's conversation history across all sessions."""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    trusted_user_id, _ = _get_or_create_session_user_id(http_request)
    history = memory_manager.get_conversation_history(trusted_user_id, limit=limit)
    return {"conversations": history}


# =============================================================================
# Phase 3: Tools & Actions Endpoints
# =============================================================================

@app.post("/api/weather")
async def get_weather(request: WeatherRequest):
    """Get weather forecast for a location."""
    try:
        from .weather import check_weather
        import asyncio
        
        # Run sync function in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, check_weather, request.location, request.date)
        return result.model_dump()
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        raise HTTPException(status_code=500, detail=f"Weather service error: {str(e)}")


@app.post("/api/schedule/generate")
async def generate_schedule_endpoint(request: ScheduleGenerateRequest, http_request: Request):
    """Generate a schedule with activities."""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    trusted_user_id, _ = _get_or_create_session_user_id(http_request)
    
    # Get weather if requested
    weather_data = None
    if request.include_weather:
        try:
            from .weather import check_weather
            import asyncio
            loop = asyncio.get_event_loop()
            weather = await loop.run_in_executor(None, check_weather, request.location, request.date)
            weather_data = weather.model_dump()
        except Exception as e:
            logger.warning(f"Could not fetch weather: {e}")
    
    # Get user profile for personalization
    profile = memory_manager.get_profile(trusted_user_id)
    preferences = request.preferences or {}
    
    if profile:
        # Merge profile preferences
        if profile.prefers_low_prep and "low_prep" not in preferences:
            preferences["low_prep"] = True
        if profile.default_age_group and not request.age_group:
            request.age_group = profile.default_age_group
        # Merge typical supplies from profile
        if profile.typical_supplies and "available_supplies" not in preferences:
            preferences["available_supplies"] = profile.typical_supplies
    
    # Extract theme and supplies from preferences
    theme = preferences.get("theme") or preferences.get("activity_type")
    available_supplies = preferences.get("available_supplies") or preferences.get("supplies", [])
    
    # Generate schedule template with activity population
    schedule = generate_schedule_template(
        date=request.date,
        age_group=request.age_group,
        duration_hours=request.duration_hours,
        preferences=preferences,
        weather=weather_data,
        theme=theme,
        available_supplies=available_supplies
    )
    
    log_event(
        logger,
        logging.INFO,
        "schedule_generated",
        user_id=trusted_user_id,
        date=request.date,
        theme=theme,
        filled_count=schedule.get("stats", {}).get("filled_slots", 0)
    )
    
    return schedule


@app.post("/api/schedule/save")
async def save_schedule(request: ScheduleCreateRequest, http_request: Request):
    """Save a generated schedule."""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    trusted_user_id, _ = _get_or_create_session_user_id(http_request)
    
    # Rate limiting check
    allowed, retry_after = schedule_save_limiter.allow(trusted_user_id)
    if not allowed:
        metrics.incr("rate_limited_requests_total")
        log_event(
            logger,
            logging.WARNING,
            "schedule_save_rate_limited",
            user_id=trusted_user_id,
            retry_after=retry_after,
        )
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry in {retry_after}s")
    
    # Generate unique ID
    import uuid
    schedule_id = str(uuid.uuid4())
    
    # Sanitize schedule title
    sanitized_title = sanitize_schedule_title(request.title) if request.title else None
    
    # Sanitize activities data
    sanitized_activities = []
    for activity in request.activities:
        sanitized_activity = sanitize_activity_data(activity.model_dump())
        from .models import ScheduleActivity
        sanitized_activities.append(ScheduleActivity(**sanitized_activity))
    
    # Save to database via memory manager
    schedule = Schedule(
        id=schedule_id,
        user_id=trusted_user_id,
        date=request.date,
        title=sanitized_title,
        age_group=request.age_group,
        duration_hours=request.duration_hours,
        activities=sanitized_activities
    )
    
    # Save to SQLite
    with sqlite3.connect(memory_manager.db_path) as conn:
        conn.execute(
            """INSERT INTO schedules 
               (id, user_id, date, title, age_group, duration_hours, activities, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                schedule.id,
                schedule.user_id,
                schedule.date,
                schedule.title,
                schedule.age_group,
                schedule.duration_hours,
                json.dumps([a.model_dump() for a in schedule.activities]),
                schedule.created_at
            )
        )
        conn.commit()
    
    log_event(
        logger,
        logging.INFO,
        "schedule_saved",
        user_id=trusted_user_id,
        schedule_id=schedule_id
    )
    
    return {"id": schedule_id, "status": "saved"}


@app.get("/api/schedule/{schedule_id}")
async def get_schedule(schedule_id: str, http_request: Request):
    """Get a saved schedule by ID."""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    trusted_user_id, _ = _get_or_create_session_user_id(http_request)
    
    with sqlite3.connect(memory_manager.db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM schedules WHERE id = ? AND user_id = ?",
            (schedule_id, trusted_user_id)
        ).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        activities = json.loads(row["activities"])
        return {
            "id": row["id"],
            "date": row["date"],
            "title": row["title"],
            "age_group": row["age_group"],
            "duration_hours": row["duration_hours"],
            "activities": activities,
            "created_at": row["created_at"]
        }


@app.get("/api/schedules")
async def list_schedules(
    http_request: Request,
    limit: int = 10,
    offset: int = 0
):
    """List saved schedules for the current user."""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    trusted_user_id, _ = _get_or_create_session_user_id(http_request)
    
    with sqlite3.connect(memory_manager.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Get total count
        count_row = conn.execute(
            "SELECT COUNT(*) as count FROM schedules WHERE user_id = ?",
            (trusted_user_id,)
        ).fetchone()
        total = count_row["count"]
        
        # Get schedules
        rows = conn.execute(
            """SELECT id, date, title, age_group, duration_hours, created_at 
               FROM schedules 
               WHERE user_id = ? 
               ORDER BY created_at DESC 
               LIMIT ? OFFSET ?""",
            (trusted_user_id, limit, offset)
        ).fetchall()
        
        schedules = [
            {
                "id": row["id"],
                "date": row["date"],
                "title": row["title"],
                "age_group": row["age_group"],
                "duration_hours": row["duration_hours"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
        
        return {
            "schedules": schedules,
            "total": total,
            "limit": limit,
            "offset": offset
        }


@app.delete("/api/schedule/{schedule_id}")
async def delete_schedule(schedule_id: str, http_request: Request):
    """Delete a saved schedule."""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    trusted_user_id, _ = _get_or_create_session_user_id(http_request)
    
    # Rate limiting check
    allowed, retry_after = delete_schedule_limiter.allow(trusted_user_id)
    if not allowed:
        metrics.incr("rate_limited_requests_total")
        log_event(
            logger,
            logging.WARNING,
            "delete_schedule_rate_limited",
            user_id=trusted_user_id,
            retry_after=retry_after,
        )
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry in {retry_after}s")
    
    with sqlite3.connect(memory_manager.db_path) as conn:
        # Check if schedule exists and belongs to user
        row = conn.execute(
            "SELECT 1 FROM schedules WHERE id = ? AND user_id = ?",
            (schedule_id, trusted_user_id)
        ).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        # Delete the schedule
        conn.execute(
            "DELETE FROM schedules WHERE id = ? AND user_id = ?",
            (schedule_id, trusted_user_id)
        )
        conn.commit()
        
    return {"success": True, "message": "Schedule deleted"}


def generate_schedule_template(
    date: str,
    age_group: str,
    duration_hours: int,
    preferences: dict,
    weather: dict = None,
    theme: str = None,
    available_supplies: list = None,
) -> dict:
    """
    Generate a schedule template with time slots and ACTUALLY populate with activities.
    
    Args:
        date: Date string (YYYY-MM-DD)
        age_group: Target age group (e.g., "6-8 years")
        duration_hours: Total schedule duration
        preferences: User preferences dict
        weather: Weather data dict (optional)
        theme: Activity theme (optional, e.g., "science", "art", "sports")
        available_supplies: List of available supplies (optional)
    
    Returns:
        Schedule dict with populated activities
    """
    from datetime import datetime, timedelta
    import random
    
    # Parse preferences
    start_time_str = preferences.get("start_time", "9:00 AM")
    include_breaks = preferences.get("include_breaks", True)
    low_prep_only = preferences.get("low_prep", False)
    
    try:
        start = datetime.strptime(start_time_str, "%I:%M %p")
    except:
        start = datetime.strptime("9:00", "%H:%M")
    
    # Determine if outdoor is suitable
    outdoor_ok = True
    if weather:
        outdoor_ok = weather.get("outdoor_suitable", True)
    indoor_pref = preferences.get("indoor_preferred", not outdoor_ok)
    
    # Activity durations based on age group
    age_num = 8  # default
    try:
        # Extract first number from age_group string
        age_match = re.search(r'(\d+)', age_group)
        if age_match:
            age_num = int(age_match.group(1))
    except:
        pass
    
    if age_num <= 6:
        activity_duration = 20  # Younger kids = shorter activities
    elif age_num <= 8:
        activity_duration = 30
    else:
        activity_duration = 45
    
    # Build search queries based on theme and preferences
    base_queries = []
    if theme:
        base_queries.append(f"{theme} activities for kids")
        base_queries.append(f"{theme} games children")
    else:
        base_queries = [
            "fun kids activities",
            "children games",
            "educational activities",
            "group activities children",
        ]
    
    # Add age-specific terms
    for i in range(len(base_queries)):
        base_queries[i] = f"{base_queries[i]} {age_group}"
    
    # Search for activities using vector store
    found_activities = []
    if vector_store:
        try:
            # Search with multiple queries for variety
            for query in base_queries[:3]:  # Limit to 3 searches
                try:
                    results = vector_store.search(
                        query=query,
                        top_k=10,
                        filter_dict=None
                    )
                    for match in results:
                        activity = {
                            "id": match.get("id"),
                            "title": match.get("title", "Untitled"),
                            "description": match.get("description", ""),
                            "type": match.get("type", "Other"),
                            "duration_minutes": match.get("duration_minutes", activity_duration),
                            "indoor_outdoor": match.get("indoor_outdoor", "either"),
                            "supplies": match.get("supplies", ""),
                            "score": match.get("score", 0),
                        }
                        # Avoid duplicates
                        if not any(a.get("id") == activity["id"] for a in found_activities):
                            found_activities.append(activity)
                except Exception as e:
                    logger.warning(f"Activity search failed for query '{query}': {e}")
                    continue
        except Exception as e:
            logger.error(f"Vector store search failed: {e}")
    
    # Filter activities based on constraints
    suitable_activities = []
    for activity in found_activities:
        # Check duration compatibility (within +/- 15 min of target)
        act_duration = activity.get("duration_minutes", 30) or 30
        if abs(act_duration - activity_duration) > 20:
            continue
        
        # Check indoor/outdoor preference
        act_io = activity.get("indoor_outdoor", "either")
        if indoor_pref and act_io == "outdoor":
            continue  # Skip outdoor-only if indoor preferred
        if not outdoor_ok and act_io == "outdoor":
            continue  # Skip outdoor-only if weather doesn't permit
        
        # Check supply constraints
        if available_supplies and activity.get("supplies"):
            act_supplies = str(activity.get("supplies", "")).lower()
            # Skip if requires special supplies not available
            has_supplies = any(s.lower() in act_supplies for s in available_supplies)
            if not has_supplies and low_prep_only:
                continue
        
        suitable_activities.append(activity)
    
    # Shuffle for variety
    random.shuffle(suitable_activities)
    
    # Generate time slots and populate with activities
    slots = []
    activities_placed = []
    current_time = start
    end_time = start + timedelta(hours=duration_hours)
    activity_count = 0
    activity_index = 0
    
    while current_time < end_time:
        time_str = current_time.strftime("%I:%M %p")
        
        # Add break every 3 activities
        if include_breaks and activity_count > 0 and activity_count % 3 == 0:
            slots.append({
                "time": time_str,
                "type": "break",
                "duration_minutes": 15,
                "title": "Break/Snack",
                "description": "Transition and refreshment break"
            })
            current_time += timedelta(minutes=15)
            continue
        
        # Determine indoor/outdoor recommendation
        if outdoor_ok and activity_count % 2 == 0:
            location_rec = "outdoor"
        else:
            location_rec = "indoor"
        
        # Get next activity from suitable_activities (cycle if needed)
        if suitable_activities and activity_index < len(suitable_activities):
            activity = suitable_activities[activity_index]
            activity_index += 1
            
            slot = {
                "time": time_str,
                "type": "activity",
                "duration_minutes": activity.get("duration_minutes", activity_duration),
                "title": activity.get("title", "Activity"),
                "description": activity.get("description", "Fun activity")[:150] + "...",
                "indoor_outdoor": activity.get("indoor_outdoor", location_rec),
                "activity_id": activity.get("id"),
                "activity_type": activity.get("type", "Other"),
                "supplies_needed": activity.get("supplies", ""),
                "needs_activity": False  # ✅ ACTIVITY POPULATED
            }
            activities_placed.append(activity.get("title"))
        else:
            # Fallback if no activities found
            slot = {
                "time": time_str,
                "type": "activity",
                "duration_minutes": activity_duration,
                "title": f"{theme.title() if theme else 'Fun'} Activity {activity_count + 1}",
                "description": f"A {theme if theme else 'fun'} activity suitable for {age_group}.",
                "indoor_outdoor": location_rec,
                "needs_activity": True  # Still needs an activity
            }
        
        slots.append(slot)
        current_time += timedelta(minutes=slot.get("duration_minutes", activity_duration))
        activity_count += 1
    
    # Build response
    filled_count = len([s for s in slots if s.get("type") == "activity" and not s.get("needs_activity", True)])
    total_activity_slots = len([s for s in slots if s.get("type") == "activity"])
    
    return {
        "date": date,
        "age_group": age_group,
        "duration_hours": duration_hours,
        "theme": theme,
        "weather": weather,
        "outdoor_suitable": outdoor_ok,
        "preferences": preferences,
        "template": slots,
        "activities_populated": activities_placed,
        "stats": {
            "total_slots": len(slots),
            "activity_slots": total_activity_slots,
            "filled_slots": filled_count,
            "break_slots": len([s for s in slots if s.get("type") == "break"]),
            "activities_found": len(found_activities),
            "activities_suitable": len(suitable_activities)
        },
        "note": f"Schedule generated with {filled_count}/{total_activity_slots} activities populated from database." if filled_count > 0 else "Schedule template created. Limited activities found - use chat to customize."
    }


# Initialize schedules table on startup
@lifespan(app)
async def init_schedules_table():
    """Initialize schedules table in database."""
    if memory_manager:
        with sqlite3.connect(memory_manager.db_path) as conn:
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
            conn.commit()


# Phase 4: Save Activity endpoint
class SaveActivityRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)
    instructions: str = Field(..., min_length=1, max_length=4000)
    age_group: str = Field(..., min_length=1, max_length=50)
    duration_minutes: int = Field(..., ge=5, le=300)
    supplies: list[str] = Field(default_factory=list)
    activity_type: str = Field(default="Other")
    indoor_outdoor: str = Field(default="either")


@app.post("/api/activities/save")
async def save_activity_endpoint(
    request: SaveActivityRequest,
    http_request: Request
):
    """
    Save a user-generated activity to the database.
    Persists to both SQLite and Pinecone vector store.
    """
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    trusted_user_id, _ = _get_or_create_session_user_id(http_request)
    
    # Rate limiting check
    allowed, retry_after = activity_save_limiter.allow(trusted_user_id)
    if not allowed:
        metrics.incr("rate_limited_requests_total")
        log_event(
            logger,
            logging.WARNING,
            "activity_save_rate_limited",
            user_id=trusted_user_id,
            retry_after=retry_after,
        )
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry in {retry_after}s")
    
    # Import the save tool
    from .tools import save_activity_tool
    
    # Sanitize user inputs
    sanitized_title = sanitize_activity_title(request.title)
    sanitized_description = sanitize_activity_description(request.description)
    sanitized_instructions = sanitize_activity_description(request.instructions)
    sanitized_supplies = [
        sanitize_text_input(s, max_length=100) for s in (request.supplies or [])
    ]
    
    # Prepare context
    tool_context = {
        "user_id": trusted_user_id,
        "memory_manager": memory_manager,
        "vector_store": vector_store
    }
    
    # Call the save tool with sanitized data
    result = save_activity_tool(
        title=sanitized_title,
        description=sanitized_description,
        instructions=sanitized_instructions,
        age_group=request.age_group,
        duration_minutes=request.duration_minutes,
        supplies=sanitized_supplies,
        activity_type=request.activity_type,
        indoor_outdoor=request.indoor_outdoor,
        _context=tool_context
    )
    
    if result.get("success"):
        return {
            "success": True,
            "activity_id": result.get("activity_id"),
            "message": "Activity saved successfully!",
            "searchable": result.get("searchable", False)
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=result.get("note", "Failed to save activity")
        )


# Activity Browser Endpoints
class ActivitySearchRequest(BaseModel):
    query: str
    age_group: Optional[str] = None
    activity_type: Optional[str] = None
    indoor_outdoor: Optional[str] = None
    max_duration: Optional[int] = 120
    limit: int = 20


@app.post("/api/activities/search")
async def search_activities_endpoint(
    request: ActivitySearchRequest,
    http_request: Request
):
    """
    Search activities with semantic + filter support.
    Uses vector search for semantic matching, then applies filters.
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not initialized")
    
    try:
        # Build search query combining theme and filters
        search_query = request.query
        
        # Get semantic matches from Pinecone (just IDs)
        filter_dict = {"type": request.activity_type} if request.activity_type else None
        semantic_results = vector_store.search(
            query=search_query,
            top_k=request.limit * 3,  # Get more for filtering
            filter_dict=filter_dict
        )
        
        # Fetch full activity data from SQLite using IDs from Pinecone
        activities = []
        for match in semantic_results:
            activity_id = match.get("id")
            score = match.get("score")
            
            # Get full activity from SQLite
            activity = memory_manager.get_activity(activity_id) if memory_manager else None
            
            if not activity:
                # Fallback to Pinecone metadata if not in SQLite
                metadata = match.get("metadata", {})
                activity = {
                    "id": activity_id,
                    "title": metadata.get("title", "Untitled"),
                    "description": metadata.get("description", ""),
                    "activity_type": metadata.get("type", "Other"),
                    "development_age_group": metadata.get("development_age_group", "6-12 years"),
                    "supplies": metadata.get("supplies", ""),
                    "duration_minutes": metadata.get("duration_minutes", 30),
                    "indoor_outdoor": metadata.get("indoor_outdoor", "either"),
                }
            
            # Apply additional filters
            if request.age_group:
                activity_age = activity.get("development_age_group", "")
                if request.age_group not in activity_age:
                    continue
            
            if request.indoor_outdoor:
                activity_io = activity.get("indoor_outdoor", "either")
                if activity_io != request.indoor_outdoor and activity_io != "either":
                    continue
            
            if request.max_duration:
                duration = activity.get("duration_minutes") or 60
                if duration > request.max_duration:
                    continue
            
            activities.append({
                "id": activity.get("id"),
                "title": activity.get("title", "Untitled"),
                "description": activity.get("description", ""),
                "type": activity.get("activity_type", "Other"),
                "development_age_group": activity.get("development_age_group", "6-12 years"),
                "supplies": activity.get("supplies", ""),
                "instructions": activity.get("instructions", ""),
                "duration_minutes": activity.get("duration_minutes") or 30,
                "indoor_outdoor": activity.get("indoor_outdoor", "either"),
                "score": score,
            })
            
            if len(activities) >= request.limit:
                break
        
        return {
            "activities": activities,
            "total": len(activities),
            "query": request.query
        }
        
    except Exception as e:
        logger.error(f"Activity search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


# Phase 7: Voice Input (Whisper Integration)
import subprocess
import tempfile
import shutil
from fastapi import File, UploadFile

@app.post("/api/transcribe")
async def transcribe_audio(
    http_request: Request,
    audio: UploadFile = File(...)
):
    """
    Transcribe audio to text using Whisper.
    Accepts common audio formats (mp3, m4a, wav, webm).
    """
    # Check whisper is available
    if not shutil.which("whisper"):
        raise HTTPException(
            status_code=503,
            detail="Voice transcription not available. Whisper not installed."
        )
    
    # Validate file type
    allowed_types = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-m4a', 'audio/webm', 'audio/ogg']
    if audio.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {audio.content_type}. Supported: {', '.join(allowed_types)}"
        )
    
    # Save uploaded file to temp location
    suffix = audio.filename.split('.')[-1] if '.' in audio.filename else 'webm'
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{suffix}') as tmp_input:
        content = await audio.read()
        tmp_input.write(content)
        tmp_input_path = tmp_input.name
    
    try:
        # Run whisper transcription
        # Using base model for speed - can upgrade to medium for accuracy
        result = subprocess.run(
            ['whisper', tmp_input_path, '--model', 'base', '--output_format', 'txt', '--output_dir', '/tmp'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            logger.error(f"Whisper transcription failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail="Transcription failed. Please try again."
            )
        
        # Read transcribed text
        output_path = tmp_input_path.replace(f'.{suffix}', '.txt')
        with open(output_path, 'r') as f:
            transcribed_text = f.read().strip()
        
        # Clean up temp files
        os.unlink(tmp_input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)
        
        log_event("voice_transcription", level="INFO", 
                  request_id=request_id_ctx.get(),
                  chars=len(transcribed_text))
        
        return {
            "success": True,
            "text": transcribed_text,
            "source": "whisper"
        }
        
    except subprocess.TimeoutExpired:
        os.unlink(tmp_input_path)
        raise HTTPException(
            status_code=504,
            detail="Transcription timed out. Please try a shorter recording."
        )
    except Exception as e:
        # Clean up on error
        if os.path.exists(tmp_input_path):
            os.unlink(tmp_input_path)
        logger.error(f"Transcription error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Transcription failed. Please try again."
        )


# =============================================================================
# Phase 2: Weekly Schedule Persistence Endpoints
# =============================================================================

@app.post("/api/schedules/weekly/save")
async def save_weekly_schedule(
    request: Request,
    schedule_data: dict
):
    """
    Save a weekly schedule to the database.
    """
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    try:
        week_number = schedule_data.get("week_number")
        theme = schedule_data.get("theme", "")
        activities = schedule_data.get("activities", [])
        
        # Save to database using memory manager
        memory_manager.save_weekly_schedule(
            week_number=week_number,
            theme=theme,
            activities=activities
        )
        
        return {
            "success": True,
            "message": f"Week {week_number} saved successfully",
            "activities_count": len(activities)
        }
    except Exception as e:
        logger.error(f"Failed to save weekly schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save: {str(e)}")


@app.get("/api/schedules/weekly/{week_number}")
async def get_weekly_schedule(
    week_number: int,
    request: Request
):
    """
    Get a weekly schedule by week number.
    """
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    try:
        schedule = memory_manager.get_weekly_schedule(week_number)
        
        if not schedule:
            return {
                "success": True,
                "week_number": week_number,
                "theme": "",
                "activities": []
            }
        
        return {
            "success": True,
            "week_number": week_number,
            "theme": schedule.get("theme", ""),
            "activities": schedule.get("activities", [])
        }
    except Exception as e:
        logger.error(f"Failed to get weekly schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load: {str(e)}")


@app.post("/api/schedules/weekly/duplicate")
async def duplicate_weekly_schedule(
    request: Request,
    duplicate_data: dict
):
    """
    Duplicate a week to another week.
    """
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    try:
        from_week = duplicate_data.get("from_week")
        to_week = duplicate_data.get("to_week")
        
        # Get source schedule
        source = memory_manager.get_weekly_schedule(from_week)
        if not source:
            raise HTTPException(status_code=404, detail=f"Week {from_week} not found")
        
        # Save to target week
        memory_manager.save_weekly_schedule(
            week_number=to_week,
            theme=source.get("theme", ""),
            activities=source.get("activities", [])
        )
        
        return {
            "success": True,
            "message": f"Week {from_week} duplicated to Week {to_week}",
            "activities_copied": len(source.get("activities", []))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to duplicate: {str(e)}")
