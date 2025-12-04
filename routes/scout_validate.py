import json
import subprocess
import time

import pexpect
import shutil
from pathlib import Path
from typing import Union, Dict


class ScoutValidate:
    def __init__(self):
        self.logger = None
        self.terminal_logger = None
        self.session_path = None
        self.child = None
        self.radar_id = None # 默认雷达号

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

        except pexpect.EOF:
            # EOF不是错误，只是命令执行完成
            if self.child.before:
                self.log_terminal_receive(self.child.before)
            self.log_terminal_receive("命令执行完成 (EOF)")
            return 0  # 返回成功状态

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

    def move_scout_folder(self, output_dir: Path):
        """
        移动/tmp/scout文件夹到输出目录

        Args:
            output_dir: 命令输出目录
        """
        tmp_scout_path = Path("/tmp/scout")
        dest_scout_path = output_dir / "scout"

        if not tmp_scout_path.exists():
            self.log("系统", f"/tmp/scout 文件夹不存在，跳过移动")
            return

        try:
            # 如果目标已存在，先删除
            if dest_scout_path.exists():
                shutil.rmtree(dest_scout_path)
                self.log("系统", f"已删除已存在的目录: {dest_scout_path}")

            # 移动文件夹
            shutil.move(str(tmp_scout_path), str(dest_scout_path))
            self.log("系统", f"已将 /tmp/scout 移动到 {dest_scout_path}")

        except Exception as e:
            self.log("错误", f"移动 /tmp/scout 失败: {str(e)}")

    def replace_radar_id_in_command(self, command: str) -> str:
        """替换命令中的雷达号占位符"""
        if "{radar}" in command:
            return command.replace("{radar}", self.radar_id)
        elif "163084325" in command:
            # 如果配置文件中有硬编码的雷达号，也替换它
            return command.replace("163084325", self.radar_id)
        return command

    def create_directory_structure(self, config: Dict, base_path: Path, use_pexpect=False):
        """
        递归创建目录结构并执行命令
        """
        for key, value in config.items():
            current_path = base_path / key
            current_path.mkdir(exist_ok=True)

            if isinstance(value, dict):
                # 如果是字典，继续递归
                self.create_directory_structure(value, current_path, use_pexpect)
            elif isinstance(value, str):
                # 如果是字符串，执行命令前替换雷达号
                command = self.replace_radar_id_in_command(value)
                if use_pexpect:
                    self.execute_with_pexpect(command, current_path)
                else:
                    self.execute_with_subprocess(command, current_path)

                # 每条命令执行后，移动scout文件夹
                self.move_scout_folder(current_path)

    def execute_commands_from_config(self, config_file: Union[str, Path], use_pexpect=False):
        """从配置文件执行命令"""
        # 读取配置文件
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 创建主文件夹
        main_dir = Path.home() / "Desktop" / "scout_validation"
        main_dir.mkdir(exist_ok=True)

        # 设置会话路径，确保日志文件在正确的位置创建
        self.set_session_path(main_dir)

        # 使用递归方法创建目录结构并执行命令
        self.create_directory_structure(config, main_dir, use_pexpect)

    def execute_with_subprocess(self, command: str, output_dir: Path):
        """使用 subprocess 执行非交互式命令并保存输出"""
        output_file = output_dir / "output.txt"

        self.log("程序输出", f"开始执行命令(非交互式): {command}")

        # 记录要执行的命令到终端日志
        self.log_terminal_send(f"执行非交互式命令: {command}")

        try:
            # 使用 subprocess 执行命令
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=600
            )

            # 组合标准输出和错误输出
            full_output = result.stdout
            if result.stderr:
                full_output += f"\n--- 错误输出 ---\n{result.stderr}"

            self.log_terminal_receive(full_output) if full_output.strip() else self.log_terminal_receive("(空输出)")

            # 保存输出到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f'$:{command}')
                f.write(full_output)
                f.write("\n" + "=" * 50 + "\n")
                f.write(f"Return Code: {result.returncode}")

            self.log("程序输出", f"命令 '{command}' 执行完成，返回码: {result.returncode}")

        except subprocess.TimeoutExpired:
            self.log("错误", f"命令 '{command}' 执行超时")

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("命令执行超时 (600秒)")
                f.write("\n" + "=" * 50 + "\n")
                f.write("Return Code: 124")

        except Exception as e:
            self.log("错误", f"执行命令 '{command}' 时出错: {str(e)}")

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"执行命令时发生错误: {str(e)}")
                f.write("\n" + "=" * 50 + "\n")
                f.write("Return Code: 125")

    def execute_with_pexpect(self, command: str, output_dir: Path):
        """使用 pexpect 执行交互式命令并保存输出"""
        output_file = output_dir / "output.txt"

        self.log("程序输出", f"开始执行命令(交互式): {command}")

        # 记录要执行的命令到终端日志
        self.log_terminal_send(f"执行命令: {command}")

        try:
            # 使用 pexpect 执行命令
            self.child = pexpect.spawn(command, encoding='utf-8', timeout=600)

            # 检查是否需要选择串行设备
            try:
                # 等待设备选择提示
                device_selection = self.expect_with_logging(['Choose a serial device:', pexpect.EOF, pexpect.TIMEOUT],
                                                            timeout=600)

                if device_selection == 0:  # 找到设备选择提示
                    self.log("程序输出", "检测到设备选择提示，自动选择设备 0")
                    self.sendline_with_logging("0")  # 选择第一个设备

                    # 等待命令完成
                    self.expect_with_logging(pexpect.EOF, timeout=600)

                # 获取命令输出
                output = self.child.before

                # 获取返回码
                self.child.close()
                return_code = self.child.exitstatus if self.child.exitstatus is not None else 0

            except pexpect.TIMEOUT:
                self.log("错误", f"命令 '{command}' 执行超时")
                output = self.child.before if self.child else "命令执行超时"
                return_code = 124
                if self.child and self.child.isalive():
                    self.child.close()

            # 保存输出到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f'$:{command}')
                f.write(output)
                f.write("\n" + "=" * 50 + "\n")
                f.write(f"Return Code: {return_code}")

            self.log("程序输出", f"命令 '{command}' 执行完成，返回码: {return_code}")

        except Exception as e:
            self.log("错误", f"执行命令 '{command}' 时出错: {str(e)}")

            # 尝试获取错误前的输出
            try:
                output_before_error = self.child.before if self.child else f"Error: {str(e)}"
            except:
                output_before_error = f"Error: {str(e)}"

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_before_error)
                f.write("\n" + "=" * 50 + "\n")
                f.write("Return Code: 125")

        finally:
            # 确保子进程被终止
            if self.child and self.child.isalive():
                self.child.close()
            self.child = None

    def set_config_paths(self, subprocess_config, pexpect_config, radar_id=None):
        """设置自定义配置文件路径"""
        self.subprocess_config = subprocess_config
        self.pexpect_config = pexpect_config
        if radar_id:
            self.radar_id = radar_id
            self.log("系统", f"设置雷达号为: {self.radar_id}")

    def main(self):
        """主执行方法"""
        self.log("系统", "=== Scout 验证脚本开始 ===")
        self.log("系统", f"使用雷达号: {self.radar_id}")

        try:
            # 使用自定义路径或默认路径
            subprocess_config_file = getattr(self, 'subprocess_config', "../routes/subprocess_config.json")
            pexpect_config_file = getattr(self, 'pexpect_config', "../routes/pexpect_config.json")

            # 执行非交互式命令（subprocess）
            self.log("系统", "=== 执行非交互式命令 ===")
            self.execute_commands_from_config(subprocess_config_file, use_pexpect=False)

            # 执行交互式命令（pexpect）
            self.log("系统", "=== 执行交互式命令 ===")
            self.execute_commands_from_config(pexpect_config_file, use_pexpect=True)

            self.log("系统", "=== Scout 验证脚本完成 ===")
        except Exception as e:
            self.log("错误", f"脚本执行错误: {e}")


def main():
    """主函数"""
    # 创建日志记录器
    from utils.logger import UnifiedLogger

    # 创建主目录
    main_dir = Path.home() / "Desktop" / "scout_validation"
    main_dir.mkdir(exist_ok=True)

    logger = UnifiedLogger(session_path=main_dir)

    validator = ScoutValidate()
    validator.set_logger(logger)

    try:
        validator.main()
    finally:
        logger.close()


if __name__ == "__main__":
    main()