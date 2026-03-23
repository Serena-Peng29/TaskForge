"""
Web 搜索工具
使用 Tavily API 进行网络搜索
"""
import json
from typing import Optional, List
from pathlib import Path

from .base import BaseTool, ToolResult


class WebSearchTool(BaseTool):
    """网络搜索工具"""

    name = "web_search"
    description = "Search the web for information. Returns relevant search results with titles, URLs, and snippets."

    def __init__(self, api_key: str = "", max_results: int = 5, search_depth: str = "basic"):
        """
        初始化 Web 搜索工具

        Args:
            api_key: Tavily API Key
            max_results: 最大返回结果数
            search_depth: 搜索深度 ("basic" 或 "advanced")
        """
        self.api_key = api_key
        self.max_results = max_results
        self.search_depth = search_depth

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "(Required) The specific search string or question you want to find information for. Be as detailed as possible."
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 5)"
                        },
                        "search_depth": {
                            "type": "string",
                            "enum": ["basic", "advanced"],
                            "description": "Search depth - 'advanced' for more thorough results"
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def execute(self, query: str = None, **kwargs) -> ToolResult:
        """执行网络搜索"""
        if not self.api_key:
            return ToolResult(
                success=False,
                content="",
                error="Tavily API key not configured. Please add 'web_search.api_key' to config.yaml"
            )
        if query is None:
            query = kwargs.get("query")
        if not query:
            return ToolResult(
                success=False,
                content="",
                error="Missing search query. Please provide a 'query' parameter."
            )
        max_results = kwargs.get("max_results") or self.max_results
        search_depth = kwargs.get("search_depth") or self.search_depth

        try:
            # 尝试导入 tavily-python
            try:
                from tavily import TavilyClient
            except ImportError:
                return ToolResult(
                    success=False,
                    content="",
                    error="tavily-python not installed. Run: pip install tavily-python"
                )

            # 执行搜索
            client = TavilyClient(api_key=self.api_key)
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth
            )

            # 格式化结果
            results = response.get("results", [])
            if not results:
                return ToolResult(
                    success=True,
                    content=f"No results found for: {query}",
                    metadata={"query": query, "count": 0}
                )

            # 构建输出
            output_lines = [f"Search results for: {query}\n"]
            for i, result in enumerate(results, 1):
                title = result.get("title", "No title")
                url = result.get("url", "")
                content = result.get("content", "")
                score = result.get("score", 0)

                output_lines.append(f"[{i}] {title}")
                output_lines.append(f"    URL: {url}")
                output_lines.append(f"    Score: {score:.2f}")
                output_lines.append(f"    {content[:300]}{'...' if len(content) > 300 else ''}")
                output_lines.append("")

            # 如果有相关图片，添加到结果
            images = response.get("images", [])
            if images:
                output_lines.append("Related images:")
                for img in images[:3]:
                    output_lines.append(f"  - {img}")

            return ToolResult(
                success=True,
                content="\n".join(output_lines),
                metadata={
                    "query": query,
                    "count": len(results),
                    "search_depth": search_depth
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Search failed: {str(e)}"
            )


class WebSearchConfig:
    """Web 搜索配置"""
    def __init__(
        self,
        api_key: str = "",
        max_results: int = 5,
        search_depth: str = "basic",
        enabled: bool = True
    ):
        self.api_key = api_key
        self.max_results = max_results
        self.search_depth = search_depth
        self.enabled = enabled