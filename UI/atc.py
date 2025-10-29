import sys
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTextEdit, QScrollArea,
                             QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QColor


class LogWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle('日志显示界面')
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

        # 设置布局比例（左侧1:右侧4）
        main_layout.setStretchFactor(self.left_widget, 1)
        main_layout.setStretchFactor(self.right_widget, 4)

    def create_left_panel(self, main_layout):
        # 左侧部件
        self.left_widget = QWidget()
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setSpacing(10)
        left_layout.setAlignment(Qt.AlignTop)

        # 创建按钮
        buttons_info = [
            ("开始记录", self.start_logging),
            ("停止记录", self.stop_logging),
            ("清空日志", self.clear_log),
            ("添加测试日志", self.add_test_log),
            ("信息日志", lambda: self.add_log("信息", "这是一条信息日志")),
            ("警告日志", lambda: self.add_log("警告", "这是一条警告日志")),
            ("错误日志", lambda: self.add_log("错误", "这是一条错误日志"))
        ]

        self.buttons = []
        for text, slot in buttons_info:
            button = QPushButton(text)
            button.setMinimumHeight(40)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(slot)
            left_layout.addWidget(button)
            self.buttons.append(button)

        # 添加弹性空间
        left_layout.addStretch(1)

        main_layout.addWidget(self.left_widget)

    def create_right_panel(self, main_layout):
        # 右侧部件
        self.right_widget = QWidget()
        right_layout = QVBoxLayout(self.right_widget)

        # 创建日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)

        # 设置字体
        font = QFont("Consolas", 10)
        self.log_text.setFont(font)

        # 设置样式
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
            self.log_timer.start(1000)  # 每秒添加一条日志
            self.add_log("系统", "开始自动记录日志")

    def stop_logging(self):
        if self.logging_active:
            self.logging_active = False
            self.log_timer.stop()
            self.add_log("系统", "停止自动记录日志")

    def clear_log(self):
        self.log_text.clear()
        self.log_count = 0

    def add_test_log(self):
        self.add_log("测试", f"这是第 {self.log_count} 条测试日志")
        self.log_count += 1

    def add_auto_log(self):
        self.add_log("自动", f"自动生成的日志 #{self.log_count}")
        self.log_count += 1

    def add_log(self, level, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 根据日志级别设置颜色
        if level == "错误":
            color = "#f44747"
        elif level == "警告":
            color = "#ff8800"
        elif level == "信息":
            color = "#4ec9b0"
        elif level == "系统":
            color = "#569cd6"
        else:
            color = "#d4d4d4"

        # 格式化日志信息
        log_entry = f"[{timestamp}] [{level}] {message}"

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
