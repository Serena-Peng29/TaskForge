import logging
import sys
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Optional
import json


@dataclass
class MemoryConfig:
    """记忆系统配置"""
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    collection_name: str = "toymagic_memories"
    enable_auto_extract: bool = True
    # Embedding 配置
    embedder_api_key: str = ""
    embedder_model: str = "text-embedding-v4"
    embedder_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"


@dataclass
class WebSearchConfig:
    """Web 搜索配置"""
    enabled: bool = True
    api_key: str = ""
    max_results: int = 5
    search_depth: str = "basic"


@dataclass
class MCPServerConfig:
    """单个 MCP Server 配置"""
    command: str = ""
    env: dict = field(default_factory=dict)


@dataclass
class MCPConfig:
    """MCP 整体配置"""
    servers: dict = field(default_factory=dict)  # {server_name: MCPServerConfig}


@dataclass
class AuthConfig:
    """认证配置"""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24小时
    users_collection: str = "toymagic_users"  # Qdrant collection 名称

# 支持 YAML 配置文件
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def setup_logging(level: str = "INFO", log_format: str = "text", log_file: str = "agent.log"):
    """配置日志系统"""
    handlers = [
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]

    if log_format == "json":
        try:
            import python_json_logger
            formatter = python_json_logger.JsonFormatter(
                '%(asctime)s %(levelname)s %(name)s %(message)s'
            )
            for h in handlers:
                h.setFormatter(formatter)
        except ImportError:
            log_format = "text"

    if log_format == "text":
        for h in handlers:
            h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=handlers
    )
    return logging.getLogger(__name__)


