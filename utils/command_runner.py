# util/command_runner.py
from abc import ABC, abstractmethod
from utils.logger import UnifiedLogger


class CommandRunner(ABC):
    """命令执行器基类"""

    def __init__(self, logger: UnifiedLogger):
        self.logger = logger

    @abstractmethod
    def execute(self):
        """执行命令的抽象方法"""
        pass

    def run_with_error_handling(self, description):
        """带错误处理的执行方法"""
        try:
            self.logger.log("系统", f"开始执行: {description}")
            result = self.execute()
            self.logger.log("系统", f"完成执行: {description}")
            return result
        except Exception as e:
            self.logger.log("错误", f"执行 {description} 时发生错误: {str(e)}")
            return None