"""
内置工具实现
"""
import subprocess
from pathlib import Path
from typing import Optional, List
import json
import time

from .base import BaseTool, ToolResult, TOOLS
from SecurityChecker import SECURITY
from SkillLoader import SkillLoader
from .websearch import WebSearchTool


class BashTool(BaseTool):
    """Shell 命令执行工具"""

    name = "bash"
    description = "Run shell command. Dangerous commands will be blocked."

    def __init__(self, workdir: Path, timeout: int = 60, config=None):
        self.workdir = workdir
        self.timeout = timeout
        self.config = config

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute"
                        }
                    },
                    "required": ["command"]
                }
            }
        }

    def execute(self, command: str) -> ToolResult:
        """执行 shell 命令"""
        # 安全检查
        is_safe, message = SECURITY.check_command(command)
        if not is_safe:
            return ToolResult(
                success=False,
                content="",
                error=message
            )

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            output = (result.stdout + result.stderr).strip() or "(no output)"
            return ToolResult(
                success=True,
                content=output[:50000],
                metadata={"return_code": result.returncode}
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                content="",
                error=f"Command timed out after {self.timeout}s"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )


class ReadFileTool(BaseTool):
    """文件读取工具"""

    name = "read_file"
    description = "Read file contents. Returns the content of the specified file."

    def __init__(self, workdir: Path, output_dir: Path = None, enable_validation: bool = True):
        self.workdir = workdir
        self.output_dir = output_dir or workdir / "output"
        self.enable_validation = enable_validation

    def _safe_path(self, p: str, for_write: bool = False) -> Path:
        """验证并返回安全的文件路径"""
        # 基础校验：防止跳出工作区
        rel_path = Path(p).relative_to("/") if Path(p).is_absolute() else Path(p)

        # 路径穿越检查
        if self.enable_validation:
            resolved = (self.workdir / rel_path).resolve()
            try:
                resolved.relative_to(self.workdir.resolve())
            except ValueError:
                raise ValueError(f"Path escapes workspace: {p}")

        if for_write:
            target_path = (self.output_dir / rel_path).resolve()
            target_path.parent.mkdir(parents=True, exist_ok=True)
            return target_path
        else:
            modified_path = (self.output_dir / rel_path).resolve()
            if modified_path.exists():
                return modified_path
            return (self.workdir / rel_path).resolve()

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file (relative to workspace)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of lines to read"
                        }
                    },
                    "required": ["path"]
                }
            }
        }

    def execute(self, path: str, limit: Optional[int] = None) -> ToolResult:
        """读取文件内容"""
        try:
            file_path = self._safe_path(path)
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"File not found: {path}"
                )
            if not file_path.is_file():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Not a file: {path}"
                )

            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            if limit and limit > 0:
                lines = lines[:limit]

            return ToolResult(
                success=True,
                content="\n".join(lines)[:50000],
                metadata={"lines": len(lines), "path": str(file_path)}
            )
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                content="",
                error=f"Cannot read binary file: {path}"
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )


class WriteFileTool(BaseTool):
    """文件写入工具"""

    name = "write_file"
    description = "Write content to a file. Creates parent directories if needed."

    def __init__(self, workdir: Path, output_dir: Path = None, enable_validation: bool = True):
        self.workdir = workdir
        self.output_dir = output_dir or workdir / "output"
        self.enable_validation = enable_validation

    def _safe_path(self, p: str) -> Path:
        """验证并返回安全的文件路径"""
        rel_path = Path(p).relative_to("/") if Path(p).is_absolute() else Path(p)

        if self.enable_validation:
            resolved = (self.output_dir / rel_path).resolve()
            try:
                resolved.relative_to(self.workdir.resolve())
            except ValueError:
                raise ValueError(f"Path escapes workspace: {p}")
            return resolved

        return (self.output_dir / rel_path).resolve()

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file (relative to workspace)"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        }

    def execute(self, path: str, content: str) -> ToolResult:
        """写入文件"""
        try:
            file_path = self._safe_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return ToolResult(
                success=True,
                content=f"Wrote {len(content)} bytes to {path}",
                metadata={"bytes": len(content), "path": str(file_path)}
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )


class EditFileTool(BaseTool):
    """文件编辑工具"""

    name = "edit_file"
    description = "Replace text in a file. Only replaces the first occurrence."

    def __init__(self, workdir: Path, output_dir: Path = None, enable_validation: bool = True):
        self.workdir = workdir
        self.output_dir = output_dir or workdir / "output"
        self.enable_validation = enable_validation
        self._read_tool = ReadFileTool(workdir, output_dir, enable_validation)

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file (relative to workspace)"
                        },
                        "old_text": {
                            "type": "string",
                            "description": "Text to find and replace"
                        },
                        "new_text": {
                            "type": "string",
                            "description": "Text to replace with"
                        }
                    },
                    "required": ["path", "old_text", "new_text"]
                }
            }
        }

    def execute(self, path: str, old_text: str, new_text: str) -> ToolResult:
        """编辑文件（替换文本）"""
        try:
            file_path = self._read_tool._safe_path(path, for_write=True)
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"File not found: {path}"
                )

            text = file_path.read_text(encoding="utf-8")
            if old_text not in text:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Text not found in {path}"
                )

            new_content = text.replace(old_text, new_text, 1)
            file_path.write_text(new_content, encoding="utf-8")
            return ToolResult(
                success=True,
                content=f"Edited {path}",
                metadata={"path": str(file_path)}
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )


