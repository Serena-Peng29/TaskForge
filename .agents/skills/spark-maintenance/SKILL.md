---
name: spark-maintenance
description: Maintain, audit, stabilize, and modernize the local Spark project at /Users/serena.peng/iDreamsky/Spark. Use when Codex is asked to optimize Spark, fix Spark tests or builds, review Spark security, refactor the Python/FastAPI agent backend, improve the React/Vite frontend, work on MCP/tool execution/auth/memory code, or create a safe maintenance plan for this legacy project.
---

# Spark Maintenance

## Overview

Use this skill for the Spark repository, a Python AI coding-agent app with FastAPI APIs, MCP integration, tool execution, memory/auth modules, bundled skills, and a React/Vite frontend. Bias toward safety, reproducibility, and regression protection before broad refactors.

Default project path:

```bash
/Users/serena.peng/iDreamsky/Spark
```

## First Moves

1. Inspect the worktree before editing:

```bash
git status --short --branch
rg --files -g '!frontend/node_modules/**' -g '!__pycache__/**' -g '!.pytest_cache/**'
```

2. Treat existing uncommitted changes as user work. Do not revert or overwrite them unless the user explicitly asks.
3. Read likely entry points before deciding on edits:

```bash
README.md
pyproject.toml
requirements.txt
main.py
agents.py
api.py
api/app.py
api/routers/*.py
tools/builtin.py
security_checker.py
mcp_manager.py
auth.py
memory.py
frontend/package.json
frontend/src/api/client.ts
frontend/src/components/*.tsx
```

4. If network commands fail, retry them with:

```bash
HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897
```

## Maintenance Order

Use this order unless the user asks for a narrower task:

1. Establish a baseline: current git status, dependency files, failing tests, failing builds, and high-risk files.
2. Fix the local environment before judging code quality.
3. Address security and secret-handling risks before broad refactors.
4. Add or repair focused tests around high-risk behavior.
5. Refactor incrementally, preserving public behavior and existing project boundaries.
6. Run the smallest meaningful verification after each change; broaden verification for shared code.

## Environment Baseline

Check Python first. This machine may have `python` pointing at another project venv, so prefer an explicit Spark venv:

```bash
cd /Users/serena.peng/iDreamsky/Spark
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
```

Use these backend checks:

```bash
python -m pytest -q
python -m ruff check .
python -m mypy .
```

Check frontend dependencies and build:

```bash
cd /Users/serena.peng/iDreamsky/Spark/frontend
npm install
npm run build
```

If `frontend/node_modules/.bin/tsc` is not executable, prefer reinstalling dependencies over chmod-only fixes unless the user asks for the smallest local repair.

## Security Priorities

Prioritize these areas:

- `tools/builtin.py`: command execution, `shell=True`, timeout handling, output limits, working directory constraints.
- `security_checker.py`: command filtering, path validation, bypasses, case sensitivity, symlink handling.
- `mcp_manager.py`: MCP server command/env validation, config import, lifecycle cleanup, remote command injection risk.
- `auth.py` and `api/routers/auth.py`: default JWT secret, password handling, token expiry, auth-disabled fallback behavior.
- `memory.py`: external service config, API key handling, persistence boundaries.
- `mcp_config.json`, `.env*`, config files: possible secret leakage.

Do not print full secret values. If a credential appears committed or stored in a project config, tell the user to rotate it and replace it with an environment variable or ignored local config.

## Testing Targets

When adding tests, prefer narrow tests for behavior that can break silently:

- dangerous command rejection and allowed command execution;
- path traversal and symlink/path normalization;
- MCP config import validation and malformed server configs;
- JWT login, bad token, expired token, and auth-disabled behavior;
- tool-call argument parsing and error propagation;
- chat streaming behavior where feasible without live API calls.

Mock external APIs and MCP processes. Avoid tests that require real OpenAI, Qdrant, Tavily, or remote MCP credentials.

## Refactor Guidance

Keep refactors small and behavior-preserving:

- Prefer moving endpoints from the large `api.py` into `api/routers/*` only when tests or smoke checks cover the path.
- Preserve compatibility for frontend API paths under `/api/*`.
- Keep model/schema changes in `api/schemas.py` and update frontend `frontend/src/types.ts` together.
- Avoid renaming public files or classes unless the surrounding code already moved in that direction.
- When touching `agents.py`, `tools/`, or `mcp_manager.py`, assume downstream behavior is fragile and add focused tests first.

## Frontend Guidance

The frontend is a Vite/React app under `frontend/`.

- Build before and after meaningful frontend changes with `npm run build`.
- Prefer shared API handling in `frontend/src/api/client.ts` over ad hoc `fetch` calls in components.
- Keep auth token behavior consistent between `useAuth.ts`, API client helpers, and components.
- Treat large components such as `MCPModal.tsx`, `ConfigPanel.tsx`, and `MemoryPanel.tsx` as candidates for incremental extraction only after build passes.

## Reporting

For maintenance work, report:

- what baseline checks were run and their result;
- what files changed;
- what risks were fixed or intentionally left for later;
- any tests/builds that could not be run and why.
