"""
Agent 核心模块
"""
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from openai import OpenAI
import time
import sys
import json

from configurable import get_config, logger
from skill_loader import SKILLS
from todo_manager import TODO
from tools.base import TOOLS, ToolResult
from tools.builtin import register_builtin_tools
from errors import (
    AgentError, APIError, ToolExecutionError,
    handle_errors, ErrorContext
)


@dataclass
class AgentType:
    """代理类型定义"""
    name: str
    description: str
    tools: List[str] | str  # "*" 表示所有工具
    system_prompt: str


AGENT_TYPES: Dict[str, AgentType] = {
    "explore": AgentType(
        name="explore",
        description="Read-only agent for exploring code, finding files, searching",
        tools=["bash", "read_file"],
        system_prompt="You are an exploration agent. Search and analyze, but never modify files. Return a concise summary.",
    ),
    "code": AgentType(
        name="code",
        description="Full agent for implementing features and fixing bugs",
        tools="*",
        system_prompt="You are a coding agent. Implement the requested changes efficiently.",
    ),
    "plan": AgentType(
        name="plan",
        description="Planning agent for designing implementation strategies",
        tools=["bash", "read_file"],
        system_prompt="You are a planning agent. Analyze the codebase and output a numbered implementation plan. Do NOT make changes.",
    ),
    "review": AgentType(
        name="review",
        description="Code review agent for analyzing code quality and suggesting improvements",
        tools=["bash", "read_file"],
        system_prompt="You are a code review agent. Analyze the code for bugs, security issues, and improvements. Do NOT make changes.",
    ),
}


class TokenUsage:
    """Token 使用统计"""

    def __init__(self):
        self.total_input = 0
        self.total_output = 0
        self.call_count = 0

    def add(self, input_tokens: int, output_tokens: int):
        self.total_input += input_tokens
        self.total_output += output_tokens
        self.call_count += 1

    def summary(self) -> str:
        return f"Token usage: {self.total_input} input, {self.total_output} output, {self.call_count} calls"


# 全局 token 使用统计
TOKEN_USAGE = TokenUsage()


