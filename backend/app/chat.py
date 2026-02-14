"""
Chat endpoint with streaming responses and function calling.
"""

from pydantic import BaseModel
from typing import List, Dict, Optional, AsyncGenerator
import json
import logging
import os
from datetime import datetime
import asyncio

# Try to import OpenAI/Anthropic, but don't fail if not available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from app.observability import classify_error, log_event, metrics
from app.rag import search_activities

LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
logger = logging.getLogger("kcp.chat")


class Message(BaseModel):
    """A single message in the conversation."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    messages: List[Message]
    user_id: Optional[str] = "anonymous"
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    stream: bool = True


def get_system_prompt(user_context: Dict = None) -> str:
    """Build the system prompt with domain knowledge about child care."""
    base_prompt = """You are an expert activity planning assistant for child care programs.
You help directors and staff plan engaging, age-appropriate activities.

Your capabilities:
1. Search the activity database for specific types of activities
2. Generate new activity ideas based on constraints (supplies, time, age, theme)
3. Plan full days or weeks of activities with proper pacing
4. Consider weather, supplies, developmental appropriateness
5. Suggest alternatives and adaptations

When planning:
- Consider age-appropriateness and developmental stages
- Balance active/calm, indoor/outdoor, structured/free play
- Account for transitions and cleanup time
- Suggest supply lists and preparation steps
- Remember user preferences from past interactions

Always be helpful, specific, and practical. Child care staff are busy — give them actionable plans they can use immediately."""

    if user_context:
        base_prompt += f"\n\nUser context:\n{json.dumps(user_context, indent=2)}"

    return base_prompt


async def chat_endpoint(
    request: ChatRequest,
    vector_store,
    memory_manager
) -> AsyncGenerator[str, None]:
    """Main chat endpoint with SSE response stream."""

    # Get user context from memory if available
    user_context = {}
    if memory_manager:
        user_context = memory_manager.get_user_context(request.user_id)

    # Build messages for LLM
    messages = [{"role": "system", "content": get_system_prompt(user_context)}]
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})

    # Last user message for retrieval and memory
    last_user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_user_message = msg.content
            break

    # RAG retrieval + emit activity events
    activity_context = []
    if vector_store and last_user_message:
        try:
            activities = search_activities(vector_store, last_user_message, limit=3)
            if activities:
                activity_context = activities
                context_str = "\n\nRelevant activities from database:\n"
                for act in activities:
                    context_str += f"- {act.get('title', 'Unknown')}: {act.get('description', '')[:100]}...\n"
                messages[0]["content"] += context_str

                for activity in activities:
                    yield f"data: {json.dumps({'type': 'activity', 'data': activity})}\n\n"
                    await asyncio.sleep(0.01)
        except Exception as e:
            error_type = classify_error(e)
            metrics.incr("rag_errors_total")
            metrics.incr(f"error_type_{error_type}_total")
            log_event(logger, logging.WARNING, "rag_lookup_failed", error_type=error_type, error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'RAG error: {str(e)}', 'error_type': error_type}})}\n\n"

    # Stream model response
    ai_provider = os.getenv("AI_PROVIDER", "openai").lower()
    log_event(logger, logging.INFO, "llm_stream_start", provider=ai_provider)

    if ai_provider == "anthropic" and ANTHROPIC_AVAILABLE:
        metrics.incr("llm_requests_total")
        metrics.incr("llm_requests_anthropic_total")
        async for chunk in stream_anthropic(messages):
            yield chunk
    elif OPENAI_AVAILABLE:
        metrics.incr("llm_requests_total")
        metrics.incr("llm_requests_openai_total")
        async for chunk in stream_openai(messages):
            yield chunk
    else:
        metrics.incr("llm_not_configured_total")
        yield f"data: {json.dumps({'type': 'content', 'data': {'content': 'AI service not configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY.'}})}\n\n"

    # Save memory
    if memory_manager and last_user_message:
        memory_manager.add_interaction(
            user_id=request.user_id,
            query=last_user_message,
            context=activity_context,
            session_id=request.session_id,
        )

    # End stream with conversation id
    conv_id = request.conversation_id or request.session_id
    metrics.incr("chat_stream_completions_total")
    log_event(logger, logging.INFO, "chat_stream_complete", conversation_id=conv_id)
    yield f"data: {json.dumps({'type': 'done', 'data': {'conversation_id': conv_id}})}\n\n"


async def stream_openai(messages: List[Dict]) -> AsyncGenerator[str, None]:
    """Stream response from OpenAI with timeout/retry hardening."""
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    )

    last_error = None
    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=messages,
                stream=True,
                temperature=0.7,
            )

            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    data = {"type": "content", "data": {"content": content}}
                    yield f"data: {json.dumps(data)}\n\n"
                    await asyncio.sleep(0.01)
            return

        except Exception as e:
            last_error = e
            error_type = classify_error(e)
            metrics.incr("openai_errors_total")
            metrics.incr(f"error_type_{error_type}_total")
            log_event(
                logger,
                logging.WARNING,
                "openai_attempt_failed",
                attempt=attempt,
                max_retries=LLM_MAX_RETRIES,
                error_type=error_type,
                error=str(e),
            )
            if attempt < LLM_MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)
                continue
            break

    yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'OpenAI failed after retries: {str(last_error)}', 'error_type': classify_error(last_error) if last_error else 'internal'}})}\n\n"


async def stream_anthropic(messages: List[Dict]) -> AsyncGenerator[str, None]:
    """Stream response from Anthropic Claude with retry hardening."""
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Convert messages to Claude format
    system_msg = ""
    claude_messages = []

    for msg in messages:
        if msg["role"] == "system":
            system_msg = msg["content"]
        else:
            claude_messages.append({"role": msg["role"], "content": msg["content"]})

    last_error = None
    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            with client.messages.stream(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
                max_tokens=4096,
                temperature=0.7,
                system=system_msg,
                messages=claude_messages,
            ) as stream:
                for text in stream.text_stream:
                    data = {"type": "content", "data": {"content": text}}
                    yield f"data: {json.dumps(data)}\n\n"
                    await asyncio.sleep(0.01)
            return

        except Exception as e:
            last_error = e
            error_type = classify_error(e)
            metrics.incr("anthropic_errors_total")
            metrics.incr(f"error_type_{error_type}_total")
            log_event(
                logger,
                logging.WARNING,
                "anthropic_attempt_failed",
                attempt=attempt,
                max_retries=LLM_MAX_RETRIES,
                error_type=error_type,
                error=str(e),
            )
            if attempt < LLM_MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)
                continue
            break

    yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'Anthropic failed after retries: {str(last_error)}', 'error_type': classify_error(last_error) if last_error else 'internal'}})}\n\n"
