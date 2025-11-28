# utils/session_manager.py
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable


class SessionManager:
    """会话管理器 - 统一处理目录创建、日志记录等重复功能"""

    def __init__(self, base_name: str = "ATC_Logs", logger=None):
        self.base_name = base_name
        self.logger = logger
        self.session_path = None
        self.terminal_log_file = None
        self.raw_terminal_logger = None

    def set_logger(self, logger):
        """设置日志记录器"""
        self.logger = logger

    def log(self, level: str, message: str):
        """统一的日志记录方法"""
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")

    def create_session_directory(self, session_type: str = "session") -> str:
        """创建标准化的会话目录结构

        Args:
            session_type: 会话类型，如 "nanocom", "scout", "reboot" 等

        Returns:
            创建的会话路径
        """
        try:
            desktop_path = os.path.expanduser("~/Desktop")

            # 创建日期文件夹
            date_str = datetime.now().strftime("%Y-%m-%d")
            date_folder = os.path.join(desktop_path, f"{self.base_name}_{date_str}")
            os.makedirs(date_folder, exist_ok=True)

            # 创建类型化的会话文件夹
            session_time = datetime.now().strftime("%H%M%S")
            self.session_path = os.path.join(
                date_folder,
                f"{session_type}_session_{session_time}"
            )
            os.makedirs(self.session_path, exist_ok=True)

            self.log("系统", f"{session_type}会话目录已创建: {self.session_path}")
            return self.session_path

        except Exception as e:
            self.log("错误", f"创建{session_type}会话目录失败: {e}")
            return None

    def setup_terminal_logging(self, log_filename: str = "terminal.log") -> bool:
        """设置终端日志记录

        Args:
            log_filename: 终端日志文件名

        Returns:
            设置是否成功
        """
        if not self.session_path:
            self.log("错误", "请先创建会话目录")
            return False

        try:
            # 创建终端日志文件路径
            log_file_path = os.path.join(self.session_path, log_filename)

            # 打开终端日志文件
            self.terminal_log_file = open(log_file_path, 'wb')

            self.log("系统", f"终端日志将保存到: {log_file_path}")
            return True

        except Exception as e:
            self.log("错误", f"设置终端日志失败: {e}")
            return False

    def create_raw_terminal_logger(self, event_handlers: Optional[dict] = None):
        """创建原始终端日志记录器

        Args:
            event_handlers: 事件处理器字典，格式为 {pattern: callback}

        Returns:
            RawTerminalLogger 实例
        """
        if not self.terminal_log_file:
            self.log("错误", "请先设置终端日志")
            return None

        class RawTerminalLogger:
            def __init__(self, raw_log_file, ui_logger, event_handlers=None):
                self.raw_log_file = raw_log_file
                self.ui_logger = ui_logger
                self.event_handlers = event_handlers or {}
                self.buffer = b''

            def write(self, data):
                # 如果是字符串，转换为字节
                if isinstance(data, str):
                    data_bytes = data.encode('utf-8', errors='replace')
                else:
                    data_bytes = data

                # 直接写入原始字节到文件
                self.raw_log_file.write(data_bytes)
                self.raw_log_file.flush()

                # 同时更新缓冲区用于UI显示和事件处理
                self.buffer += data_bytes
                self._process_buffer_for_ui()

            def _process_buffer_for_ui(self):
                """处理缓冲区数据用于UI显示和事件处理"""
                try:
                    # 尝试解码为UTF-8
                    decoded = self.buffer.decode('utf-8', errors='ignore')

                    # 按行分割，处理完整的行
                    lines = decoded.split('\n')

                    # 如果最后一行不完整，保留在缓冲区中
                    if not decoded.endswith('\n'):
                        self.buffer = lines[-1].encode('utf-8')
                        lines = lines[:-1]
                    else:
                        self.buffer = b''

                    # 处理完整的行
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        # 调用事件处理器
                        self._handle_events(line)

                        # 默认UI显示
                        self.ui_logger.log("终端输出", line)

                except Exception as e:
                    # 如果解码失败，清空缓冲区
                    self.buffer = b''
                    self.ui_logger.log("错误", f"终端日志处理异常: {e}")

            def _handle_events(self, line: str):
                """处理特定事件"""
                for pattern, callback in self.event_handlers.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        try:
                            callback(line)
                        except Exception as e:
                            self.ui_logger.log("错误", f"事件处理回调异常: {e}")

            def flush(self):
                self.raw_log_file.flush()

            def log_command(self, command: str):
                """专门记录命令"""
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # 在UI中显示命令
                self.ui_logger.log("命令输入", f"执行命令: {command}")
                # 同时确保命令被写入日志文件
                command_bytes = f"\n[{timestamp}] [COMMAND] 执行命令: {command}\n".encode('utf-8')
                self.raw_log_file.write(command_bytes)
                self.raw_log_file.flush()

        return RawTerminalLogger(
            self.terminal_log_file,
            self.logger,
            event_handlers
        )

    def get_session_path(self) -> Optional[str]:
        """获取会话路径"""
        return self.session_path

    def setup_complete_session(self, session_type: str, log_filename: str = "terminal.log",
                               event_handlers: Optional[dict] = None) -> bool:
        """完整设置会话（一步到位）

        Args:
            session_type: 会话类型
            log_filename: 日志文件名
            event_handlers: 事件处理器

        Returns:
            设置是否成功
        """
        if not self.create_session_directory(session_type):
            return False

        if not self.setup_terminal_logging(log_filename):
            return False

        self.raw_terminal_logger = self.create_raw_terminal_logger(event_handlers)
        return self.raw_terminal_logger is not None

    def cleanup(self):
        """清理资源"""
        if self.terminal_log_file:
            self.terminal_log_file.close()
            self.terminal_log_file = None

        self.raw_terminal_logger = None

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()


# 预定义的事件处理器
class EventHandlers:
    """常用事件处理器"""

    @staticmethod
    def create_auth_handler(logger):
        def handler(line):
            if 'authenticating' in line.lower():
                logger.log("系统输出", f"认证状态: {line}")

        return handler

    @staticmethod
    def create_login_handler(logger):
        def handler(line):
            if 'login' in line.lower() or 'username' in line.lower():
                logger.log("系统输出", "需要登录")
            elif 'password' in line.lower():
                logger.log("系统输出", "需要密码")

        return handler

    @staticmethod
    def create_prompt_handler(logger, prompt_pattern):
        def handler(line):
            if re.search(prompt_pattern, line):
                logger.log("系统输出", "进入目标系统")

        return handler

    @staticmethod
    def create_completion_handler(logger):
        def handler(line):
            if 'saved in' in line or 'done' in line.lower():
                logger.log("系统输出", f"操作完成: {line}")
            elif 'error' in line.lower() or 'failed' in line.lower():
                logger.log("错误", f"错误信息: {line}")

        return handler