@dataclass
class Config:
    """集中配置管理 - 支持环境变量和配置文件"""
    workdir: Path = field(default_factory=Path.cwd)
    skills_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    api_key: str = ""
    base_url: str = ""
    model: str = "global.anthropic.claude-opus-4-5-20251101-v1:0"
    max_tokens: int = 8000
    max_history_messages: int = 50
    max_subagent_iterations: int = 20
    api_retry_attempts: int = 3
    api_retry_delay: float = 1.0
    command_timeout: int = 60
    log_level: str = "INFO"
    log_format: str = "text"
    enable_path_validation: bool = True
    temperature: float = 0.7  # 模型温度
    # Web Server 配置
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    cors_origins: list = field(default_factory=lambda: ["*"])
    # Memory 配置
    memory_config: MemoryConfig = field(default_factory=MemoryConfig)
    # Web Search 配置
    web_search_config: WebSearchConfig = field(default_factory=WebSearchConfig)
    # MCP 配置
    mcp_config: MCPConfig = field(default_factory=MCPConfig)
    # Auth 配置
    auth_config: AuthConfig = field(default_factory=AuthConfig)

    def __post_init__(self):
        # 设置工作目录相关路径
        if self.skills_dir is None:
            self.skills_dir = self.workdir / "skills"
        if self.output_dir is None:
            self.output_dir = self.workdir / "output"

        # 加载配置（优先级：环境变量 > 配置文件 > 默认值）
        self._load_from_file()
        self._load_from_env()

        # 验证必需配置
        self._validate()

        # 初始化日志
        global logger
        logger = setup_logging(self.log_level, self.log_format)

    def _load_from_file(self):
        """从配置文件加载"""
        config_files = [
            self.workdir / "config.yaml",
            self.workdir / "config.yml",
            self.workdir / "config.json",
        ]

        for config_file in config_files:
            if config_file.exists():
                try:
                    if config_file.suffix in (".yaml", ".yml"):
                        if not YAML_AVAILABLE:
                            print(f"Warning: YAML config found but PyYAML not installed. Run: pip install pyyaml")
                            continue
                        with open(config_file, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f) or {}
                    else:
                        with open(config_file, "r", encoding="utf-8") as f:
                            data = json.load(f)

                    # 解析配置
                    api_config = data.get("api", {})
                    agent_config = data.get("agent", {})
                    log_config = data.get("logging", {})
                    security_config = data.get("security", {})

                    if api_config.get("key"):
                        self.api_key = api_config["key"]
                    if api_config.get("base_url"):
                        self.base_url = api_config["base_url"]
                    if api_config.get("model"):
                        self.model = api_config["model"]
                    if api_config.get("max_tokens"):
                        self.max_tokens = api_config["max_tokens"]
                    if api_config.get("retry_attempts"):
                        self.api_retry_attempts = api_config["retry_attempts"]
                    if api_config.get("retry_delay"):
                        self.api_retry_delay = api_config["retry_delay"]

                    if agent_config.get("max_history_messages"):
                        self.max_history_messages = agent_config["max_history_messages"]
                    if agent_config.get("max_subagent_iterations"):
                        self.max_subagent_iterations = agent_config["max_subagent_iterations"]
                    if agent_config.get("command_timeout"):
                        self.command_timeout = agent_config["command_timeout"]

                    if log_config.get("level"):
                        self.log_level = log_config["level"]
                    if log_config.get("format"):
                        self.log_format = log_config["format"]

                    if "enable_path_validation" in security_config:
                        self.enable_path_validation = security_config["enable_path_validation"]

                    # Web Server 配置
                    server_config = data.get("server", {})
                    if server_config.get("host"):
                        self.server_host = server_config["host"]
                    if server_config.get("port"):
                        self.server_port = int(server_config["port"])
                    if server_config.get("cors_origins"):
                        self.cors_origins = server_config["cors_origins"]

                    # Memory 配置
                    memory_config = data.get("memory", {})
                    if memory_config:
                        self.memory_config = MemoryConfig(
                            qdrant_host=memory_config.get("qdrant_host", "localhost"),
                            qdrant_port=memory_config.get("qdrant_port", 6333),
                            collection_name=memory_config.get("collection_name", "toymagic_memories"),
                            enable_auto_extract=memory_config.get("enable_auto_extract", True),
                            embedder_api_key=memory_config.get("embedder_api_key", ""),
                            embedder_model=memory_config.get("embedder_model", "text-embedding-v4"),
                            embedder_base_url=memory_config.get("embedder_base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
                        )

                    # Web Search 配置
                    web_search_config = data.get("web_search", {})
                    if web_search_config:
                        self.web_search_config = WebSearchConfig(
                            enabled=web_search_config.get("enabled", True),
                            api_key=web_search_config.get("api_key", ""),
                            max_results=web_search_config.get("max_results", 5),
                            search_depth=web_search_config.get("search_depth", "basic")
                        )

                    # MCP 配置
                    mcp_config = data.get("mcp", {})
                    if mcp_config:
                        servers = {}
                        for server_name, server_cfg in mcp_config.get("servers", {}).items():
                            servers[server_name] = MCPServerConfig(
                                command=server_cfg.get("command", ""),
                                env=server_cfg.get("env", {})
                            )
                        self.mcp_config = MCPConfig(servers=servers)

                    # Auth 配置
                    auth_config = data.get("auth", {})
                    if auth_config:
                        self.auth_config = AuthConfig(
                            jwt_secret=auth_config.get("jwt_secret", "change-me-in-production"),
                            jwt_algorithm=auth_config.get("jwt_algorithm", "HS256"),
                            access_token_expire_minutes=auth_config.get("access_token_expire_minutes", 1440),
                            users_collection=auth_config.get("users_collection", "toymagic_users")
                        )

                    print(f"[Config] Loaded from {config_file}")
                    return
                except Exception as e:
                    print(f"Warning: Failed to load config file {config_file}: {e}")

    def _load_from_env(self):
        """从环境变量加载（优先级最高）"""
        env_mappings = {
            "OPENAI_API_KEY": "api_key",
            "OPENAI_BASE_URL": "base_url",
            "AGENT_MODEL": "model",
            "AGENT_MAX_TOKENS": ("max_tokens", int),
            "AGENT_TIMEOUT": ("command_timeout", int),
            "LOG_LEVEL": "log_level",
        }

        for env_key, config_attr in env_mappings.items():
            value = os.getenv(env_key)
            if value:
                if isinstance(config_attr, tuple):
                    attr_name, converter = config_attr
                    try:
                        setattr(self, attr_name, converter(value))
                    except ValueError:
                        pass
                else:
                    setattr(self, config_attr, value)

    def _validate(self):
        """验证必需配置"""
        errors = []

        if not self.api_key:
            errors.append(
                "API key is required. Set OPENAI_API_KEY environment variable "
                "or add 'api.key' to config.yaml"
            )

        if not self.base_url:
            errors.append(
                "Base URL is required. Set OPENAI_BASE_URL environment variable "
                "or add 'api.base_url' to config.yaml"
            )

        if errors:
            print("\n[Configuration Error]")
            for error in errors:
                print(f"  - {error}")
            print("\nPlease create a config.yaml file (see config.example.yaml) "
                  "or set the required environment variables.")
            raise ValueError("Missing required configuration")


# 延迟初始化配置
def init_config(workdir: Path = None) -> Config:
    """初始化配置"""
    return Config(workdir=workdir or Path.cwd())


# 全局配置实例（延迟初始化）
_CONFIG: Optional[Config] = None

def get_config() -> Config:
    """获取全局配置实例"""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = init_config()
    return _CONFIG


# 向后兼容
CONFIG = None  # 将在模块加载后设置

# 初始化日志（基础配置，会在 Config 初始化后更新）
logger = logging.getLogger(__name__)