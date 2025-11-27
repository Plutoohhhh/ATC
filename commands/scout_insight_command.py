# commands/scout_insight_command.py (修复版)
from PyQt5.QtWidgets import QApplication

from utils.command_runner import CommandRunner
from routes import scout_insight
from PyQt5.QtCore import pyqtSignal, QObject
import threading


class ScoutConfigManager(QObject):
    """配置管理器，用于在主线程中处理对话框"""

    config_received = pyqtSignal(dict)
    dialog_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.config = None
        self.dialog = None

    def show_dialog(self):
        """在主线程中显示对话框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox

        class ScoutConfigDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Scout Insight 配置")
                self.setModal(True)
                self.resize(400, 300)

                self.sn = ""
                self.station = ""
                self.user_path = ""
                self.target_timestamp = ""

                self.init_ui()

            def init_ui(self):
                layout = QVBoxLayout()

                # SN 输入
                sn_layout = QHBoxLayout()
                sn_layout.addWidget(QLabel("设备序列号 (SN):"))
                self.sn_input = QLineEdit()
                self.sn_input.setPlaceholderText("例如: C2C73PT95C")
                sn_layout.addWidget(self.sn_input)
                layout.addLayout(sn_layout)

                # Station 输入
                station_layout = QHBoxLayout()
                station_layout.addWidget(QLabel("站点名称:"))
                self.station_input = QLineEdit()
                self.station_input.setPlaceholderText("例如: SW-DOWNLOAD")
                station_layout.addWidget(self.station_input)
                layout.addLayout(station_layout)

                # 用户路径输入
                path_layout = QHBoxLayout()
                path_layout.addWidget(QLabel("用户路径:"))
                self.path_input = QLineEdit()
                self.path_input.setPlaceholderText("例如: /private/tmp/log")
                path_layout.addWidget(self.path_input)
                layout.addLayout(path_layout)

                # 时间戳输入
                timestamp_layout = QHBoxLayout()
                timestamp_layout.addWidget(QLabel("目标时间戳:"))
                self.timestamp_input = QLineEdit()
                self.timestamp_input.setPlaceholderText("例如: 20250523-210217")
                timestamp_layout.addWidget(self.timestamp_input)
                layout.addLayout(timestamp_layout)

                # 按钮布局
                button_layout = QHBoxLayout()

                self.ok_button = QPushButton("确定")
                self.ok_button.clicked.connect(self.accept_config)
                button_layout.addWidget(self.ok_button)

                self.cancel_button = QPushButton("取消")
                self.cancel_button.clicked.connect(self.reject)
                button_layout.addWidget(self.cancel_button)

                layout.addLayout(button_layout)
                self.setLayout(layout)

            def accept_config(self):
                """接受配置并验证"""
                self.sn = self.sn_input.text().strip()
                self.station = self.station_input.text().strip()
                self.user_path = self.path_input.text().strip()
                self.target_timestamp = self.timestamp_input.text().strip()

                # 基本验证
                if not all([self.sn, self.station, self.user_path, self.target_timestamp]):
                    QMessageBox.warning(self, "输入错误", "请填写所有必填字段")
                    return

                # 时间戳格式验证
                if not self.target_timestamp.replace("-", "").isdigit():
                    QMessageBox.warning(self, "输入错误", "时间戳格式不正确，应为: YYYYMMDD-HHMMSS")
                    return

                self.accept()

        self.dialog = ScoutConfigDialog()
        if self.dialog.exec_() == QDialog.Accepted:
            self.config = {
                'sn': self.dialog.sn,
                'station': self.dialog.station,
                'user_path': self.dialog.user_path,
                'target_timestamp': self.dialog.target_timestamp
            }
            self.config_received.emit(self.config)
        else:
            self.config = None
        self.dialog_finished.emit()


class ScoutInsightCommand(CommandRunner):
    def __init__(self, logger=None):
        super().__init__(logger)
        self.config = None
        self.config_manager = None
        self.config_received = False
        self.config_result = None

    def get_config_from_dialog(self):
        """通过配置管理器获取配置（线程安全）"""
        # 这个方法现在只在主线程中调用
        self.config_manager = ScoutConfigManager()
        self.config_manager.config_received.connect(self._on_config_received)
        self.config_manager.dialog_finished.connect(self._on_dialog_finished)

        # 显示对话框
        self.config_manager.show_dialog()

        # 等待对话框完成
        while not self.config_received:
            QApplication.processEvents()

        return self.config_result

    def _on_config_received(self, config):
        """配置接收回调"""
        self.config_result = config
        self.config_received = True

    def _on_dialog_finished(self):
        """对话框完成回调"""
        if not self.config_received:
            self.config_received = True

    def execute(self):
        """执行scout insight命令"""
        # 注意：这个方法在命令线程中执行，不能直接创建UI

        # 检查是否已有配置
        if not self.config:
            self.logger.log("错误", "请先通过设置按钮配置 Scout Insight 参数")
            return False

        self.logger.log("系统", "开始执行 Scout Insight 下载")
        self.logger.log("程序输出", f"设备序列号: {self.config['sn']}")
        self.logger.log("程序输出", f"站点名称: {self.config['station']}")
        self.logger.log("程序输出", f"用户路径: {self.config['user_path']}")
        self.logger.log("程序输出", f"目标时间戳: {self.config['target_timestamp']}")

        try:
            # 创建scout自动化实例
            automation = scout_insight.ScoutAutomation(self.logger)
            success = automation.run_automated_download(
                sn=self.config['sn'],
                station=self.config['station'],
                user_path=self.config['user_path'],
                target_timestamp=self.config['target_timestamp']
            )

            if success:
                self.logger.log("系统", "Scout Insight 下载完成")
            else:
                self.logger.log("错误", "Scout Insight 下载失败")

            return success

        except Exception as e:
            self.logger.log("错误", f"Scout Insight 执行异常: {e}")
            return False

    def set_config(self, config):
        """设置配置（从主线程调用）"""
        self.config = config