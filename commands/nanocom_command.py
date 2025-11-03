from utils.command_runner import CommandRunner


class NanocomCommand(CommandRunner):
    def execute(self):
        # 从 routes 包中导入 sys_read
        from routes.sysconfig_read import sys_read

        sys_reader = sys_read()
        # 将统一的logger传递给sys_reader
        sys_reader.set_logger(self.logger)
        return sys_reader.main()