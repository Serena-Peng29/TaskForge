"""
聊天核心 API 路由 (SSE 流式响应)
"""
import json
import re
from typing import AsyncGenerator, List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse

from configurable import get_config, logger
from memory import get_memory
from tools.base import TOOLS
from agents import TOKEN_USAGE
from api.schemas import ChatRequest
from api.deps import (
    get_current_user_optional, get_state_for_user, get_current_state,
    set_current_state, get_system_prompt
)

CONFIG = get_config()
MEMORY = get_memory()
router = APIRouter(tags=["chat"])


def _get_user_id(user: Optional[Dict[str, Any]]) -> str:
    return user["user_id"] if user else "default"


def get_filtered_tools() -> List[dict]:
    current_state = get_current_state()
    all_tools = TOOLS.get_all_schemas()
    if current_state.mcp_manager and current_state.mcp_manager.is_available():
        all_tools.extend(current_state.mcp_manager.get_tool_schemas())
    if not current_state.enabled_tools:
        return all_tools
    return [t for t in all_tools if t["function"]["name"] in current_state.enabled_tools]


def validate_history_messages(messages: List[dict]) -> List[dict]:
    validated = []
    for msg in messages:
        msg_copy = dict(msg)
        if "tool_calls" in msg_copy and msg_copy["tool_calls"]:
            valid_tool_calls = []
            for tc in msg_copy["tool_calls"]:
                if isinstance(tc, dict):
                    args = tc.get("function", {}).get("arguments", "")
                    if args:
                        try:
                            json.loads(args)
                        except json.JSONDecodeError:
                            logger.warning("Skipping message with invalid tool_call arguments")
                            continue
                    valid_tool_calls.append(tc)
                elif hasattr(tc, 'id') and hasattr(tc, 'function'):
                    valid_tool_calls.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": getattr(tc.function, 'name', ''),
                            "arguments": getattr(tc.function, 'arguments', '{}')
                        }
                    })
            msg_copy["tool_calls"] = valid_tool_calls
        validated.append(msg_copy)
    return validated


def get_memory_context(message: str, user_id: str = "default") -> str:
    if not MEMORY.is_long_term_memory_available():
        return ""
    try:
        memories = MEMORY.search_memories(message, user_id, limit=5)
        if not memories:
            return ""
        memory_text = "\n".join([f"- {m.get('memory', str(m))}" for m in memories])
        return f"\n\n[User Memories (remember these across all sessions)]:\n{memory_text}\n"
    except Exception as e:
        logger.error(f"Failed to get memory context: {e}")
        return ""


def auto_save_memories():
    if not CONFIG.memory_config.enable_auto_extract or not MEMORY.is_long_term_memory_available():
        return
    try:
        current_state = get_current_state()
        user_message = ""
        assistant_message = ""
        for msg in reversed(current_state.history):
            if msg.get("role") == "user" and not user_message:
                user_message = msg.get("content", "")
            elif msg.get("role") == "assistant" and not assistant_message:
                assistant_message = msg.get("content", "") or ""
            if user_message and assistant_message:
                break
        if not user_message:
            return
        user_id = getattr(current_state, 'user_id', 'default') or 'default'
        result = MEMORY.add_memory(f"用户: {user_message}\n助手: {assistant_message}", user_id=user_id)
        if result and result.get("results"):
            logger.info(f"Auto-extracted memories: {len(result.get('results', []))} items")
    except Exception as e:
        logger.error(f"Failed to auto-save memories: {e}")


def auto_save_session():
    current_state = get_current_state()
    if not current_state.current_session_id:
        return
    user_id = getattr(current_state, 'user_id', 'default') or 'default'
    try:
        MEMORY.save_session_by_id(current_state.current_session_id, current_state.history, user_id)
    except Exception as e:
        logger.error(f"Failed to auto-save session: {e}")


async def stream_chat_response(message: str) -> AsyncGenerator[dict, None]:
    from openai.types.chat import ChatCompletionMessageToolCall

    current_state = get_current_state()
    user_id = getattr(current_state, 'user_id', 'default') or 'default'
    memory_context = get_memory_context(message, user_id)

    if memory_context:
        current_state.history.append({"role": "system", "content": memory_context.strip()})

    current_state.history.append({"role": "user", "content": message})
    logger.info(f"User input: {message[:100]}...")
    yield {"event": "start", "data": json.dumps({"message": message})}

    try:
        tools = get_filtered_tools()
        validated_history = validate_history_messages(current_state.history)
        response = current_state.agent_client.api_call_with_retry(validated_history, tools, stream=True)

        collected_content = ""
        tool_calls_data = {}

        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                collected_content += delta.content
                yield {"event": "content", "data": json.dumps({"content": delta.content})}

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_data:
                        tool_calls_data[idx] = {"id": tc.id, "name": "", "arguments": ""}
                        yield {"event": "tool_start", "data": json.dumps({"index": idx, "id": tc.id})}
                    if tc.function:
                        if tc.function.name:
                            tool_calls_data[idx]["name"] = tc.function.name
                            yield {"event": "tool_name", "data": json.dumps({"index": idx, "name": tc.function.name})}
                        if tc.function.arguments:
                            tool_calls_data[idx]["arguments"] += tc.function.arguments
                            yield {"event": "tool_args", "data": json.dumps({"index": idx, "args": tc.function.arguments})}

        if collected_content:
            yield {"event": "content_done", "data": json.dumps({"content": collected_content})}

        if tool_calls_data:
            tool_calls = [
                ChatCompletionMessageToolCall(id=d["id"], function={"name": d["name"], "arguments": d["arguments"]}, type="function")
                for d in [tool_calls_data[i] for i in sorted(tool_calls_data.keys())]
            ]
            assistant_message = {
                "role": "assistant",
                "content": collected_content,
                "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in tool_calls]
            }
            current_state.history.append(assistant_message)

            for tool_call in tool_calls:
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                func_name = tool_call.function.name
                yield {"event": "tool_execute", "data": json.dumps({"name": func_name, "args": args})}
                result = current_state.agent_client.execute_tool(func_name, args)
                preview = result[:500] + "..." if len(result) > 500 else result
                yield {"event": "tool_result", "data": json.dumps({"name": func_name, "result": preview})}
                current_state.history.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

            async for event in stream_agent_loop():
                yield event
        else:
            current_state.history.append({"role": "assistant", "content": collected_content})
            auto_save_memories()
            auto_save_session()
            yield {"event": "done", "data": json.dumps({"content": collected_content})}

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        yield {"event": "error", "data": json.dumps({"error": str(e)})}


