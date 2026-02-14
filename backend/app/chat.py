"""
Chat endpoint with streaming responses and function calling.
"""

from pydantic import BaseModel
from typing import List, Dict, Optional, AsyncGenerator, Any
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
from app.safety import check_input_safety
from app.tools import get_available_tools, execute_tool, tools

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
1. Search the activity database for specific types of activities using search_activities
2. Search with detailed constraints using search_activities_with_constraints (age, supplies, indoor/outdoor, theme, prep level)
3. Check weather using check_weather to plan outdoor vs indoor activities
4. Generate complete daily schedules using generate_schedule (weather-aware, with timing)
5. Generate new activity ideas using generate_activity when needed
6. Get user preferences using get_user_preferences

When a user asks you to plan something:
1. First, check the weather if outdoor activities might be involved
2. Search for relevant activities using constraints from their request
3. If needed, generate a complete schedule with proper timing

TOOL CALLING INSTRUCTIONS:
- You can call multiple tools in parallel when they don't depend on each other
- After receiving tool results, analyze them and provide a helpful response
- When generating schedules, explain your choices and provide the complete timeline
- If weather suggests indoor activities, focus on those and mention why

When planning:
- Consider age-appropriateness and developmental stages
- Balance active/calm, indoor/outdoor, structured/free play
- Account for transitions and cleanup time (include 5-min buffers)
- Suggest supply lists and preparation steps
- Remember user preferences from their profile

