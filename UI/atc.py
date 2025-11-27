# atc.py (重构版本)
import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTextEdit, QScrollArea,
                             QSizePolicy, QFrame, QToolButton, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QTextCursor, QColor

from commands.scout_insight_command import ScoutInsightCommand, ScoutConfigManager
from commands.scout_validate_command import ScoutValidateCommand
from utils.logger import UnifiedLogger
from commands.nanocom_command import NanocomCommand
from commands.reboot_log_command import RebootLogCommand


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

        # 创建日志目录
        self.session_path = self.create_session_directory()
        # 创建统一的日志记录器
        self.logger = UnifiedLogger(session_path=self.session_path, log_to_file=True)
        self.logger.log_signal.connect(self.add_log)

        self.initUI()
        self.setup_commands()

    def create_session_directory(self):
        """创建会话目录"""
        desktop = Path.home() / "Desktop"
        session_dir = desktop / "ATC_Logs" / datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir.mkdir(parents=True, exist_ok=True)
        return str(session_dir)

    def setup_commands(self):
        """设置可用的命令"""
        self.commands = {
            "nanocom": NanocomCommand(self.logger),
            "reboot_log": RebootLogCommand(self.logger),
            "scout_validate": ScoutValidateCommand(self.logger),
            "scout_insight": ScoutInsightCommand(self.logger),  # 新增
            # 后续添加新命令只需在这里注册
        }

        # 为每个命令设置会话路径（如果命令类支持）
        for command_name, command in self.commands.items():
            if hasattr(command, 'set_session_path'):
                command.set_session_path(self.session_path)

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
            ("开始记录", "start_logging", self.start_logging),
            ("停止记录", "stop_logging", self.stop_logging),
            ("清空日志", "clear_log", self.clear_log),
            ("执行 Nanocom", "nanocom", lambda: self.execute_command("nanocom")),
            ("执行 reboot_log", "reboot_log", lambda: self.execute_command("reboot_log")),
            ("执行 scout_validate", "scout_validate", lambda: self.execute_command("scout_validate")),
            # 新增 Scout Insight 按钮，带设置图标
            ("Scout Insight", "scout_insight", self.execute_scout_insight),
            # 添加新命令按钮只需在这里添加一行
        ]

        self.buttons = {}
        for text, command_name, slot in buttons_info:
            # if command_name == "scout_insight":
                # 为 Scout Insight 创建带设置按钮的布局
            scout_layout = QHBoxLayout()
            scout_layout.setSpacing(5)

            # 主按钮
            main_button = QPushButton(text)
            main_button.setMinimumHeight(40)
            main_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            main_button.clicked.connect(slot)
            scout_layout.addWidget(main_button)

            # 设置按钮（齿轮图标）
            settings_button = QToolButton()
            settings_button.setText("⚙")  # 使用文本符号作为齿轮图标
            settings_button.setToolTip("配置 Scout Insight 参数")
            settings_button.setFixedSize(30, 40)
            settings_button.clicked.connect(self.configure_scout_insight)
            scout_layout.addWidget(settings_button)

            left_layout.addLayout(scout_layout)
            self.buttons[command_name] = main_button
            # else:
            #     button = QPushButton(text)
            #     button.setMinimumHeight(40)
            #     button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            #     button.clicked.connect(slot)
            #     left_layout.addWidget(button)
            #     self.buttons[command_name] = button

        # 添加弹性空间
        left_layout.addStretch(1)
        main_layout.addWidget(self.left_widget)

    def execute_scout_insight(self):
        """执行 Scout Insight 命令"""
        # 检查是否已配置
        scout_command = self.commands["scout_insight"]
        if not scout_command.config:
            QMessageBox.warning(self, "配置错误", "请先配置 Scout Insight 参数")
            return

        self.execute_command("scout_insight")

    def configure_scout_insight(self):
        """配置 Scout Insight 参数（在主线程中执行）"""
        if "scout_insight" in self.commands:
            # 使用配置管理器在主线程中显示对话框
            config_manager = ScoutConfigManager()
            config_manager.config_received.connect(self._on_scout_config_received)
            config_manager.show_dialog()
        else:
            self.logger.log("错误", "Scout Insight 命令未找到")

    def _on_scout_config_received(self, config):
        """Scout配置接收回调"""
        scout_command = self.commands["scout_insight"]
        scout_command.set_config(config)
        self.logger.log("系统", "Scout Insight 配置已更新")
        self.logger.log("程序输出", f"新配置: {config}")

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
                color: #ffffff;
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
            "错误": "#ff6b6b",    # 更亮的红色
            "警告": "#ffa94d",    # 更亮的橙色
            "信息": "#51cf66",    # 更亮的绿色
            "系统": "#339af0",    # 更亮的蓝色
            "程序输出": "#ffd43b", # 更亮的黄色
            "命令输入": "#ff8787", # 更亮的粉红色
            "系统输出": "#74c0fc", # 更亮的浅蓝色
            "自动": "#da77f2"     # 更亮的紫色
        }

        color = color_map.get(level, "#ffffff")

        # 添加带颜色的文本
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)

        # 插入带格式的文本
        self.log_text.setTextColor(QColor("#adb5bd"))  # 灰色时间戳
        self.log_text.insertPlainText(f"[{timestamp}] ")

        self.log_text.setTextColor(QColor("#868e96"))  # 灰色括号
        self.log_text.insertPlainText("[")

        self.log_text.setTextColor(self.get_color(color))  # 彩色级别
        self.log_text.insertPlainText(level)

        self.log_text.setTextColor(QColor("#868e96"))  # 灰色括号
        self.log_text.insertPlainText("] ")

        self.log_text.setTextColor(QColor("#ffffff"))  # 白色消息
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
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #4a4a4f;
            border: 1px solid #666;
        }
        QPushButton:pressed {
            background-color: #007acc;
            color: #ffffff;
        }
        QPushButton:disabled {
            background-color: #2d2d30;
            color: #666666;
            border: 1px solid #444;
        }
        QToolButton {
            background-color: #3e3e42;
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 5px;
            font-size: 14px;
        }
        QToolButton:hover {
            background-color: #4a4a4f;
            border: 1px solid #666;
        }
        QToolButton:pressed {
            background-color: #007acc;
            color: #ffffff;
        }
        QWidget {
            background-color: #2d2d30;
            color: #ffffff;
        }
        QLabel {
            color: #ffffff;
            background-color: transparent;
        }
        QLineEdit {
            background-color: #3e3e42;
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 5px;
            selection-background-color: #007acc;
        }
        QLineEdit:focus {
            border: 1px solid #007acc;
        }
        QDialog {
            background-color: #2d2d30;
            color: #ffffff;
        }
        QMessageBox {
            background-color: #2d2d30;
            color: #ffffff;
        }
        QMessageBox QLabel {
            color: #ffffff;
        }
    """)

    window = LogWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
