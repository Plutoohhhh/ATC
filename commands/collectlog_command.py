# commands/collectlog_command.py
from utils.command_runner import CommandRunner
from routes import collectlog

class CollectlogCommand(CommandRunner):
    def execute(self):
        collector = collectlog.RebootLogCollector()
        # 将统一的logger传递给collector
        collector.set_logger(self.logger)
        return collector.main()