class AgentClient:
    """Agent 客户端"""

    def __init__(self, config=None):
        self.config = config or get_config()
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
        self._setup_tools()

    def _setup_tools(self):
        """设置工具"""
        register_builtin_tools(
            self.config,
            TODO,
            SKILLS,
            self.run_subagent,
            AGENT_TYPES
        )

    def get_tools_for_agent(self, agent_type: str) -> List[dict]:
        """根据代理类型过滤可用工具"""
        agent = AGENT_TYPES.get(agent_type)
        if not agent:
            return TOOLS.get_all_schemas()

        if agent.tools == "*":
            return TOOLS.get_all_schemas()

        return [
            t for t in TOOLS.get_all_schemas()
            if t["function"]["name"] in agent.tools
        ]

    def api_call_with_retry(self, messages: List[dict], tools: List[dict], stream: bool = False) -> Any:
        """带重试机制的 API 调用"""
        last_error = None

        for attempt in range(self.config.api_retry_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    tools=tools,
                    max_tokens=self.config.max_tokens,
                    stream=stream,
                )

                # 记录 token 使用量
                if not stream and hasattr(response, 'usage') and response.usage:
                    TOKEN_USAGE.add(response.usage.prompt_tokens, response.usage.completion_tokens)

                return response

            except Exception as e:
                last_error = e
                logger.warning(f"API call failed (attempt {attempt + 1}/{self.config.api_retry_attempts}): {e}")

                if attempt < self.config.api_retry_attempts - 1:
                    delay = self.config.api_retry_delay * (2 ** attempt)
                    time.sleep(delay)

        raise APIError(f"API call failed after {self.config.api_retry_attempts} attempts: {last_error}")

    def api_call_stream(self, messages: List[dict], tools: List[dict]):
        """流式 API 调用"""
        response = self.api_call_with_retry(messages, tools, stream=True)

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
            if chunk.choices[0].delta.tool_calls:
                yield ("tool_calls", chunk.choices[0].delta.tool_calls)

    def validate_history_messages(self, messages: List[dict]) -> List[dict]:
        """
        验证并修复历史消息格式
        确保 tool_calls 中的 arguments 是有效的 JSON 字符串
        """
        import json
        validated = []

        for msg in messages:
            # 复制消息以避免修改原始对象
            msg_copy = dict(msg)

            # 检查是否有 tool_calls
            if "tool_calls" in msg_copy and msg_copy["tool_calls"]:
                valid_tool_calls = []
                for tc in msg_copy["tool_calls"]:
                    # 确保 tool_call 是字典格式
                    if isinstance(tc, dict):
                        func = tc.get("function", {})
                        args = func.get("arguments", "")

                        # 验证 arguments 是有效的 JSON
                        if args:
                            try:
                                json.loads(args)
                            except json.JSONDecodeError:
                                # 如果不是有效 JSON，尝试修复
                                logger.warning(f"Invalid JSON in tool_call arguments, attempting fix")
                                # 如果 arguments 看起来像 Python 字典，尝试转换
                                if args.startswith("{") and args.endswith("}"):
                                    try:
                                        # 尝试用 ast.literal_eval 解析
                                        import ast
                                        parsed = ast.literal_eval(args)
                                        args = json.dumps(parsed)
                                        func["arguments"] = args
                                    except:
                                        logger.warning(f"Could not fix tool_call arguments")
                                        continue  # 跳过无效的 tool_call
                                else:
                                    continue  # 跳过无效的 tool_call

                        valid_tool_calls.append(tc)
                    else:
                        # tool_call 不是字典格式，尝试转换
                        if hasattr(tc, 'id') and hasattr(tc, 'function'):
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

    def trim_history(self, messages: List[dict]) -> List[dict]:
        """
        智能裁剪历史消息以控制上下文长度
        保留 system prompt 和最近的消息
        """
        if len(messages) <= self.config.max_history_messages:
            return messages

        system_msg = messages[0] if messages[0]["role"] == "system" else None
        recent_messages = messages[-(self.config.max_history_messages - 1):]

        if system_msg:
            return [system_msg] + recent_messages
        return recent_messages

    def compress_history(self, messages: List[dict]) -> List[dict]:
        """
        使用 LLM 压缩历史消息（可选实现）
        目前使用简单截断，后续可实现智能压缩
        """
        # 先验证历史消息格式
        messages = self.validate_history_messages(messages)
        return self.trim_history(messages)

    def execute_tool(self, name: str, args: dict) -> str:
        """执行工具"""
        logger.debug(f"Executing tool: {name} with args: {list(args.keys())}")

        with ErrorContext("tool_execution", tool=name, args=args):
            result = TOOLS.execute(name, args)

            if result.success:
                logger.debug(f"Tool {name} succeeded: {result.content[:100]}...")
                return result.content
            else:
                logger.warning(f"Tool {name} failed: {result.error}")
                return f"Error: {result.error}"

    def run_subagent(self, description: str, prompt: str, agent_type: str) -> str:
        """运行子代理任务"""
        if agent_type not in AGENT_TYPES:
            available = ", ".join(AGENT_TYPES.keys())
            return f"Error: Unknown agent type '{agent_type}'. Available: {available}"

        config = AGENT_TYPES[agent_type]
        sub_system = f"""You are a {agent_type} subagent at {self.config.workdir}.
{config.system_prompt}
Complete the task and return a clear, concise summary."""

        sub_tools = self.get_tools_for_agent(agent_type)
        sub_messages = [
            {"role": "system", "content": sub_system},
            {"role": "user", "content": prompt}
        ]

        print(f"  [{agent_type}] {description}")
        logger.info(f"Starting subagent: {agent_type} - {description}")
        start = time.time()
        tool_count = 0
        iteration = 0

        while iteration < self.config.max_subagent_iterations:
            iteration += 1

            try:
                response = self.api_call_with_retry(sub_messages, sub_tools)
            except APIError as e:
                logger.error(f"Subagent API error: {e}")
                return f"Subagent error: {e}"

            message = response.choices[0].message

            if not message.tool_calls:
                elapsed = time.time() - start
                sys.stdout.write(f"\r  [{agent_type}] {description} - done ({tool_count} tools, {elapsed:.1f}s)\n")
                sub_messages.append(message)
                logger.info(f"Subagent completed: {agent_type} - {tool_count} tools in {elapsed:.1f}s")
                return message.content or "(subagent returned no text)"

            sub_messages.append(message)

            for tool_call in message.tool_calls:
                tool_count += 1
                function_name = tool_call.function.name

                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                output = self.execute_tool(function_name, arguments)

                elapsed = time.time() - start
                sys.stdout.write(f"\r  [{agent_type}] {description} ... {tool_count} tools, {elapsed:.1f}s")
                sys.stdout.flush()

                sub_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": output
                })

        logger.warning(f"Subagent reached max iterations: {agent_type}")
        return f"Warning: Subagent reached maximum iterations ({self.config.max_subagent_iterations}). Partial result may be incomplete."

    def process_tool_calls(self, message, messages: List[dict]) -> None:
        """处理工具调用"""
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name

            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                args = {}

            # 打印 UI
            if func_name == "Task":
                print(f"\n> Task: {args.get('description', 'subtask')}")
            elif func_name == "Skill":
                print(f"\n> Loading skill: {args.get('skill', '?')}")
            else:
                if func_name == "bash":
                    cmd_preview = args.get("command", "")[:80]
                    print(f"\n> {func_name}: {cmd_preview}")
                else:
                    print(f"\n> {func_name}: {args.get('path', str(args)[:50])}")

            output = self.execute_tool(func_name, args)

            # 打印结果预览
            if func_name == "Skill":
                print(f"  Skill loaded ({len(output)} chars)")
            elif func_name != "Task":
                preview = output[:200] + "..." if len(output) > 200 else output
                print(f"  {preview}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": output
            })

    def agent_loop(self, messages: List[dict], use_stream: bool = False) -> List[dict]:
        """主代理循环"""
        while True:
            messages = self.compress_history(messages)

            try:
                if use_stream:
                    return self._agent_loop_stream(messages)
                else:
                    response = self.api_call_with_retry(messages, TOOLS.get_all_schemas())
            except APIError as e:
                logger.error(f"Agent loop API error: {e}")
                print(f"Error: API call failed - {e}")
                return messages

            message = response.choices[0].message

            if message.content:
                print(message.content)

            if not message.tool_calls:
                # 转换为字典格式，避免 JSON 序列化问题
                messages.append({
                    "role": "assistant",
                    "content": message.content
                })
                return messages

            # 转换为字典格式，包含 tool_calls
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [{
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in message.tool_calls]
            })
            self.process_tool_calls(message, messages)

        return messages

    def _agent_loop_stream(self, messages: List[dict]) -> List[dict]:
        """流式代理循环"""
        collected_content = ""
        tool_calls_data = {}

        for chunk in self.api_call_stream(messages, TOOLS.get_all_schemas()):
            if isinstance(chunk, tuple) and chunk[0] == "tool_calls":
                # 处理工具调用
                for tc in chunk[1]:
                    idx = tc.index
                    if idx not in tool_calls_data:
                        tool_calls_data[idx] = {"id": tc.id, "name": "", "arguments": ""}
                    if tc.function:
                        if tc.function.name:
                            tool_calls_data[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_data[idx]["arguments"] += tc.function.arguments
            else:
                # 处理文本内容
                print(chunk, end="", flush=True)
                collected_content += chunk

        print()  # 换行

        if tool_calls_data:
            # 构建工具调用消息
            from openai.types.chat import ChatCompletionMessageToolCall

            tool_calls = []
            for idx in sorted(tool_calls_data.keys()):
                data = tool_calls_data[idx]
                tool_calls.append(ChatCompletionMessageToolCall(
                    id=data["id"],
                    function={
                        "name": data["name"],
                        "arguments": data["arguments"]
                    },
                    type="function"
                ))

            # 使用字典格式消息（便于 JSON 序列化）
            message = {
                "role": "assistant",
                "content": collected_content,
                "tool_calls": [{
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in tool_calls]
            }
            messages.append(message)
            self.process_tool_calls(message, messages)

            # 继续循环
            return self.agent_loop(messages, use_stream=True)

        # 没有工具调用，结束
        messages.append({"role": "assistant", "content": collected_content})
        return messages


# 向后兼容的全局函数
def agent_loop(messages: List[dict]) -> List[dict]:
    """主代理循环（向后兼容）"""
    client = AgentClient()
    return client.agent_loop(messages)


def get_agent_descriptions() -> str:
    """获取代理描述"""
    return "\n".join(f"- {name}: {cfg.description}" for name, cfg in AGENT_TYPES.items())