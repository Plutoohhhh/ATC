# atc.py (重构版本)
import sys
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTextEdit, QScrollArea,
                             QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QTextCursor, QColor

from commands.check_diags_command import CheckDiagsCommand
from utils.logger import UnifiedLogger
from commands.nanocom_command import NanocomCommand
from commands.collectlog_command import CollectlogCommand


class CommandThread(QThread):
    """命令执行线程"""

    def __init__(self, command_runner):
        super().__init__()
        self.command_runner = command_runner

    def run(self):
        self.command_runner.run_with_error_handling(
            self.command_runner.__class__.__name__
        )


class LogWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 创建统一的日志记录器
        self.logger = UnifiedLogger(log_to_file=True)
        self.logger.log_signal.connect(self.add_log)

        self.initUI()
        self.setup_commands()

    def setup_commands(self):
        default_spartan_name = "YourSpartanModemName"  # 修改为实际的名称
        """设置可用的命令"""
        self.commands = {
            "nanocom": NanocomCommand(self.logger),
            "collectlog": CollectlogCommand(self.logger),
            "check_diags": CheckDiagsCommand(self.logger, self),
            # 后续添加新命令只需在这里注册
        }

    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle('自动化测试控制台')
        self.setGeometry(100, 100, 1000, 600)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主水平布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 创建左侧按钮列
        self.create_left_panel(main_layout)

        # 创建右侧日志显示区域
        self.create_right_panel(main_layout)

        # 设置布局比例
        main_layout.setStretchFactor(self.left_widget, 1)
        main_layout.setStretchFactor(self.right_widget, 4)

    def create_left_panel(self, main_layout):
        # 左侧部件
        self.left_widget = QWidget()
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setSpacing(10)
        left_layout.setAlignment(Qt.AlignTop)

        # 创建命令按钮
        buttons_info = [
            ("开始记录", self.start_logging),
            ("停止记录", self.stop_logging),
            ("清空日志", self.clear_log),
            ("执行 Nanocom", lambda: self.execute_command("nanocom")),
            ("执行 Collectlog", lambda: self.execute_command("collectlog")),
            ("检测 Diags", lambda: self.execute_command("check_diags")),
            # 添加新命令按钮只需在这里添加一行
        ]

        self.buttons = {}
        for text, slot in buttons_info:
            button = QPushButton(text)
            button.setMinimumHeight(40)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(slot)
            left_layout.addWidget(button)
            # 存储按钮引用以便后续操作
            if "执行" in text:
                command_name = text.replace("执行 ", "").lower()
                self.buttons[command_name] = button

        # 添加弹性空间
        left_layout.addStretch(1)
        main_layout.addWidget(self.left_widget)

    def execute_command(self, command_name):
        """执行指定命令"""
        if command_name in self.commands:
            # 禁用按钮防止重复点击
            self.buttons[command_name].setEnabled(False)

            # 在新线程中执行命令
            self.command_thread = CommandThread(self.commands[command_name])
            self.command_thread.finished.connect(
                lambda: self.buttons[command_name].setEnabled(True)
            )
            self.command_thread.start()
        else:
            self.logger.log("错误", f"未知命令: {command_name}")

    def create_right_panel(self, main_layout):
        # 右侧部件
        self.right_widget = QWidget()
        right_layout = QVBoxLayout(self.right_widget)

        # 创建日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)

        # 设置字体和样式
        font = QFont("Consolas", 10)
        self.log_text.setFont(font)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 10px;
            }
        """)

        right_layout.addWidget(self.log_text)
        main_layout.addWidget(self.right_widget)

        # 日志记录状态
        self.logging_active = False
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.add_auto_log)
        self.log_count = 0

    def start_logging(self):
        if not self.logging_active:
            self.logging_active = True
            self.log_timer.start(1000)
            self.logger.log("系统", "开始自动记录日志")

    def stop_logging(self):
        if self.logging_active:
            self.logging_active = False
            self.log_timer.stop()
            self.logger.log("系统", "停止自动记录日志")

    def clear_log(self):
        self.log_text.clear()
        self.log_count = 0

    def add_auto_log(self):
        self.logger.log("自动", f"自动生成的日志 #{self.log_count}")
        self.log_count += 1

    def add_log(self, level, message):
        """添加日志到UI显示"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 根据日志级别设置颜色
        color_map = {
            "错误": "#f44747",
            "警告": "#ff8800",
            "信息": "#4ec9b0",
            "系统": "#569cd6",
            "程序输出": "#dcdcaa",
            "命令输入": "#ce9178",
            "系统输出": "#9cdcfe",
            "自动": "#c586c0"
        }

        color = color_map.get(level, "#d4d4d4")

        # 添加带颜色的文本
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)

        # 插入带格式的文本
        self.log_text.setTextColor(Qt.white)
        self.log_text.insertPlainText(f"[{timestamp}] ")

        self.log_text.setTextColor(Qt.gray)
        self.log_text.insertPlainText("[")

        self.log_text.setTextColor(self.get_color(color))
        self.log_text.insertPlainText(level)

        self.log_text.setTextColor(Qt.gray)
        self.log_text.insertPlainText("] ")

        self.log_text.setTextColor(Qt.white)
        self.log_text.insertPlainText(f"{message}\n")

        # 自动滚动到底部
        self.log_text.ensureCursorVisible()

    def get_color(self, hex_color):
        """将十六进制颜色转换为QColor"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return QColor(r, g, b)

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.logger.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)

    # 设置应用程序样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2d2d30;
        }
        QPushButton {
            background-color: #3e3e42;
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 5px;
            padding: 8px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #4a4a4f;
        }
        QPushButton:pressed {
            background-color: #007acc;
        }
        QWidget {
            background-color: #2d2d30;
        }
    """)

    window = LogWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()