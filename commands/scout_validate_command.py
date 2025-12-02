# scout_validate_command.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QSpinBox, QFileDialog,
                             QGroupBox, QFormLayout)
from PyQt5.QtCore import pyqtSignal, QObject
from utils.command_runner import CommandRunner
from routes import scout_validate


class ScoutValidateConfigManager(QObject):
    """Scout Validate 配置管理器"""

    config_received = pyqtSignal(dict)
    dialog_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.config = None
        self.dialog = None

    def show_dialog(self):
        """显示配置对话框"""

        class ScoutValidateConfigDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("配置 Scout Validate")
                self.resize(500, 300)
                self.setup_ui()

            def setup_ui(self):
                layout = QVBoxLayout()

                # 配置文件设置组
                config_group = QGroupBox("配置文件路径")
                config_layout = QFormLayout()

                # 非交互式命令配置文件
                subprocess_layout = QHBoxLayout()
                self.subprocess_edit = QLineEdit()
                self.subprocess_edit.setPlaceholderText("选择非交互式命令配置文件...")
                subprocess_browse_btn = QPushButton("浏览")
                subprocess_browse_btn.clicked.connect(self.browse_subprocess_config)
                subprocess_layout.addWidget(self.subprocess_edit)
                subprocess_layout.addWidget(subprocess_browse_btn)
                config_layout.addRow("非交互式配置:", subprocess_layout)

                # 交互式命令配置文件
                pexpect_layout = QHBoxLayout()
                self.pexpect_edit = QLineEdit()
                self.pexpect_edit.setPlaceholderText("选择交互式命令配置文件...")
                pexpect_browse_btn = QPushButton("浏览")
                pexpect_browse_btn.clicked.connect(self.browse_pexpect_config)
                pexpect_layout.addWidget(self.pexpect_edit)
                pexpect_layout.addWidget(pexpect_browse_btn)
                config_layout.addRow("交互式配置:", pexpect_layout)

                config_group.setLayout(config_layout)
                layout.addWidget(config_group)

                # 按钮组
                button_layout = QHBoxLayout()
                ok_btn = QPushButton("确定")
                ok_btn.clicked.connect(self.accept)
                cancel_btn = QPushButton("取消")
                cancel_btn.clicked.connect(self.reject)
                button_layout.addStretch()
                button_layout.addWidget(ok_btn)
                button_layout.addWidget(cancel_btn)
                layout.addLayout(button_layout)

                self.setLayout(layout)

            def browse_subprocess_config(self):
                """浏览非交互式命令配置文件"""
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "选择非交互式命令配置文件",
                    "",
                    "JSON Files (*.json);;All Files (*)"
                )
                if file_path:
                    self.subprocess_edit.setText(file_path)

            def browse_pexpect_config(self):
                """浏览交互式命令配置文件"""
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "选择交互式命令配置文件",
                    "",
                    "JSON Files (*.json);;All Files (*)"
                )
                if file_path:
                    self.pexpect_edit.setText(file_path)

            def get_config(self):
                """获取配置数据"""
                return {
                    'subprocess_config': self.subprocess_edit.text(),
                    'pexpect_config': self.pexpect_edit.text()
                }

        self.dialog = ScoutValidateConfigDialog()
        if self.dialog.exec_() == QDialog.Accepted:
            self.config = self.dialog.get_config()
            self.config_received.emit(self.config)
        else:
            self.config = None
        self.dialog_finished.emit()


class ScoutValidateCommand(CommandRunner):
    def __init__(self, logger=None):
        super().__init__(logger)
        self.config = None
        self.config_manager = None
        self.timeout = 30
        self.subprocess_config = None
        self.pexpect_config = None

    def get_config_from_dialog(self):
        """通过配置管理器获取配置"""
        self.config_manager = ScoutValidateConfigManager()
        self.config_manager.config_received.connect(self._on_config_received)

        # 显示对话框
        self.config_manager.show_dialog()

        return self.config

    def _on_config_received(self, config):
        """配置接收回调"""
        self.config = config
        # 应用配置
        if config:
            self.subprocess_config = config.get('subprocess_config')
            self.pexpect_config = config.get('pexpect_config')

    def set_timeout(self, timeout):
        """设置超时时间"""
        self.timeout = timeout

    def set_config_paths(self, subprocess_config, pexpect_config):
        """设置配置文件路径"""
        self.subprocess_config = subprocess_config
        self.pexpect_config = pexpect_config

    def set_config(self, config):
        """设置配置（从主线程调用）"""
        if config:
            self.subprocess_config = config.get('subprocess_config')
            self.pexpect_config = config.get('pexpect_config')
            self.config = config

    def execute(self):
        """执行 Scout Validate 命令"""
        if not self.config:
            self.logger.log("错误", "请先通过设置按钮配置 Scout Validate 参数")
            return False

        self.logger.log("系统", "开始执行 Scout Validate")
        if self.subprocess_config:
            self.logger.log("程序输出", f"非交互式配置文件: {self.subprocess_config}")
        if self.pexpect_config:
            self.logger.log("程序输出", f"交互式配置文件: {self.pexpect_config}")

        try:
            scouter = scout_validate.ScoutValidate()
            scouter.set_logger(self.logger)

            # 如果有自定义配置文件路径，传递给 ScoutValidate
            if hasattr(scouter, 'set_config_paths') and self.subprocess_config and self.pexpect_config:
                scouter.set_config_paths(self.subprocess_config, self.pexpect_config)

            return scouter.main()

        except Exception as e:
            self.logger.log("错误", f"Scout Validate 执行异常: {e}")
            return False