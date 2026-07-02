"""
本地工作区配置管理。
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from taskforge.config import Config


PERMISSION_MODES = {"auto", "allowlist", "manual"}


@dataclass
class Workspace:
    id: str
    name: str
    path: str
    permission_mode: str = "manual"
    allowed_tools: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Workspace":
        mode = data.get("permission_mode") or "manual"
        if mode not in PERMISSION_MODES:
            mode = "manual"
        return cls(
            id=str(data.get("id") or uuid4().hex),
            name=str(data.get("name") or Path(str(data.get("path", ""))).name or "Workspace"),
            path=str(data.get("path") or ""),
            permission_mode=mode,
            allowed_tools=list(data.get("allowed_tools") or []),
        )

    def to_dict(self, active_path: Path | None = None) -> dict[str, Any]:
        is_active = False
        if active_path is not None:
            try:
                is_active = Path(self.path).expanduser().resolve() == active_path.resolve()
            except OSError:
                is_active = False
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "permission_mode": self.permission_mode,
            "allowed_tools": self.allowed_tools,
            "is_active": is_active,
        }


class WorkspaceStore:
    """持久化工作区列表到项目本地 JSON 文件。"""

    def __init__(self, config: Config):
        self.config = config
        self.path = config.workdir / "workspaces.json"

    def _load_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"workspaces": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"workspaces": []}

    def _save_raw(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def list(self) -> list[Workspace]:
        return [Workspace.from_dict(item) for item in self._load_raw().get("workspaces", [])]

    def list_dicts(self) -> list[dict[str, Any]]:
        active_path = self.config.workspace_dir or self.config.workdir
        return [workspace.to_dict(active_path) for workspace in self.list()]

    def ensure_active(self) -> Workspace:
        active_path = self.config.workspace_dir or self.config.workdir
        resolved_active = active_path.expanduser().resolve()
        workspaces = self.list()
        for workspace in workspaces:
            if Path(workspace.path).expanduser().resolve() == resolved_active:
                return workspace

        workspace = Workspace(
            id=uuid4().hex,
            name=resolved_active.name or "Workspace",
            path=str(resolved_active),
            permission_mode=self.config.permission_mode,
            allowed_tools=self.config.allowed_tools,
        )
        workspaces.append(workspace)
        self._save_raw({"workspaces": [item.to_dict() for item in workspaces]})
        return workspace

    def add(self, path: str, name: str | None = None, permission_mode: str = "manual", allowed_tools: list[str] | None = None) -> Workspace:
        workspace_path = Path(path).expanduser()
        if not workspace_path.is_absolute():
            workspace_path = (self.config.workdir / workspace_path).resolve()
        else:
            workspace_path = workspace_path.resolve()
        if not workspace_path.exists():
            raise ValueError(f"Workspace does not exist: {workspace_path}")
        if not workspace_path.is_dir():
            raise ValueError(f"Workspace is not a directory: {workspace_path}")
        if permission_mode not in PERMISSION_MODES:
            raise ValueError(f"Invalid permission mode: {permission_mode}")

        workspaces = self.list()
        for workspace in workspaces:
            if Path(workspace.path).expanduser().resolve() == workspace_path:
                workspace.name = name or workspace.name
                workspace.permission_mode = permission_mode
                workspace.allowed_tools = list(allowed_tools or workspace.allowed_tools)
                self._save_raw({"workspaces": [item.to_dict() for item in workspaces]})
                return workspace

        workspace = Workspace(
            id=uuid4().hex,
            name=name or workspace_path.name or "Workspace",
            path=str(workspace_path),
            permission_mode=permission_mode,
            allowed_tools=list(allowed_tools or []),
        )
        workspaces.append(workspace)
        self._save_raw({"workspaces": [item.to_dict() for item in workspaces]})
        return workspace

    def get(self, workspace_id: str) -> Workspace:
        for workspace in self.list():
            if workspace.id == workspace_id:
                return workspace
        raise KeyError(workspace_id)

    def update(
        self,
        workspace_id: str,
        name: str | None = None,
        permission_mode: str | None = None,
        allowed_tools: list[str] | None = None,
    ) -> Workspace:
        if permission_mode is not None and permission_mode not in PERMISSION_MODES:
            raise ValueError(f"Invalid permission mode: {permission_mode}")

        workspaces = self.list()
        for workspace in workspaces:
            if workspace.id == workspace_id:
                if name is not None:
                    workspace.name = name
                if permission_mode is not None:
                    workspace.permission_mode = permission_mode
                if allowed_tools is not None:
                    workspace.allowed_tools = list(dict.fromkeys(allowed_tools))
                self._save_raw({"workspaces": [item.to_dict() for item in workspaces]})
                return workspace
        raise KeyError(workspace_id)

    def delete(self, workspace_id: str) -> None:
        workspaces = self.list()
        remaining = [workspace for workspace in workspaces if workspace.id != workspace_id]
        if len(remaining) == len(workspaces):
            raise KeyError(workspace_id)
        self._save_raw({"workspaces": [item.to_dict() for item in remaining]})
