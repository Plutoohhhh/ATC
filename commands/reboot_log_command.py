from utils.command_runner import CommandRunner
from routes import reboot_log


class RebootLogCommand(CommandRunner):
    def execute(self):
        collector = reboot_log.RebootLogCollector()
        # 将统一的logger传递给collector
        collector.set_logger(self.logger)
        return collector.main()