Always be helpful, specific, and practical. Child care staff are busy - give them actionable plans they can use immediately."""

    if user_context:
        base_prompt += f"\n\nUser context:\n{json.dumps(user_context, indent=2)}"

    return base_prompt


async def chat_endpoint(
    request: ChatRequest,
    vector_store,
    memory_manager
) -> AsyncGenerator[str, None]:
    """Main chat endpoint with SSE response stream and function calling."""

    # Get user context from memory if available
    user_context = {}
    profile_context = ""
    if memory_manager:
        user_context = memory_manager.get_user_context(request.user_id)
        profile_context = memory_manager.get_user_context_for_prompt(request.user_id)

    # Build messages for LLM
    system_content = get_system_prompt(user_context)

    # Inject user profile context if available
    if profile_context:
        system_content += f"\n\n{profile_context}"

    messages = [{"role": "system", "content": system_content}]
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})

    # Last user message for retrieval and memory
    last_user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_user_message = msg.content
            break

    # Safety guardrail before retrieval/model call
    is_safe, safety_msg = check_input_safety(last_user_message or "")
    if not is_safe:
        metrics.incr("safety_blocked_requests_total")
        log_event(logger, logging.WARNING, "safety_blocked_input", reason=safety_msg)
        yield f"data: {json.dumps({'type': 'error', 'data': {'message': safety_msg, 'error_type': 'safety'}})}\n\n"
        conv_id = request.conversation_id or request.session_id
        yield f"data: {json.dumps({'type': 'done', 'data': {'conversation_id': conv_id}})}\n\n"
        return

    # Prepare tool context
    tool_context = {
        "user_id": request.user_id,
        "memory_manager": memory_manager,
        "vector_store": vector_store
    }

    # Stream model response with function calling
    ai_provider = os.getenv("AI_PROVIDER", "openai").lower()
    log_event(logger, logging.INFO, "llm_stream_start", provider=ai_provider)

    available_tools = get_available_tools()

    if ai_provider == "anthropic" and ANTHROPIC_AVAILABLE:
        metrics.incr("llm_requests_total")
        metrics.incr("llm_requests_anthropic_total")
        async for chunk in stream_anthropic_with_tools(messages, available_tools, tool_context):
            yield chunk
    elif OPENAI_AVAILABLE:
        metrics.incr("llm_requests_total")
        metrics.incr("llm_requests_openai_total")
        async for chunk in stream_openai_with_tools(messages, available_tools, tool_context):
            yield chunk
    else:
        metrics.incr("llm_not_configured_total")
        yield f"data: {json.dumps({'type': 'content', 'data': {'content': 'AI service not configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY.'}})}\n\n"

    # Save memory
    if memory_manager and last_user_message:
        response_summary = "Chat response with tool calls"

        memory_manager.add_interaction(
            user_id=request.user_id,
            query=last_user_message,
            response_summary=response_summary,
            session_id=request.session_id,
        )

    # End stream with conversation id
    conv_id = request.conversation_id or request.session_id
    metrics.incr("chat_stream_completions_total")
    log_event(logger, logging.INFO, "chat_stream_complete", conversation_id=conv_id)
    yield f"data: {json.dumps({'type': 'done', 'data': {'conversation_id': conv_id}})}\n\n"


async def stream_openai_with_tools(
    messages: List[Dict], 
    tools: List[Dict],
    tool_context: Dict,
    max_iterations: int = 10
) -> AsyncGenerator[str, None]:
    """
    Stream response from OpenAI with function calling support.

    This handles the full conversation loop including tool execution.
    """
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    )

    iteration = 0
    current_messages = messages.copy()

    while iteration < max_iterations:
        iteration += 1

        try:
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=current_messages,
                tools=tools,
                tool_choice="auto",
                stream=True,
                temperature=0.7,
            )

            content_buffer = ""
            tool_calls_buffer = []
            current_tool_call = None

            for chunk in response:
                delta = chunk.choices[0].delta

                # Handle content
                if delta.content:
                    content_buffer += delta.content
                    data = {"type": "content", "data": {"content": delta.content}}
                    yield f"data: {json.dumps(data)}\n\n"
                    await asyncio.sleep(0.01)

                # Handle tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.id:
                            # New tool call
                            if current_tool_call and current_tool_call.get("id") != tc.id:
                                tool_calls_buffer.append(current_tool_call)
                            current_tool_call = {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name or "",
                                    "arguments": tc.function.arguments or ""
                                }
                            }
                        elif current_tool_call and tc.function:
                            # Append to existing
                            if tc.function.name:
                                current_tool_call["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                current_tool_call["function"]["arguments"] += tc.function.arguments

            # Don't forget the last tool call
            if current_tool_call:
                tool_calls_buffer.append(current_tool_call)

            # If no tool calls, we're done
            if not tool_calls_buffer:
                return

            # Execute tool calls and add to messages
            assistant_message = {
                "role": "assistant",
                "content": content_buffer or None,
                "tool_calls": tool_calls_buffer
            }
            current_messages.append(assistant_message)

            # Execute each tool call
            for tool_call in tool_calls_buffer:
                tool_name = tool_call["function"]["name"]
                try:
                    tool_args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}

                # Emit tool call event
                tool_call_event = {
                    "type": "tool_call",
                    "data": {
                        "name": tool_name,
                        "arguments": tool_args
                    }
                }
                yield f"data: {json.dumps(tool_call_event)}\n\n"

                # Execute the tool
                logger.info(f"Executing tool: {tool_name}")
                result = execute_tool(tool_name, tool_args, tool_context)

                # Add tool response to messages
                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result.result) if result.success else json.dumps({"error": result.error_message})
                }
                current_messages.append(tool_response)

        except Exception as e:
            error_type = classify_error(e)
            metrics.incr("openai_errors_total")
            metrics.incr(f"error_type_{error_type}_total")
            log_event(logger, logging.ERROR, "openai_stream_failed", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e), 'error_type': error_type}})}\n\n"
            return

    # If we hit max iterations, let the user know
    yield f"data: {json.dumps({'type': 'content', 'data': {'content': '\n\n[Note: Reached maximum tool iterations. Response may be incomplete.]\n\n'}})}\n\n"


async def stream_anthropic_with_tools(
    messages: List[Dict],
    tools: List[Dict],
    tool_context: Dict,
    max_iterations: int = 10
) -> AsyncGenerator[str, None]:
    """
    Stream response from Anthropic Claude with tool use support.
    """
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Convert OpenAI tool format to Anthropic format
    anthropic_tools = []
    for tool in tools:
        if tool.get("type") == "function":
            func = tool.get("function", {})
            anthropic_tools.append({
                "name": func.get("name"),
                "description": func.get("description"),
                "input_schema": func.get("parameters", {})
            })

    # Separate system message
    system_msg = ""
    claude_messages = []

    for msg in messages:
        if msg["role"] == "system":
            system_msg = msg["content"]
        else:
            claude_messages.append(msg)

    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        try:
            with client.messages.stream(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
                max_tokens=4096,
                temperature=0.7,
                system=system_msg,
                messages=claude_messages,
                tools=anthropic_tools if anthropic_tools else None,
            ) as stream:

                content_buffer = ""
                tool_use_blocks = []
                current_block = None

                for event in stream:
                    # Handle text content
                    if hasattr(event, 'delta') and hasattr(event.delta, 'text'):
                        text = event.delta.text
                        if text:
                            content_buffer += text
                            data = {"type": "content", "data": {"content": text}}
                            yield f"data: {json.dumps(data)}\n\n"
                            await asyncio.sleep(0.01)

                    # Handle tool use
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            current_block = {
                                "type": "tool_use",
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input": ""
                            }

                    elif event.type == "content_block_delta":
                        if event.delta.type == "input_json_delta":
                            if current_block:
                                current_block["input"] += event.delta.partial_json

                    elif event.type == "content_block_stop":
                        if current_block:
                            tool_use_blocks.append(current_block)
                            current_block = None

            # If no tool use, we're done
            if not tool_use_blocks:
                return

            # Add assistant message with tool uses
            assistant_content = []
            if content_buffer:
                assistant_content.append({"type": "text", "text": content_buffer})

            for tool_use in tool_use_blocks:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tool_use["id"],
                    "name": tool_use["name"],
                    "input": json.loads(tool_use["input"]) if tool_use["input"] else {}
                })

            claude_messages.append({
                "role": "assistant",
                "content": assistant_content
            })

            # Execute each tool
            tool_results = []
            for tool_use in tool_use_blocks:
                tool_name = tool_use["name"]
                tool_args = tool_use.get("input", {})

                # Emit tool call event
                tool_call_event = {
                    "type": "tool_call",
                    "data": {
                        "name": tool_name,
                        "arguments": tool_args
                    }
                }
                yield f"data: {json.dumps(tool_call_event)}\n\n"

                # Execute the tool
                logger.info(f"Executing tool: {tool_name}")
                result = execute_tool(tool_name, tool_args, tool_context)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use["id"],
                    "content": json.dumps(result.result) if result.success else json.dumps({"error": result.error_message})
                })

            # Add tool results to messages
            claude_messages.append({
                "role": "user",
                "content": tool_results
            })

        except Exception as e:
            error_type = classify_error(e)
            metrics.incr("anthropic_errors_total")
            metrics.incr(f"error_type_{error_type}_total")
            log_event(logger, logging.ERROR, "anthropic_stream_failed", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e), 'error_type': error_type}})}\n\n"
            return

    # If we hit max iterations
    yield f"data: {json.dumps({'type': 'content', 'data': {'content': '\n\n[Note: Reached maximum tool iterations. Response may be incomplete.]\n\n'}})}\n\n"


# Legacy streaming functions for backwards compatibility
async def stream_openai(messages: List[Dict]) -> AsyncGenerator[str, None]:
    """Stream response from OpenAI (legacy, no tools)."""
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
    """Stream response from Anthropic Claude (legacy, no tools)."""
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
