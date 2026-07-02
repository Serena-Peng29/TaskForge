from spark.config import logger
import re

class SecurityChecker:
    """命令安全检查器"""

    # 危险命令黑名单（更全面）
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/",          # rm -rf /
        r"rm\s+-rf\s+\*",         # rm -rf *
        r"rm\s+-rf\s+\.\.",       # rm -rf ..
        r">\s*/dev/sd",           # 写入磁盘设备
        r"mkfs\.",                # 格式化
        r"dd\s+if=.*of=/dev",     # dd 写入设备
        r":(){ :|:& };:",         # Fork bomb
        r"shutdown",
        r"reboot",
        r"halt",
        r"poweroff",
        r"init\s+[06]",
        r"systemctl\s+(halt|poweroff|reboot)",
        r"chmod\s+-R\s+777\s+/",  # 危险权限修改
        r"chown\s+-R.*\s+/",      # 危险所有权修改
        r"curl.*\|\s*(ba)?sh",    # 管道执行远程脚本
        r"wget.*\|\s*(ba)?sh",
        r"eval\s+\$\(",           # 危险的 eval
    ]

    # 需要确认的命令（警告级别）
    WARNING_PATTERNS = [
        r"sudo\s+",
        r"su\s+",
        r"rm\s+-rf",
        r"rm\s+-r",
        r">\s+/etc/",
        r"pip\s+install",
        r"npm\s+install\s+-g",
    ]

    def __init__(self):
        self.dangerous_regex = [re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATTERNS]
        self.warning_regex = [re.compile(p, re.IGNORECASE) for p in self.WARNING_PATTERNS]

    def check_command(self, cmd: str) -> tuple[bool, str]:
        """
        检查命令安全性
        Returns: (is_safe, message)
        """
        # 检查危险命令
        for pattern in self.dangerous_regex:
            if pattern.search(cmd):
                return False, f"Blocked dangerous command matching: {pattern.pattern}"

        # 检查警告级别命令
        warnings = []
        for pattern in self.warning_regex:
            if pattern.search(cmd):
                warnings.append(pattern.pattern)

        if warnings:
            logger.warning(f"Command contains potentially risky patterns: {warnings}")

        return True, ""

SECURITY = SecurityChecker()