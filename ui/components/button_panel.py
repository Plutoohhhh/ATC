# uis/components/button_panel.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QToolButton)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class CommandButtonPanel(QWidget):
    """命令按钮面板组件"""

    # 信号定义
    command_triggered = pyqtSignal(str)  # command_name
    config_triggered = pyqtSignal(str)  # command_name

    def __init__(self):
        super().__init__()
        self.buttons = {}
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignTop)

        # 定义按钮信息
        buttons_info = [
            ("开始记录", "start_logging", True),
            ("停止记录", "stop_logging", True),
            ("清空日志", "clear_log", True),
            ("Nanocom", "nanocom", False),
            ("Reboot Log", "reboot_log", False),
            ("Scout Validate", "scout_validate", False),
            ("Scout Insight", "scout_insight", False),
        ]

        # 创建按钮
        for text, command_name, is_system in buttons_info:
            self.create_command_button(layout, text, command_name, is_system)

        # 添加弹性空间
        layout.addStretch(1)

    def create_command_button(self, layout, text, command_name, is_system):
        """创建命令按钮"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        # 主按钮
        main_button = QPushButton(text)
        main_button.setMinimumHeight(40)
        main_button.setProperty("commandName", command_name)
        main_button.clicked.connect(lambda: self.command_triggered.emit(command_name))
        button_layout.addWidget(main_button)

        # 配置按钮（非系统命令才有）
        if not is_system:
            settings_button = QToolButton()
            settings_button.setText("⚙")
            settings_button.setToolTip(f"配置 {text} 参数")
            settings_button.setFixedSize(30, 40)
            settings_button.setProperty("commandName", command_name)
            settings_button.clicked.connect(lambda: self.config_triggered.emit(command_name))
            button_layout.addWidget(settings_button)
        else:
            # 占位符保持对齐
            placeholder = QWidget()
            placeholder.setFixedSize(30, 40)
            button_layout.addWidget(placeholder)

        layout.addLayout(button_layout)
        self.buttons[command_name] = main_button

    def set_button_enabled(self, command_name, enabled):
        """设置按钮启用状态"""
        if command_name in self.buttons:
            self.buttons[command_name].setEnabled(enabled)