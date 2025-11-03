# commands/check_diags_command.py
from utils.command_runner import CommandRunner
from PyQt5.QtWidgets import QInputDialog


class CheckDiagsCommand(CommandRunner):
    def __init__(self, logger, parent_window=None):
        super().__init__(logger)
        self.parent_window = parent_window

    def execute(self):
        # 从用户获取 spartan_name
        spartan_name, ok = QInputDialog.getText(
            self.parent_window,
            '输入 Spartan Name',
            '请输入 Spartan Modem Name:'
        )

        if not ok or not spartan_name:
            self.logger.log("警告", "用户取消了操作或未输入名称")
            return None

        # 从 routes 包中导入 check_diags_and_return_status
        from routes.check_diags import check_diags_and_return_status

        return check_diags_and_return_status(spartan_name, self.logger)