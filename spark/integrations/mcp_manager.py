"""
MCP (Model Context Protocol) Manager
管理 MCP server 连接和工具
"""
import asyncio
import json
import logging
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

from tools.base import BaseTool, ToolResult, TOOLS

logger = logging.getLogger(__name__)


@dataclass
class MCPServerStatus:
    """MCP Server 状态"""
    name: str
    status: str = "disconnected"  # disconnected, connecting, connected, error
    error: Optional[str] = None
    tools: List[str] = field(default_factory=list)


class MCPTool(BaseTool):
    """包装 MCP tool 为 BaseTool"""

    def __init__(self, server_name: str, tool_info: Any, call_fn: Callable):
        """
        Args:
            server_name: MCP server 名称
            tool_info: MCP tool 信息对象
            call_fn: 异步调用函数
        """
        self._server_name = server_name
        self._tool_info = tool_info
        self._call_fn = call_fn
        self._original_name = tool_info.name

        # 生成唯一的工具名：mcp_{server}_{tool}
        self.name = f"mcp_{server_name}_{tool_info.name}"
        self.description = tool_info.description or f"MCP tool from {server_name}"

    def get_schema(self) -> dict:
        """返回工具的 JSON Schema 定义"""
        # MCP tool 的 inputSchema 已经是 JSON Schema 格式
        parameters = self._tool_info.inputSchema or {
            "type": "object",
            "properties": {},
            "required": []
        }

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters
            }
        }

    def execute(self, **kwargs) -> ToolResult:
        """执行工具 - 同步包装"""
        try:
            # 创建新的事件循环来运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._call_fn(kwargs))
                return self._process_result(result)
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"MCP tool {self.name} execution failed: {e}")
            return ToolResult(success=False, content="", error=str(e))

    async def execute_async(self, **kwargs) -> ToolResult:
        """异步执行工具"""
        try:
            result = await self._call_fn(kwargs)
            return self._process_result(result)
        except Exception as e:
            logger.error(f"MCP tool {self.name} execution failed: {e}")
            return ToolResult(success=False, content="", error=str(e))

    def _process_result(self, result: Any) -> ToolResult:
        """处理 MCP tool 返回结果"""
        if result is None:
            return ToolResult(success=True, content="Tool executed successfully (no output)")

        # MCP 返回的结果可能是列表（包含 content blocks）
        if isinstance(result, list):
            contents = []
            for item in result:
                if hasattr(item, 'content'):
                    contents.append(item.content)
                elif isinstance(item, dict) and 'content' in item:
                    contents.append(item['content'])
                else:
                    contents.append(str(item))
            return ToolResult(success=True, content="\n".join(contents))

        # 其他格式直接转字符串
        return ToolResult(success=True, content=str(result))


@dataclass
class MCPServerConnection:
    """MCP Server 连接信息"""
    name: str
    config: dict
    status: MCPServerStatus
    session: Any = None
    read_stream: Any = None
    write_stream: Any = None
    tools: Dict[str, MCPTool] = field(default_factory=dict)
    _task: Any = None


