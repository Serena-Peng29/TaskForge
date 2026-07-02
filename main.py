"""
PyCode Agent 主入口
"""
from pathlib import Path
import sys
import argparse

# 初始化配置
from configurable import get_config, init_config, logger
CONFIG = get_config()

from skill_loader import SKILLS
from agents import AGENT_TYPES, get_agent_descriptions, agent_loop, TOKEN_USAGE
from memory import get_memory
MEMORY = get_memory()

from todo_manager import TODO
from api.deps import DEFAULT_SYSTEM_PROMPT


def get_system_prompt() -> str:
    return DEFAULT_SYSTEM_PROMPT.format(
        workdir=str(CONFIG.workdir),
        skills=SKILLS.get_descriptions(),
        agents=get_agent_descriptions()
    )

def print_banner():
    """打印启动信息"""
    print("=" * 60)
    print(f"  PyCode Agent v3.0 (Async / Tools Framework / Skills)")
    print("=" * 60)
    print(f"  Workspace: {CONFIG.workdir}")
    print(f"  Output:    {CONFIG.output_dir}")
    print(f"  Model:     {CONFIG.model}")
    print(f"  Skills:    {', '.join(SKILLS.list_skills()) or 'none'}")
    print(f"  Agents:    {', '.join(AGENT_TYPES.keys())}")
    print(f"  Memory:    {MEMORY.memory_dir}")
    print(f"  Security:  Path validation {'enabled' if CONFIG.enable_path_validation else 'disabled'}")
    print("=" * 60)
    print("  Commands:")
    print("    'exit'    - Quit")
    print("    'clear'   - Reset history")
    print("    'status'  - Show session info")
    print("    'skills'  - List available skills")
    print("    'tokens'  - Show token usage")
    print("    'load'    - Load last session")
    print("    'save'    - Save current session")
    print("    'memory'  - Show memory info")
    print("=" * 60)
    print(f"  Logs: {CONFIG.workdir / 'agent.log'}")
    print("=" * 60)
    print()


def run_web_server(host: str = None, port: int = None):
    """启动 Web 服务器"""
    from api import run_server
    run_server(
        host=host or CONFIG.server_host,
        port=port or CONFIG.server_port
    )


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='PyCode Agent - AI Coding Assistant')
    parser.add_argument('--web', action='store_true', help='Start web server mode')
    parser.add_argument('--port', type=int, default=None, help='Web server port (default: 8000)')
    parser.add_argument('--host', type=str, default=None, help='Web server host (default: 0.0.0.0)')
    args = parser.parse_args()

    # 初始化配置
    try:
        init_config(Path.cwd())
    except ValueError as e:
        print(f"\n[Error] {e}")
        sys.exit(1)

    # Web 模式
    if args.web:
        run_web_server(args.host, args.port)
        return

    print_banner()

    # 初始化历史记录
    history = [{"role": "system", "content": get_system_prompt()}]

    # 启动钩子: 尝试加载上次对话
    last_session = MEMORY.load_last_session()
    if last_session:
        print(f"[Memory] Found previous session with {len(last_session)} messages")
        try:
            load_choice = input("Load previous session? [y/N]: ").strip().lower()
            if load_choice in ("y", "yes"):
                history = [{"role": "system", "content": get_system_prompt()}] + last_session
                print(f"[Memory] Loaded {len(last_session)} messages from previous session")
            else:
                print("[Memory] Starting fresh session")
        except (EOFError, KeyboardInterrupt):
            print("\n[Memory] Starting fresh session")
    else:
        print("[Memory] No previous session found, starting fresh")
    print()

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            # 内置命令
            cmd = user_input.lower()

            if cmd in ("exit", "quit", "q"):
                print("Goodbye!")
                break

            if cmd == "clear":
                history = [{"role": "system", "content": get_system_prompt()}]
                MEMORY.clear_session()
                print("History cleared.")
                continue

            if cmd == "status":
                print(f"History messages: {len(history)}")
                print(f"Current todos:\n{TODO.render()}")
                print(f"Token usage: {TOKEN_USAGE.summary()}")
                continue

            if cmd == "skills":
                print(f"Available skills:\n{SKILLS.get_descriptions()}")
                continue

            if cmd == "tokens":
                print(TOKEN_USAGE.summary())
                continue

            if cmd == "load":
                last_session = MEMORY.load_last_session()
                if last_session:
                    history = [{"role": "system", "content": get_system_prompt()}] + last_session
                    print(f"[Memory] Loaded {len(last_session)} messages")
                else:
                    print("[Memory] No session to load")
                continue

            if cmd == "save":
                if MEMORY.save_session(history):
                    print(f"[Memory] Session saved to {MEMORY.session_file}")
                else:
                    print("[Memory] Failed to save session")
                continue

            if cmd == "memory":
                print(f"[Memory] Directory: {MEMORY.memory_dir}")
                print(f"[Memory] {MEMORY.get_session_info()}")
                print(f"[Memory] Current session: {len(history)} messages")
                continue

            # 添加用户消息
            history.append({"role": "user", "content": user_input})
            logger.info(f"User input: {user_input[:100]}...")

            try:
                history = agent_loop(history)
            except KeyboardInterrupt:
                print("\n[Interrupted]")
                logger.warning("Agent loop interrupted by user")
            except Exception as e:
                logger.error(f"Agent loop error: {e}", exc_info=True)
                print(f"Error: {e}")

            print()

    finally:
        # 退出钩子: 保存当前对话
        if len(history) > 1:
            print("\n[Memory] Saving session...")
            if MEMORY.save_session(history):
                print(f"[Memory] Session saved to {MEMORY.session_file}")
            else:
                print("[Memory] Failed to save session")

            # 打印 token 使用统计
            print(f"\n{TOKEN_USAGE.summary()}")


if __name__ == "__main__":
    main()