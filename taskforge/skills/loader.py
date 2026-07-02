"""
技能加载器
"""
from taskforge.config import logger
import re
from pathlib import Path
from typing import Dict, List, Optional


class SkillLoader:
    """技能加载器，负责管理外部知识模块"""

    def __init__(self, skills_dirs: List[Path] = None):
        """
        初始化技能加载器
        Args:
            skills_dirs: 技能目录列表，按优先级顺序加载（后面的覆盖前面的）
        """
        self.skills_dirs = skills_dirs or []
        self.skills: Dict[str, dict] = {}
        if self.skills_dirs:
            self.load_skills()
        else:
            logger.info("Skills directories not specified, skipping skill loading")

    def parse_skill_md(self, path: Path) -> Optional[dict]:
        """解析 SKILL.md 文件"""
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read skill file {path}: {e}")
            return None

        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            logger.warning(f"Invalid skill format in {path}")
            return None

        frontmatter, body = match.groups()
        metadata = {}
        for line in frontmatter.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip().strip("\"'")

        if "name" not in metadata or "description" not in metadata:
            logger.warning(f"Missing required fields in {path}")
            return None

        return {
            "name": metadata["name"],
            "description": metadata["description"],
            "body": body.strip(),
            "path": path,
            "dir": path.parent,
        }

    def load_skills(self):
        """加载所有技能（从多个目录）"""
        for skills_dir in self.skills_dirs:
            if not skills_dir.exists():
                logger.debug(f"Skills directory not found: {skills_dir}")
                continue

            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue
                skill = self.parse_skill_md(skill_md)
                if skill:
                    self.skills[skill["name"]] = skill
                    logger.info(f"Loaded skill: {skill['name']}")

    def get_descriptions(self) -> str:
        if not self.skills:
            return "(no skills available)"
        return "\n".join(
            f"- {name}: {skill['description']}"
            for name, skill in self.skills.items()
        )

    def get_skill_content(self, name: str) -> Optional[str]:
        if name not in self.skills:
            return None
        skill = self.skills[name]
        content = f"# Skill: {skill['name']}\n\n{skill['body']}"

        resources = []
        for folder, label in [("scripts", "Scripts"), ("references", "References"), ("assets", "Assets")]:
            folder_path = skill["dir"] / folder
            if folder_path.exists():
                files = list(folder_path.glob("*"))
                if files:
                    resources.append(f"{label}: {', '.join(f.name for f in files)}")

        if resources:
            content += f"\n\n**Available resources in {skill['dir']}:**\n"
            content += "\n".join(f"- {r}" for r in resources)
        return content

    def list_skills(self) -> List[str]:
        return list(self.skills.keys())

    def reload(self) -> None:
        """重新加载所有技能"""
        self.skills.clear()
        if self.skills_dirs:
            self.load_skills()


# 延迟初始化
_SKILLS = None

def get_skills():
    """获取技能加载器实例"""
    global _SKILLS
    if _SKILLS is None:
        from taskforge.config import get_config
        config = get_config()
        # 支持多个技能目录：skills/ 和 .agents/skills/
        skills_dirs = [config.workdir / "skills", config.workdir / ".agents" / "skills"]
        _SKILLS = SkillLoader(skills_dirs)
    return _SKILLS

# 向后兼容
SKILLS = get_skills()
