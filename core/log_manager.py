# core/log_manager.py
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from datetime import datetime


class LogManager(QObject):
    """日志管理器 - 处理日志相关的业务逻辑"""

    auto_log_signal = pyqtSignal(str, str)  # level, message

    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.logging_active = False
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self._generate_auto_log)
        self.log_count = 0

    def start_logging(self):
        """开始自动记录"""
        if not self.logging_active:
            self.logging_active = True
            self.log_timer.start(1000)
            self.logger.log("系统", "开始自动记录日志")
            return True
        return False

    def stop_logging(self):
        """停止自动记录"""
        if self.logging_active:
            self.logging_active = False
            self.log_timer.stop()
            self.logger.log("系统", "停止自动记录日志")
            return True
        return False

    def clear_logs(self):
        """清空日志计数"""
        self.log_count = 0
        return True

    def _generate_auto_log(self):
        """生成自动日志"""
        self.auto_log_signal.emit("自动", f"自动生成的日志 #{self.log_count}")
        self.log_count += 1