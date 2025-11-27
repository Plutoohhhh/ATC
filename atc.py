# atc.py (重构后 - 简洁版本)
import sys
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout

from ui.components.log_display import LogDisplay
from utils.logger import UnifiedLogger
from core.command_manager import CommandManager
from core.log_manager import LogManager
from ui.components.button_panel import CommandButtonPanel


class LogWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 初始化核心组件
        self.session_path = self.create_session_directory()
        self.logger = UnifiedLogger(session_path=self.session_path, log_to_file=True)
        self.command_manager = CommandManager(self.logger, self.session_path)
        self.log_manager = LogManager(self.logger)

        # 连接信号
        self.setup_signals()

        # 初始化UI
        self.init_ui()

    def create_session_directory(self):
        """创建会话目录"""
        desktop = Path.home() / "Desktop"
        session_dir = desktop / "ATC_Logs" / datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir.mkdir(parents=True, exist_ok=True)
        return str(session_dir)

    def setup_signals(self):
        """连接所有信号"""
        # 日志信号
        self.logger.log_signal.connect(self.add_log)
        self.command_manager.log_signal.connect(self.add_log)
        self.log_manager.auto_log_signal.connect(self.add_log)

        # 命令管理器信号
        self.command_manager.command_started.connect(self.on_command_started)
        self.command_manager.command_finished.connect(self.on_command_finished)

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('自动化测试控制台')
        self.setGeometry(100, 100, 1000, 600)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 创建左侧按钮面板
        self.button_panel = CommandButtonPanel()
        self.button_panel.command_triggered.connect(self.on_command_triggered)
        self.button_panel.config_triggered.connect(self.on_config_triggered)
        main_layout.addWidget(self.button_panel)

        # 创建右侧日志显示
        self.log_display = LogDisplay()
        main_layout.addWidget(self.log_display)

        # 设置布局比例
        main_layout.setStretchFactor(self.button_panel, 1)
        main_layout.setStretchFactor(self.log_display, 4)

    def on_command_triggered(self, command_name):
        """处理命令触发"""
        if command_name in ["start_logging", "stop_logging", "clear_log"]:
            self.handle_system_command(command_name)
        else:
            self.execute_command(command_name)

    def handle_system_command(self, command_name):
        """处理系统命令"""
        if command_name == "start_logging":
            self.log_manager.start_logging()
        elif command_name == "stop_logging":
            self.log_manager.stop_logging()
        elif command_name == "clear_log":
            self.log_display.clear()
            self.log_manager.clear_logs()

    def execute_command(self, command_name):
        """执行测试命令"""
        from core.command_executor import CommandExecutor

        command = self.command_manager.get_command(command_name)
        if not command:
            self.logger.log("错误", f"未知命令: {command_name}")
            return

        # 特殊处理 Scout Insight 的配置检查
        if command_name == "scout_insight" and not getattr(command, 'config', None):
            self.logger.log("错误", "请先配置 Scout Insight 参数")
            return

        # 使用命令执行器
        executor = CommandExecutor(command, command_name)
        executor.command_started.connect(lambda: self.button_panel.set_button_enabled(command_name, False))
        executor.command_finished.connect(lambda: self.button_panel.set_button_enabled(command_name, True))
        executor.log_signal.connect(self.add_log)
        executor.execute()

    def on_config_triggered(self, command_name):
        """处理配置触发"""
        self.command_manager.configure_command(command_name, self)

    def on_command_started(self, command_name):
        """命令开始回调"""
        self.button_panel.set_button_enabled(command_name, False)

    def on_command_finished(self, command_name):
        """命令完成回调"""
        self.button_panel.set_button_enabled(command_name, True)

    def add_log(self, level, message):
        """添加日志到显示"""
        self.log_display.add_log(level, message)

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.logger.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(get_application_style())

    window = LogWindow()
    window.show()

    sys.exit(app.exec_())


def get_application_style():
    """返回应用程序样式表"""
    return """
        /* 样式表内容保持不变 */
        QMainWindow { background-color: #2d2d30; }
        QPushButton {
            background-color: #3e3e42;
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 5px;
            padding: 8px;
            font-size: 12px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #4a4a4f; border: 1px solid #666; }
        QPushButton:pressed { background-color: #007acc; color: #ffffff; }
        QPushButton:disabled { background-color: #2d2d30; color: #666666; border: 1px solid #444; }
        /* ... 其他样式保持不变 ... */
    """


if __name__ == '__main__':
    main()