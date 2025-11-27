# core/command_manager.py
from PyQt5.QtCore import QObject, pyqtSignal
from commands.nanocom_command import NanocomCommand
from commands.reboot_log_command import RebootLogCommand
from commands.scout_validate_command import ScoutValidateCommand
from commands.scout_insight_command import ScoutInsightCommand, ScoutConfigManager


class CommandManager(QObject):
    """命令管理器 - 处理所有命令相关的业务逻辑"""

    # 信号定义
    log_signal = pyqtSignal(str, str)  # level, message
    command_started = pyqtSignal(str)  # command_name
    command_finished = pyqtSignal(str)  # command_name

    def __init__(self, logger, session_path):
        super().__init__()
        self.logger = logger
        self.session_path = session_path
        self.commands = {}
        self.setup_commands()

    def setup_commands(self):
        """初始化所有命令"""
        self.commands = {
            "nanocom": NanocomCommand(self.logger),
            "reboot_log": RebootLogCommand(self.logger),
            "scout_validate": ScoutValidateCommand(self.logger),
            "scout_insight": ScoutInsightCommand(self.logger),
        }

        # 设置会话路径
        for command_name, command in self.commands.items():
            if hasattr(command, 'set_session_path'):
                command.set_session_path(self.session_path)

    def get_command(self, command_name):
        """获取命令实例"""
        return self.commands.get(command_name)

    def configure_command(self, command_name, parent=None):
        """配置指定命令"""
        command = self.get_command(command_name)
        if not command:
            self.log_signal.emit("错误", f"未知命令: {command_name}")
            return False

        if command_name == "scout_insight":
            return self._configure_scout_insight(parent)
        elif command_name == "nanocom":
            return self._configure_nanocom(parent)
        elif command_name == "reboot_log":
            return self._configure_reboot_log(parent)
        elif command_name == "scout_validate":
            return self._configure_scout_validate(parent)
        else:
            self.log_signal.emit("警告", f"命令 {command_name} 暂无配置选项")
            return False

    def _configure_scout_insight(self, parent):
        """配置 Scout Insight"""
        config_manager = ScoutConfigManager()
        config_manager.config_received.connect(self._on_scout_config_received)
        config_manager.show_dialog()
        return True

    def _configure_nanocom(self, parent):
        """配置 Nanocom"""
        from PyQt5.QtWidgets import QInputDialog
        baud_rate, ok = QInputDialog.getInt(parent, "配置 Nanocom", "请输入波特率:", 9600, 1200, 115200, 100)
        if ok and hasattr(self.commands["nanocom"], 'set_baud_rate'):
            self.commands["nanocom"].set_baud_rate(baud_rate)
            self.log_signal.emit("程序输出", f"Nanocom 波特率设置为: {baud_rate}")
            return True
        return False

    def _configure_reboot_log(self, parent):
        """配置 Reboot Log"""
        from PyQt5.QtWidgets import QInputDialog
        log_level, ok = QInputDialog.getItem(
            parent, "配置 Reboot Log", "选择日志级别:",
            ["DEBUG", "INFO", "WARNING", "ERROR"], 1, False
        )
        if ok and hasattr(self.commands["reboot_log"], 'set_log_level'):
            self.commands["reboot_log"].set_log_level(log_level)
            self.log_signal.emit("程序输出", f"Reboot Log 日志级别设置为: {log_level}")
            return True
        return False

    def _configure_scout_validate(self, parent):
        """配置 Scout Validate"""
        from PyQt5.QtWidgets import QInputDialog
        timeout, ok = QInputDialog.getInt(
            parent, "配置 Scout Validate", "设置超时时间(秒):", 30, 5, 300, 5
        )
        if ok and hasattr(self.commands["scout_validate"], 'set_timeout'):
            self.commands["scout_validate"].set_timeout(timeout)
            self.log_signal.emit("程序输出", f"Scout Validate 超时时间设置为: {timeout} 秒")
            return True
        return False

    def _on_scout_config_received(self, config):
        """Scout配置接收回调"""
        scout_command = self.commands["scout_insight"]
        scout_command.set_config(config)
        self.log_signal.emit("系统", "Scout Insight 配置已更新")
        self.log_signal.emit("程序输出", f"新配置: {config}")