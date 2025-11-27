# ui/components/log_display.py
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor, QColor
from datetime import datetime


class LogDisplay(QTextEdit):
    """日志显示组件"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.NoWrap)

        # 设置字体和样式
        font = QFont("Consolas", 10)
        self.setFont(font)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 10px;
            }
        """)

    def add_log(self, level, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 根据日志级别设置颜色
        color_map = {
            "错误": "#ff6b6b",
            "警告": "#ffa94d",
            "信息": "#51cf66",
            "系统": "#339af0",
            "程序输出": "#ffd43b",
            "命令输入": "#ff8787",
            "系统输出": "#74c0fc",
            "自动": "#da77f2"
        }

        color = color_map.get(level, "#ffffff")

        # 添加带颜色的文本
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        # 插入带格式的文本
        self.setTextColor(QColor("#adb5bd"))  # 灰色时间戳
        self.insertPlainText(f"[{timestamp}] ")

        self.setTextColor(QColor("#868e96"))  # 灰色括号
        self.insertPlainText("[")

        self.setTextColor(self._hex_to_color(color))  # 彩色级别
        self.insertPlainText(level)

        self.setTextColor(QColor("#868e96"))  # 灰色括号
        self.insertPlainText("] ")

        self.setTextColor(QColor("#ffffff"))  # 白色消息
        self.insertPlainText(f"{message}\n")

        # 自动滚动到底部
        self.ensureCursorVisible()

    def _hex_to_color(self, hex_color):
        """将十六进制颜色转换为QColor"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return QColor(r, g, b)

    def clear(self):
        """清空日志"""
        super().clear()