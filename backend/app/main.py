"""
KidsClubPlans Conversational Backend
FastAPI app with streaming chat via Server-Sent Events
"""

import json
import logging
import os
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
from .safety import chat_rate_limiter, normalize_text

load_dotenv()
configure_logging()
logger = logging.getLogger("kcp.api")


# Global instances (single architecture)
vector_store = None
memory_manager: Optional[MemoryManager] = None


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
            secure=False,
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
    
    # Generate schedule template
    schedule = generate_schedule_template(
        date=request.date,
        age_group=request.age_group,
        duration_hours=request.duration_hours,
        preferences=preferences,
        weather=weather_data
    )
    
    log_event(
        logger,
        logging.INFO,
        "schedule_generated",
        user_id=trusted_user_id,
        date=request.date,
        activity_count=len(schedule.get("activities", []))
    )
    
    return schedule


@app.post("/api/schedule/save")
async def save_schedule(request: ScheduleCreateRequest, http_request: Request):
    """Save a generated schedule."""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    trusted_user_id, _ = _get_or_create_session_user_id(http_request)
    
    # Generate unique ID
    import uuid
    schedule_id = str(uuid.uuid4())
    
    # Save to database via memory manager
    schedule = Schedule(
        id=schedule_id,
        user_id=trusted_user_id,
        date=request.date,
        title=request.title,
        age_group=request.age_group,
        duration_hours=request.duration_hours,
        activities=request.activities
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


def generate_schedule_template(
    date: str,
    age_group: str,
    duration_hours: int,
    preferences: dict,
    weather: dict = None
) -> dict:
    """Generate a schedule template with time slots."""
    from datetime import datetime, timedelta
    
    # Parse preferences
    start_time_str = preferences.get("start_time", "9:00 AM")
    include_breaks = preferences.get("include_breaks", True)
    
    try:
        start = datetime.strptime(start_time_str, "%I:%M %p")
    except:
        start = datetime.strptime("9:00", "%H:%M")
    
    # Generate time slots
    slots = []
    current_time = start
    end_time = start + timedelta(hours=duration_hours)
    
    # Determine if outdoor is suitable
    outdoor_ok = True
    if weather:
        outdoor_ok = weather.get("outdoor_suitable", True)
    
    # Activity durations based on age group
    if "5" in age_group or "6" in age_group:
        activity_duration = 20  # Younger kids = shorter activities
    elif "7" in age_group or "8" in age_group:
        activity_duration = 30
    else:
        activity_duration = 45
    
    activity_count = 0
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
        
        slots.append({
            "time": time_str,
            "type": "activity",
            "duration_minutes": activity_duration,
            "title": None,  # To be filled
            "description": None,
            "indoor_outdoor": location_rec,
            "needs_activity": True
        })
        
        current_time += timedelta(minutes=activity_duration)
        activity_count += 1
    
    return {
        "date": date,
        "age_group": age_group,
        "duration_hours": duration_hours,
        "weather": weather,
        "outdoor_suitable": outdoor_ok,
        "preferences": preferences,
        "template": slots,
        "note": "Schedule template created. Use the chat to fill activities for each slot."
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
    
    # Import the save tool
    from .tools import save_activity_tool
    
    # Prepare context
    tool_context = {
        "user_id": trusted_user_id,
        "memory_manager": memory_manager,
        "vector_store": vector_store
    }
    
    # Call the save tool
    result = save_activity_tool(
        title=request.title,
        description=request.description,
        instructions=request.instructions,
        age_group=request.age_group,
        duration_minutes=request.duration_minutes,
        supplies=request.supplies,
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
