"""
上下文压缩模块
"""
from typing import List, Optional, Tuple
from dataclasses import dataclass
import json

from configurable import get_config, logger


@dataclass
class MessageSummary:
    """消息摘要"""
    role: str
    summary: str
    tool_calls_count: int = 0
    original_length: int = 0


class ContextCompressor:
    """上下文压缩器"""

    def __init__(self, config=None):
        self.config = config or get_config()
        self._llm_client = None

    def _get_llm_client(self):
        """延迟初始化 LLM 客户端"""
        if self._llm_client is None:
            from openai import OpenAI
            self._llm_client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url
            )
        return self._llm_client

    def compress_messages(
        self,
        messages: List[dict],
        target_length: Optional[int] = None
    ) -> Tuple[List[dict], int]:
        """
        压缩消息列表

        Returns:
            (compressed_messages, tokens_saved)
        """
        if not messages:
            return messages, 0

        target_length = target_length or self.config.max_history_messages

        # 简单截断（默认行为）
        if len(messages) <= target_length:
            return messages, 0

        # 保留 system prompt
        system_msg = messages[0] if messages[0].get("role") == "system" else None
        content_messages = messages[1:] if system_msg else messages

        # 尝试智能压缩
        if len(content_messages) > target_length:
            compressed = self._smart_compress(content_messages, target_length - 1)
            result = [system_msg] + compressed if system_msg else compressed
            tokens_saved = len(content_messages) - len(compressed)
            return result, tokens_saved

        return messages, 0

    def _smart_compress(self, messages: List[dict], target_length: int) -> List[dict]:
        """
        智能压缩：保留关键消息，合并相似内容
        """
        if len(messages) <= target_length:
            return messages

        # 策略1：保留最近的工具调用链和结果
        # 策略2：合并连续的 assistant 消息
        # 策略3：使用 LLM 生成摘要

        # 简单实现：保留首尾，中间部分按比例抽取
        head_count = max(1, target_length // 4)
        tail_count = target_length - head_count

        head = messages[:head_count]
        tail = messages[-tail_count:]

        # 如果首尾有重叠，只保留尾部
        if head_count + tail_count > len(messages):
            return tail

        return head + tail

    def compress_with_llm(self, messages: List[dict]) -> str:
        """
        使用 LLM 生成对话摘要
        """
        if not messages:
            return ""

        client = self._get_llm_client()

        # 构建摘要请求
        conversation_text = self._format_messages_for_summary(messages)

        try:
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a conversation summarizer. Create a concise summary of the following conversation, highlighting: 1) What the user asked 2) What actions were taken 3) What was accomplished. Keep it under 500 words."
                    },
                    {
                        "role": "user",
                        "content": f"Summarize this conversation:\n\n{conversation_text}"
                    }
                ],
                max_tokens=500,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"[Summary generation failed: {e}]"

    def _format_messages_for_summary(self, messages: List[dict]) -> str:
        """格式化消息用于摘要"""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "user":
                lines.append(f"USER: {content[:500]}")
            elif role == "assistant":
                if msg.get("tool_calls"):
                    tool_names = [tc.get("function", {}).get("name", "?") for tc in msg["tool_calls"]]
                    lines.append(f"ASSISTANT: Used tools: {', '.join(tool_names)}")
                elif content:
                    lines.append(f"ASSISTANT: {content[:500]}")
            elif role == "tool":
                tool_id = msg.get("tool_call_id", "?")[:8]
                lines.append(f"TOOL RESULT [{tool_id}]: {content[:200]}")

        return "\n".join(lines)

    def estimate_tokens(self, messages: List[dict]) -> int:
        """估算消息的 token 数量"""
        # 简单估算：每4个字符约1个token
        total_chars = sum(
            len(str(msg.get("content", ""))) +
            len(json.dumps(msg.get("tool_calls", [])))
            for msg in messages
        )
        return total_chars // 4


class SlidingWindowCompressor(ContextCompressor):
    """滑动窗口压缩器"""

    def __init__(self, window_size: int = 10, overlap: int = 2, config=None):
        super().__init__(config)
        self.window_size = window_size
        self.overlap = overlap

    def compress_messages(self, messages: List[dict], target_length: Optional[int] = None) -> Tuple[List[dict], int]:
        """使用滑动窗口压缩"""
        if len(messages) <= self.window_size:
            return messages, 0

        # 保留 system prompt 和最近的窗口
        system_msg = messages[0] if messages[0].get("role") == "system" else None
        content_messages = messages[1:] if system_msg else messages

        # 使用滑动窗口
        windows = []
        for i in range(0, len(content_messages), self.window_size - self.overlap):
            window = content_messages[i:i + self.window_size]
            if window:
                windows.append(window)

        # 取最后一个窗口
        compressed = windows[-1] if windows else []

        result = [system_msg] + compressed if system_msg else compressed
        tokens_saved = len(content_messages) - len(compressed)

        return result, tokens_saved


# 默认压缩器
def get_compressor(config=None) -> ContextCompressor:
    """获取压缩器实例"""
    return ContextCompressor(config)