# core/command_executor.py
from PyQt5.QtCore import QObject, QThread, pyqtSignal


class CommandExecutor(QObject):
    """命令执行器 - 管理命令的执行和线程生命周期"""

    command_started = pyqtSignal(str)  # command_name
    command_finished = pyqtSignal(str)  # command_name
    log_signal = pyqtSignal(str, str)  # level, message

    def __init__(self, command, command_name):
        super().__init__()
        self.command = command
        self.command_name = command_name
        self.thread = None

    def execute(self):
        """执行命令"""
        self.command_started.emit(self.command_name)

        # 创建执行线程
        self.thread = CommandThread(self.command)
        self.thread.finished.connect(
            lambda: self._on_command_finished()
        )

        # 连接错误信号
        if hasattr(self.command, 'error_occurred'):
            self.command.error_occurred.connect(
                lambda msg: self.log_signal.emit("错误", msg)
            )

        self.thread.start()

    def _on_command_finished(self):
        """命令完成回调"""
        self.command_finished.emit(self.command_name)
        self.thread.deleteLater()
        self.thread = None


class CommandThread(QThread):
    """命令执行线程"""

    def __init__(self, command_runner):
        super().__init__()
        self.command_runner = command_runner

    def run(self):
        self.command_runner.run_with_error_handling(
            self.command_runner.__class__.__name__
        )