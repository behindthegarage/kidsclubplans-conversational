"""
KidsClubPlans Conversational Backend
FastAPI app with streaming chat via Server-Sent Events
"""

import json
import logging
import os
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
from .observability import (
    classify_error,
    configure_logging,
    log_event,
    metrics,
    request_id_ctx,
)
from .rag import initialize_vector_store

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
