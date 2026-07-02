# Project Structure

Spark is currently in a transitional layout: the FastAPI app has been split into
the `api/` package, while core agent modules still live at the repository root.

## Current Layout

```text
main.py                 CLI and Web server entry point
api/                    FastAPI application package
tools/                  Tool abstractions and built-in tools
frontend/               React/Vite frontend
scripts/                Local utility scripts
skills/                 Bundled skills
tests/                  Backend tests
agents.py               Agent orchestration
auth.py                 User auth and JWT helpers
configurable.py         Runtime configuration
memory.py               Session and long-term memory
mcp_manager.py          MCP connection management
security_checker.py     Command safety checks
skill_loader.py         Skill discovery and loading
todo_manager.py         Todo state management
user_state.py           Per-user runtime state
```

## Next Refactor Target

When the current API split has enough tests, move root-level runtime modules into
a real package, for example:

```text
spark/
  cli.py
  config.py
  core/
    agents.py
    compression.py
    errors.py
  services/
    auth.py
    memory.py
    todo_manager.py
    user_state.py
  integrations/
    mcp_manager.py
  security/
    checker.py
  skills/
    loader.py
```

Do that move incrementally. Keep `main.py` as a compatibility entry point until
imports, tests, and packaging are all updated.
