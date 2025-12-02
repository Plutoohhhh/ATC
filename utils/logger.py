from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal


class TerminalLogger:
    """终端输入输出记录器"""

    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.log_file = None
        self.setup_terminal_log()

    def setup_terminal_log(self):
        """设置终端日志文件"""
        try:
            self.log_file = open(self.log_file_path, 'a', encoding='utf-8')
            self.write_terminal_log("TERMINAL", "终端日志开始记录")
        except Exception as e:
            print(f"无法创建终端日志文件: {e}")

    def write_terminal_log(self, direction, data):
        """写入终端日志"""
        if self.log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            # 清理数据中的控制字符
            cleaned_data = self.clean_control_chars(data)
            log_entry = f"[{timestamp}] [{direction}] {cleaned_data}\n"
            self.log_file.write(log_entry)
            self.log_file.flush()

    def clean_control_chars(self, text):
        """清理控制字符，保留可打印字符"""
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')
        # 保留换行符和制表符，移除其他控制字符
        cleaned = ''.join(
            char for char in text if char == '\n' or char == '\t' or (ord(char) >= 32 and ord(char) != 127))
        return cleaned

    def log_send(self, data):
        """记录发送的数据"""
        self.write_terminal_log("SEND", data)

    def log_receive(self, data):
        """记录接收的数据"""
        self.write_terminal_log("RECV", data)

    def log_expect(self, pattern):
        """记录期望的模式"""
        self.write_terminal_log("EXPECT", f"等待模式: {pattern}")

    def log_timeout(self):
        """记录超时"""
        self.write_terminal_log("TIMEOUT", "操作超时")

    def close(self):
        """关闭终端日志"""
        if self.log_file:
            self.write_terminal_log("TERMINAL", "终端日志结束记录")
            self.log_file.close()


class UnifiedLogger(QObject):
    """统一的日志记录器，支持UI显示、文件保存和命令记录"""

    # 信号用于UI更新
    log_signal = pyqtSignal(str, str)  # level, message

    def __init__(self, session_path=None, log_to_file=True):
        super().__init__()
        self.log_to_file = log_to_file
        self.session_path = session_path

        # 延迟初始化日志文件路径，直到session_path可用
        self.log_file_path = None
        self.terminal_log_path = None

        self.log_file = None
        self.terminal_logger = None

        # 如果提供了session_path，立即设置日志文件
        if self.session_path and self.log_to_file:
            self.setup_log_files()

    def set_session_path(self, session_path):
        """设置会话路径并初始化日志文件"""
        self.session_path = session_path
        if self.log_to_file and not self.log_file:
            self.setup_log_files()

    def setup_log_files(self):
        """设置日志文件和终端日志文件"""
        if not self.session_path:
            raise ValueError("Session path must be set before setting up log files")

        try:
            # 确保会话目录存在
            Path(self.session_path).mkdir(parents=True, exist_ok=True)

            # 设置日志文件路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file_path = Path(self.session_path) / f"atc_log_{timestamp}.log"
            self.terminal_log_path = Path(self.session_path) / f"atc_terminal_{timestamp}.log"

            # 设置普通日志文件
            self.log_file = open(self.log_file_path, 'a', encoding='utf-8')
            self.log("系统", f"日志文件: {self.log_file_path}")

            # 设置终端日志记录器
            self.terminal_logger = TerminalLogger(self.terminal_log_path)
            self.log("系统", f"终端日志文件: {self.terminal_log_path}")

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

    def get_terminal_logger(self):
        """获取终端日志记录器"""
        return self.terminal_logger

    def close(self):
        """关闭日志记录器"""
        if self.log_file:
            self.log_file.close()

        if self.terminal_logger:
            self.terminal_logger.close()