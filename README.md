# PyCode Agent

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

## 项目结构

```
.
├── main.py              # 主入口
├── configurable.py      # 配置管理
├── Agents.py            # Agent 核心逻辑
├── tools/               # 工具系统
│   ├── __init__.py
│   ├── base.py          # 工具基类
│   └── builtin.py       # 内置工具
├── skills/              # 技能模块
├── memory.py            # 会话管理
├── SecurityChecker.py   # 安全检查
├── TodoManager.py       # 任务管理
├── errors.py            # 异常处理
├── compression.py       # 上下文压缩
└── tests/               # 测试
```

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
pytest tests/
```

## 许可证

MIT