class TodoWriteTool(BaseTool):
    """任务列表工具"""

    name = "TodoWrite"
    description = "Update the task list. Use to track multi-step work progress."

    def __init__(self, todo_manager):
        self.todo_manager = todo_manager

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "description": "List of task items",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string", "description": "Task description"},
                                    "status": {
                                        "type": "string",
                                        "enum": ["pending", "in_progress", "completed"]
                                    },
                                    "activeForm": {
                                        "type": "string",
                                        "description": "Present continuous form (e.g., 'Running tests')"
                                    }
                                },
                                "required": ["content", "status", "activeForm"]
                            }
                        }
                    },
                    "required": ["items"]
                }
            }
        }

    def execute(self, items: List[dict]) -> ToolResult:
        """更新任务列表"""
        try:
            result = self.todo_manager.update(items)
            return ToolResult(success=True, content=result)
        except ValueError as e:
            return ToolResult(success=False, content="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class TaskTool(BaseTool):
    """子代理任务工具"""

    name = "Task"
    description = "Spawn a subagent for a focused subtask."

    def __init__(self, agent_types: dict, agent_runner):
        self.agent_types = agent_types
        self.agent_runner = agent_runner

    def get_schema(self) -> dict:
        agent_descriptions = "\n".join(
            f"- {name}: {cfg.description}"
            for name, cfg in self.agent_types.items()
        )
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": f"Spawn a subagent for a focused subtask.\n\nAgent types:\n{agent_descriptions}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Short task description (3-5 words)"
                        },
                        "prompt": {
                            "type": "string",
                            "description": "Detailed instructions for the subagent"
                        },
                        "agent_type": {
                            "type": "string",
                            "enum": list(self.agent_types.keys()),
                            "description": "Type of agent to spawn"
                        }
                    },
                    "required": ["description", "prompt", "agent_type"]
                }
            }
        }

    def execute(self, description: str, prompt: str, agent_type: str) -> ToolResult:
        """运行子代理任务"""
        if agent_type not in self.agent_types:
            available = ", ".join(self.agent_types.keys())
            return ToolResult(
                success=False,
                content="",
                error=f"Unknown agent type '{agent_type}'. Available: {available}"
            )

        result = self.agent_runner(description, prompt, agent_type)
        return ToolResult(success=True, content=result)


class SkillTool(BaseTool):
    """技能加载工具"""

    name = "Skill"
    description = "Load a skill to gain specialized knowledge for a task."

    def __init__(self, skills_loader):
        self.skills_loader = skills_loader

    def get_schema(self) -> dict:
        skills_desc = self.skills_loader.get_descriptions()
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": f"""Load a skill to gain specialized knowledge for a task.

Available skills:
{skills_desc}

When to use:
- IMMEDIATELY when user task matches a skill description
- Before attempting domain-specific work (PDF, MCP, etc.)""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill": {
                            "type": "string",
                            "description": "Name of the skill to load"
                        }
                    },
                    "required": ["skill"]
                }
            }
        }

    def execute(self, skill: str) -> ToolResult:
        """加载技能"""
        content = self.skills_loader.get_skill_content(skill)
        if content is None:
            available = ", ".join(self.skills_loader.list_skills()) or "none"
            return ToolResult(
                success=False,
                content="",
                error=f"Unknown skill '{skill}'. Available: {available}"
            )

        return ToolResult(
            success=True,
            content=f"""<skill-loaded name="{skill}">
{content}
</skill-loaded>

Follow the instructions in the skill above to complete the user's task.""",
            metadata={"skill": skill}
        )


def register_builtin_tools(config, todo_manager, skills_loader, agent_runner, agent_types):
    """注册内置工具"""
    TOOLS.register(BashTool(config.workdir, config.command_timeout, config))
    TOOLS.register(ReadFileTool(config.workdir, config.output_dir, config.enable_path_validation))
    TOOLS.register(WriteFileTool(config.workdir, config.output_dir, config.enable_path_validation))
    TOOLS.register(EditFileTool(config.workdir, config.output_dir, config.enable_path_validation))
    TOOLS.register(TodoWriteTool(todo_manager))
    TOOLS.register(TaskTool(agent_types, agent_runner))
    TOOLS.register(SkillTool(skills_loader))

    # 注册 Web Search 工具（如果启用且有 API key）
    if config.web_search_config.enabled and config.web_search_config.api_key:
        TOOLS.register(WebSearchTool(
            api_key=config.web_search_config.api_key,
            max_results=config.web_search_config.max_results,
            search_depth=config.web_search_config.search_depth
        ))

    return TOOLS