async def stream_agent_loop() -> AsyncGenerator[dict, None]:
    from openai.types.chat import ChatCompletionMessageToolCall

    current_state = get_current_state()
    tools = get_filtered_tools()
    validated_history = validate_history_messages(current_state.history)
    response = current_state.agent_client.api_call_with_retry(validated_history, tools, stream=True)

    collected_content = ""
    tool_calls_data = {}

    for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            collected_content += delta.content
            yield {"event": "content", "data": json.dumps({"content": delta.content})}
        if delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_calls_data:
                    tool_calls_data[idx] = {"id": tc.id, "name": "", "arguments": ""}
                    yield {"event": "tool_start", "data": json.dumps({"index": idx, "id": tc.id})}
                if tc.function:
                    if tc.function.name:
                        tool_calls_data[idx]["name"] = tc.function.name
                        yield {"event": "tool_name", "data": json.dumps({"index": idx, "name": tc.function.name})}
                    if tc.function.arguments:
                        tool_calls_data[idx]["arguments"] += tc.function.arguments
                        yield {"event": "tool_args", "data": json.dumps({"index": idx, "args": tc.function.arguments})}

    if collected_content:
        yield {"event": "content_done", "data": json.dumps({"content": collected_content})}

    if tool_calls_data:
        valid_tool_calls = []
        for idx in sorted(tool_calls_data.keys()):
            data = tool_calls_data[idx]
            if not data['arguments']:
                continue
            try:
                json.loads(data['arguments'])
                valid_tool_calls.append(ChatCompletionMessageToolCall(
                    id=data["id"], function={"name": data["name"], "arguments": data["arguments"]}, type="function"
                ))
            except json.JSONDecodeError:
                continue

        if not valid_tool_calls:
            current_state.history.append({"role": "assistant", "content": collected_content})
            yield {"event": "done", "data": json.dumps({"content": collected_content})}
            return

        assistant_message = {
            "role": "assistant",
            "content": collected_content,
            "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in valid_tool_calls]
        }
        current_state.history.append(assistant_message)

        for tool_call in valid_tool_calls:
            args = json.loads(tool_call.function.arguments)
            func_name = tool_call.function.name
            yield {"event": "tool_execute", "data": json.dumps({"name": func_name, "args": args})}
            result = current_state.agent_client.execute_tool(func_name, args)
            preview = result[:500] + "..." if len(result) > 500 else result
            yield {"event": "tool_result", "data": json.dumps({"name": func_name, "result": preview})}
            current_state.history.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

        async for event in stream_agent_loop():
            yield event
    else:
        current_state.history.append({"role": "assistant", "content": collected_content})
        auto_save_memories()
        auto_save_session()
        yield {"event": "done", "data": json.dumps({"content": collected_content})}


@router.post("/api/chat")
async def chat(request: ChatRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    user_state = get_state_for_user(current_user)
    set_current_state(user_state)
    if request.stream:
        return EventSourceResponse(stream_chat_response(request.message))
    full_content = ""
    async for event in stream_chat_response(request.message):
        if event.get("event") == "content":
            full_content += json.loads(event["data"])["content"]
        elif event.get("event") in ("done", "error"):
            break
    return {"content": full_content}


@router.post("/api/load")
async def load_session(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    user_id = _get_user_id(current_user)
    current_state = get_state_for_user(current_user)
    sessions = MEMORY.list_sessions(user_id)
    if sessions:
        session = sessions[0]
        session_data = MEMORY.get_session(session.id, user_id)
        if session_data:
            current_state.current_session_id = session.id
            set_current_state(current_state)
            current_state.history = [{"role": "system", "content": get_system_prompt()}] + session_data.get("messages", [])
            return {"status": "loaded", "session_id": session.id, "message_count": len(session_data.get("messages", []))}
    return {"status": "no_session"}


@router.post("/api/save")
async def save_session(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    user_id = _get_user_id(current_user)
    current_state = get_state_for_user(current_user)
    if current_state.current_session_id and MEMORY.save_session_by_id(current_state.current_session_id, current_state.history, user_id):
        return {"status": "saved", "session_id": current_state.current_session_id}
    return {"status": "error", "message": "Failed to save session"}