class MCPManager:
    """MCP Server 管理器"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: MCP 配置文件路径，默认为 workdir/mcp_config.json
        """
        self._servers: Dict[str, MCPServerConnection] = {}
        self._config_path = config_path
        self._mcp_available = self._check_mcp_available()

        if self._mcp_available:
            logger.info("MCP library available")
        else:
            logger.warning("MCP library not available. Install with: pip install mcp")

    def _check_mcp_available(self) -> bool:
        """检查 MCP 库是否可用"""
        try:
            from mcp import ClientSession
            return True
        except ImportError:
            return False

    def is_available(self) -> bool:
        """检查 MCP 功能是否可用"""
        return self._mcp_available

    async def connect_server(self, name: str, config: dict) -> MCPServerStatus:
        """
        连接到 MCP server

        Args:
            name: Server 名称
            config: Server 配置，包含 command 和 env

        Returns:
            MCPServerStatus 连接状态
        """
        if not self._mcp_available:
            return MCPServerStatus(
                name=name,
                status="error",
                error="MCP library not installed. Run: pip install mcp"
            )

        # 如果已存在，先断开
        if name in self._servers:
            await self.disconnect_server(name)

        status = MCPServerStatus(name=name, status="connecting")

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            # 解析命令
            command_str = config.get("command", "")
            env = config.get("env", {})

            if not command_str:
                raise ValueError("Missing 'command' in server config")

            # 解析命令字符串
            # 支持: "npx -y mcp-remote https://..." 或 "python server.py"
            parts = command_str.split()
            if not parts:
                raise ValueError("Empty command")

            command = parts[0]
            args = parts[1:] if len(parts) > 1 else []

            # 检查命令是否存在
            if not shutil.which(command):
                raise ValueError(f"Command not found: {command}")

            logger.info(f"Connecting to MCP server '{name}': {command_str}")

            # 创建 server 参数
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env if env else None
            )

            # 创建连接
            read_stream, write_stream = await stdio_client(server_params)

            # 创建 session
            session = ClientSession(read_stream, write_stream)
            await session.initialize()

            # 获取工具列表
            tools_response = await session.list_tools()
            tools_list = tools_response.tools if hasattr(tools_response, 'tools') else []

            # 创建工具包装
            tools_dict = {}
            for tool_info in tools_list:
                tool_name = tool_info.name

                # 创建闭包捕获 session 和 tool_name
                async def make_call_fn(sess, t_name):
                    async def call_fn(args):
                        return await sess.call_tool(t_name, arguments=args)
                    return call_fn

                call_fn = await make_call_fn(session, tool_name)
                mcp_tool = MCPTool(name, tool_info, call_fn)
                tools_dict[tool_name] = mcp_tool

                # 注册到全局工具注册表
                TOOLS.register(mcp_tool)

            # 保存连接信息
            connection = MCPServerConnection(
                name=name,
                config=config,
                status=MCPServerStatus(
                    name=name,
                    status="connected",
                    tools=list(tools_dict.keys())
                ),
                session=session,
                read_stream=read_stream,
                write_stream=write_stream,
                tools=tools_dict
            )
            self._servers[name] = connection

            logger.info(f"MCP server '{name}' connected with {len(tools_dict)} tools")
            return connection.status

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to connect MCP server '{name}': {error_msg}")
            return MCPServerStatus(
                name=name,
                status="error",
                error=error_msg
            )

    async def disconnect_server(self, name: str) -> bool:
        """
        断开 MCP server 连接

        Args:
            name: Server 名称

        Returns:
            是否成功断开
        """
        if name not in self._servers:
            return False

        connection = self._servers[name]

        try:
            # 从工具注册表中移除
            for tool_name, tool in connection.tools.items():
                TOOLS.unregister(tool.name)

            # 关闭 session
            if connection.session:
                try:
                    await connection.session.close()
                except Exception as e:
                    logger.warning(f"Error closing session for '{name}': {e}")

            # 关闭 streams
            if connection.read_stream:
                try:
                    await connection.read_stream.aclose()
                except Exception:
                    pass

            if connection.write_stream:
                try:
                    await connection.write_stream.aclose()
                except Exception:
                    pass

            del self._servers[name]
            logger.info(f"MCP server '{name}' disconnected")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting MCP server '{name}': {e}")
            return False

    def get_server_status(self, name: str) -> Optional[MCPServerStatus]:
        """获取 server 状态"""
        if name in self._servers:
            return self._servers[name].status
        return MCPServerStatus(name=name, status="disconnected")

    def get_all_servers_status(self) -> List[MCPServerStatus]:
        """获取所有 server 状态"""
        return [conn.status for conn in self._servers.values()]

    def get_all_tools(self) -> List[MCPTool]:
        """获取所有 MCP 工具"""
        tools = []
        for conn in self._servers.values():
            tools.extend(conn.tools.values())
        return tools

    def get_tool_schemas(self) -> List[dict]:
        """获取所有 MCP 工具的 schema"""
        return [tool.get_schema() for tool in self.get_all_tools()]

    def has_server(self, name: str) -> bool:
        """检查 server 是否存在"""
        return name in self._servers

    def list_servers(self) -> List[str]:
        """列出所有已连接的 server 名称"""
        return list(self._servers.keys())

    async def load_config(self, config_dict: dict) -> Dict[str, MCPServerStatus]:
        """
        从配置字典加载 MCP servers

        Args:
            config_dict: 配置字典，格式：
                {
                    "mcpServers": {
                        "server-name": {
                            "command": "npx -y mcp-remote https://...",
                            "env": {}
                        }
                    }
                }

        Returns:
            每个服务器的连接状态
        """
        results = {}
        mcp_servers = config_dict.get("mcpServers", {})

        for name, server_config in mcp_servers.items():
            status = await self.connect_server(name, server_config)
            results[name] = status

        return results

    def save_config(self, config_dict: dict) -> bool:
        """
        保存 MCP 配置到文件

        Args:
            config_dict: MCP 配置字典

        Returns:
            是否保存成功
        """
        if not self._config_path:
            logger.warning("No config path set, cannot save MCP config")
            return False

        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"MCP config saved to {self._config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save MCP config: {e}")
            return False

    def load_config_from_file(self) -> dict:
        """
        从文件加载 MCP 配置

        Returns:
            MCP 配置字典
        """
        if not self._config_path or not self._config_path.exists():
            return {"mcpServers": {}}

        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            return {"mcpServers": {}}


# 全局 MCP 管理器实例
_MCP_MANAGER: Optional[MCPManager] = None


def get_mcp_manager(config_path: Optional[Path] = None) -> MCPManager:
    """获取全局 MCP 管理器实例"""
    global _MCP_MANAGER
    if _MCP_MANAGER is None:
        _MCP_MANAGER = MCPManager(config_path)
    return _MCP_MANAGER