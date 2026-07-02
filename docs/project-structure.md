# Project Structure

TaskForge uses a package layout for backend runtime code. The repository root keeps
entry points, project configuration, documentation, and top-level app folders.

## Current Layout

```text
main.py       CLI and Web server entry point
taskforge/    Backend runtime package
api/          FastAPI application package
tools/        Tool abstractions and built-in tools
frontend/     React/Vite frontend
scripts/      Local utility scripts
skills/       Bundled skills
tests/        Backend tests
```

## Runtime Package

The `taskforge/` package is organized by responsibility:

```text
taskforge/
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

Keep `main.py` as a compatibility entry point for local runs. New imports should
prefer `taskforge.*` modules directly.
