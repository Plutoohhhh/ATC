import json
import pexpect
from pathlib import Path


class ScoutValidate:
    def __init__(self):
        self.child = None
        self.logger = None
        self.terminal_logger = None

    def set_logger(self, logger):
        self.logger = logger
        if logger:
            self.terminal_logger = logger.get_terminal_logger()

    def set_session_path(self, session_path):
        """设置会话路径"""
        self.session_path = session_path
        if self.logger:
            self.logger.set_session_path(session_path)

    def log(self, level, message):
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")

    def log_terminal_send(self, data):
        """记录发送到终端的数据"""
        if self.terminal_logger:
            self.terminal_logger.log_send(data)

    def log_terminal_receive(self, data):
        """记录从终端接收的数据"""
        if self.terminal_logger:
            self.terminal_logger.log_receive(data)

    def log_terminal_expect(self, pattern):
        """记录期望的模式"""
        if self.terminal_logger:
            self.terminal_logger.log_expect(str(pattern))

    def log_terminal_timeout(self):
        """记录超时"""
        if self.terminal_logger:
            self.terminal_logger.log_timeout()

    def _ensure_pattern_list(self, patterns):
        """确保模式是列表形式"""
        if isinstance(patterns, str):
            return [patterns]
        return list(patterns)

    def expect_with_logging(self, patterns, timeout=None):
        """带日志记录的expect方法"""
        # 确保模式是列表形式
        pattern_list = self._ensure_pattern_list(patterns)

        self.log_terminal_expect(pattern_list)
        try:
            result = self.child.expect(pattern_list, timeout=timeout)

            # 记录匹配到的内容
            if self.child.before:
                self.log_terminal_receive(self.child.before)
            if self.child.after:
                self.log_terminal_receive(self.child.after)

            return result

        except pexpect.TIMEOUT:
            self.log_terminal_timeout()
            if self.child.before:
                self.log_terminal_receive(self.child.before)
            raise
        except Exception as e:
            self.log("错误", f"expect操作异常: {e}")
            if self.child.before:
                self.log_terminal_receive(self.child.before)
            raise

    def sendline_with_logging(self, data):
        """带日志记录的sendline方法"""
        self.log_terminal_send(data + "\n")
        self.child.sendline(data)

    def create_directory_structure(self, config, base_path):
        """
        递归创建目录结构并执行命令
        """
        for key, value in config.items():
            current_path = base_path / key
            current_path.mkdir(exist_ok=True)

            if isinstance(value, dict):
                # 如果是字典，继续递归
                self.create_directory_structure(value, current_path)
            elif isinstance(value, str):
                # 如果是字符串，执行命令
                self.execute_and_save_command(value, current_path)

    def execute_commands_from_config(self, config_file):
        # 读取配置文件
        with open(config_file, 'r') as f:
            config = json.load(f)

        # 创建主文件夹
        main_dir = Path.home() / "Desktop" / "scout_validation"
        main_dir.mkdir(exist_ok=True)

        # 使用递归方法创建目录结构并执行命令
        self.create_directory_structure(config, main_dir)

    def execute_and_save_command(self, command, output_dir):
        output_file = output_dir / "output.txt"

        self.log("程序输出", f"开始执行命令: {command}")

        try:
            # 使用 pexpect 执行命令
            self.child = pexpect.spawn(command, encoding='utf-8', timeout=600)

            # 等待命令执行完成，直到出现提示符 "~ %"
            self.expect_with_logging('~ %', timeout=600)

            # 获取命令输出
            output = self.child.before

            # 关闭子进程并获取退出状态码
            self.child.close()

            # 获取返回码
            if self.child.exitstatus is not None:
                return_code = self.child.exitstatus
            elif self.child.signalstatus is not None:
                # 如果进程被信号终止，使用标准的信号退出码
                return_code = 128 + self.child.signalstatus
            else:
                return_code = 0  # 假设成功

            # 保存输出到文件，包括返回码
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
                f.write("\n" + "=" * 50 + "\n")
                f.write(f"Return Code: {return_code}")

            self.log("程序输出", f"命令 '{command}' 执行完成，返回码: {return_code}，输出已保存到 {output_file}")

        except pexpect.TIMEOUT:
            self.log("错误", f"命令 '{command}' 执行超时")
            # 尝试获取超时前的输出
            try:
                output_before_timeout = self.child.before if self.child else "No output before timeout"
            except:
                output_before_timeout = "No output before timeout"

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_before_timeout)
                f.write("\n" + "=" * 50 + "\n")
                f.write(f"Return Code: 124")  # 使用标准的超时退出码 124

        except pexpect.ExceptionPexpect as e:
            self.log("错误", f"执行命令 '{command}' 时出错: {str(e)}")
            # 尝试获取错误前的输出
            try:
                output_before_error = self.child.before if self.child else f"Error: {str(e)}"
            except:
                output_before_error = f"Error: {str(e)}"

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_before_error)
                f.write("\n" + "=" * 50 + "\n")
                f.write(f"Return Code: 125")  # 使用标准的无法执行退出码 125

        except Exception as e:
            self.log("错误", f"未知错误: {str(e)}")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Unknown error: {str(e)}")
                f.write("\n" + "=" * 50 + "\n")
                f.write(f"Return Code: 126")  # 使用标准的命令无法调用退出码 126
        finally:
            # 确保子进程被终止
            if self.child and self.child.isalive():
                self.child.close()
            self.child = None

    def main(self):
        self.log("系统", "=== Scout 验证脚本开始 ===")

        try:
            self.execute_commands_from_config("../UI/config.json")
            self.log("系统", "完成执行: ScoutValidateCommand")
        except Exception as e:
            self.log("错误", f"脚本执行错误: {e}")


def main():
    # 创建日志记录器
    from utils.logger import UnifiedLogger
    logger = UnifiedLogger()

    validator = ScoutValidate()
    validator.set_logger(logger)

    try:
        validator.main()
    finally:
        logger.close()


if __name__ == "__main__":
    main()