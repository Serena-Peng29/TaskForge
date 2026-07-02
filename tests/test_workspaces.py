from pathlib import Path

from taskforge.config import Config
from taskforge.core.agents import AgentClient


def make_config(tmp_path: Path) -> Config:
    config = Config(
        workdir=tmp_path,
        api_key="test-key",
        base_url="http://test.local/v1",
    )
    config.set_workspace(tmp_path)
    return config


class TestWorkspacePermissions:
    def test_manual_mode_blocks_mutating_tools(self, tmp_path: Path):
        config = make_config(tmp_path)
        config.set_permission("manual")
        client = AgentClient(config)

        result = client.execute_tool("write_file", {"path": "demo.txt", "content": "hello"})

        assert "requires manual approval" in result
        assert not (tmp_path / "demo.txt").exists()

    def test_allowlist_mode_allows_listed_tool(self, tmp_path: Path):
        config = make_config(tmp_path)
        config.set_permission("allowlist", ["write_file"])
        client = AgentClient(config)

        result = client.execute_tool("write_file", {"path": "demo.txt", "content": "hello"})

        assert "Wrote" in result
        assert (tmp_path / "demo.txt").read_text(encoding="utf-8") == "hello"

    def test_allowlist_mode_blocks_unlisted_tool(self, tmp_path: Path):
        config = make_config(tmp_path)
        config.set_permission("allowlist", ["read_file"])
        client = AgentClient(config)

        result = client.execute_tool("write_file", {"path": "demo.txt", "content": "hello"})

        assert "not in the workspace allowlist" in result
        assert not (tmp_path / "demo.txt").exists()
