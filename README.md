# Spark Agent

基于 OpenAI SDK 的 AI 编码助手框架。

## 特性

- **工具系统**: 模块化的工具架构，支持动态注册
- **技能系统**: 可扩展的技能模块，支持领域知识注入
- **子代理**: 支持多种专用子代理类型
- **会话管理**: 自动保存/恢复对话历史
- **安全机制**: 命令过滤、路径验证
- **异步支持**: 流式输出

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

复制配置模板并修改：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，填入你的 API key。

或者使用环境变量：

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="your-base-url"
```

### 运行

```bash
python main.py
```

启动 Web API：

```bash
python main.py --web
```

## 项目结构

```
.
├── main.py                # CLI / Web 启动入口
├── api/                   # FastAPI 应用、路由和请求/响应模型
│   ├── app.py             # FastAPI app 组装
│   ├── deps.py            # 共享依赖、认证和状态上下文
│   ├── schemas.py         # Pydantic 模型
│   └── routers/           # auth/chat/config/mcp/memory/session 路由
├── tools/                 # 工具系统
│   ├── base.py            # 工具基类和注册表
│   ├── builtin.py         # 内置工具
│   └── websearch.py       # Web 搜索工具
├── frontend/              # React/Vite 前端
├── scripts/               # 辅助脚本
├── skills/                # 内置技能包
├── tests/                 # 后端测试
├── agents.py              # Agent 核心逻辑
├── auth.py                # 认证和 JWT 管理
├── configurable.py        # 配置管理
├── memory.py              # 会话和长期记忆
├── mcp_manager.py         # MCP server 连接和工具包装
├── security_checker.py    # 命令安全检查
├── skill_loader.py        # 技能加载器
├── todo_manager.py        # 任务列表管理
└── user_state.py          # 用户状态隔离
```

根目录保留启动入口、项目配置和当前尚未拆包的核心模块。新的 Web API 代码以 `api/` 包为准；旧的单文件 `api.py` 已移除，避免和 `api/` 包产生重复入口。

## 内置命令

| 命令 | 说明 |
|------|------|
| `exit` | 退出程序 |
| `clear` | 清除历史 |
| `status` | 显示状态 |
| `skills` | 列出技能 |
| `tokens` | Token 统计 |
| `load` | 加载上次会话 |
| `save` | 保存当前会话 |
| `memory` | 显示内存信息 |

## 扩展

### 添加新工具

```python
from tools.base import BaseTool, ToolResult, TOOLS

class MyTool(BaseTool):
    name = "my_tool"
    description = "My custom tool"

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"}
                    },
                    "required": ["input"]
                }
            }
        }

    def execute(self, input: str) -> ToolResult:
        # 实现你的逻辑
        return ToolResult(success=True, content=f"Processed: {input}")

# 注册工具
TOOLS.register(MyTool())
```

### 添加新技能

在 `skills/` 目录下创建新文件夹，添加 `SKILL.md`：

```markdown
---
name: my-skill
description: My custom skill
---

# My Skill

Skill instructions here...
```

## 测试

```bash
python -m pytest -q
cd frontend && npm run build
```

## 许可证

MIT
