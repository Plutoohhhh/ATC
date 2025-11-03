# utils/logger.py
import os
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal


class UnifiedLogger(QObject):
    """统一的日志记录器，支持UI显示和文件保存"""

    # 信号用于UI更新
    log_signal = pyqtSignal(str, str)  # level, message

    def __init__(self, log_to_file=True, log_file_path=None):
        super().__init__()
        self.log_to_file = log_to_file
        self.log_file_path = log_file_path or self.get_default_log_path()
        self.log_file = None

        if self.log_to_file:
            self.setup_log_file()

    def get_default_log_path(self):
        """获取默认日志文件路径"""
        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return desktop / f"atc_log_{timestamp}.log"

    def setup_log_file(self):
        """设置日志文件"""
        try:
            self.log_file = open(self.log_file_path, 'a', encoding='utf-8')
            self.log("系统", f"日志文件: {self.log_file_path}")
        except Exception as e:
            print(f"无法创建日志文件: {e}")

    def log(self, level, message):
        """统一的日志记录方法"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}"

        # 输出到控制台
        print(formatted_message)

        # 发送到UI
        self.log_signal.emit(level, message)

        # 写入文件
        if self.log_to_file and self.log_file:
            self.log_file.write(formatted_message + "\n")
            self.log_file.flush()

    def close(self):
        """关闭日志记录器"""
        if self.log_file:
            self.log_file.close()