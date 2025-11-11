import pexpect
import sys
import re
import time
import os
import os.path
from datetime import datetime

# --- 配置区: 请根据你的需求修改 ---

# 1. 要执行的命令列表
COMMANDS_TO_RUN = [
    "pwd",
    "ls",
    "date"
    # 在这里添加更多你需要的命令...
]

# 2. 登录凭据 (如果不需要登录, 保持为 None)
USERNAME = 'local'
PASSWORD = 'local'

# 3. [重要] 机台的 OS 模式提示符 (来自你的 Chimp_serial.txt 日志)
TARGET_PROMPT_STRING = "local@locals-Mac ~ %"
TARGET_PROMPT_REGEX = re.escape(TARGET_PROMPT_STRING)

# 4. 基础日志文件名
LOG_FILE_NAME = "nanocom_session.log"

# 5. 超时设置 (秒)
TIMEOUT = 15


class sys_read:
    def __init__(self):
        self.logger = None
        self.raw_log_file = None
        self.session_start_time = None
        self.test_session_path = None
        self.terminal_logger = None
        self.child = None

    def set_logger(self, logger):
        """设置统一的日志记录器"""
        self.logger = logger
        if logger:
            self.terminal_logger = logger.get_terminal_logger()

    def log(self, level, message):
        """统一的日志方法 - 使用UnifiedLogger"""
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

    def expect_with_logging(self, pattern_list, timeout=None):
        """带日志记录的expect方法"""
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

    def create_session_directory(self):
        """创建测试会话目录结构"""
        try:
            desktop_path = os.path.expanduser("~/Desktop")

            # 创建日期文件夹
            date_str = datetime.now().strftime("%Y-%m-%d")
            date_folder = os.path.join(desktop_path, f"ATC_Logs_{date_str}")
            os.makedirs(date_folder, exist_ok=True)

            # 创建测试会话文件夹
            session_time = datetime.now().strftime("%H%M%S")
            self.test_session_path = os.path.join(date_folder, f"test_session_{session_time}")
            os.makedirs(self.test_session_path, exist_ok=True)

            self.log("系统", f"测试会话目录已创建: {self.test_session_path}")
            return True

        except Exception as e:
            self.log("错误", f"创建会话目录失败: {e}")
            return False

    def setup_logging(self):
        """设置日志文件 - 完整的终端会话记录"""
        if not self.create_session_directory():
            return False

        try:
            # 完整的终端会话日志文件路径
            log_file_path = os.path.join(self.test_session_path, LOG_FILE_NAME)

            # 打开原始日志文件 - 记录所有原始字节，包括控制字符
            self.raw_log_file = open(log_file_path, 'wb')
            self.session_start_time = datetime.now()

            self.log("系统", f"完整终端会话日志将保存到: {log_file_path}")
            return True

        except Exception as e:
            self.log("错误", f"设置日志文件失败: {e}")
            return False

    def create_complete_terminal_logger(self):
        """创建完整的终端日志记录器 - 记录所有输入输出"""

        class CompleteTerminalLogger:
            def __init__(self, raw_log_file, ui_logger):
                self.raw_log_file = raw_log_file
                self.ui_logger = ui_logger
                self.pending_command = None

            def write(self, data):
                # 记录所有原始字节到文件
                if isinstance(data, str):
                    data_bytes = data.encode('utf-8', errors='replace')
                else:
                    data_bytes = data

                # 写入文件 - 这是关键，记录所有原始数据
                self.raw_log_file.write(data_bytes)
                self.raw_log_file.flush()

                # 处理数据显示到UI
                self._process_for_ui(data_bytes)

            def _process_for_ui(self, data_bytes):
                """处理数据用于UI显示"""
                try:
                    decoded = data_bytes.decode('utf-8', errors='replace')

                    # 将重要信息发送到UI
                    lines = decoded.split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        # 检测重要事件
                        if 'Serial device' in line:
                            self.ui_logger.log("系统输出", f"发现设备: {line}")
                        elif 'Select a device by its number' in line:
                            self.ui_logger.log("系统输出", "等待选择设备...")
                        elif 'login:' in line.lower() or 'username:' in line.lower():
                            self.ui_logger.log("系统输出", "需要登录")
                        elif 'password:' in line.lower():
                            self.ui_logger.log("系统输出", "需要密码")
                        elif TARGET_PROMPT_STRING in line:
                            self.ui_logger.log("系统输出", "进入目标系统")

                except Exception as e:
                    pass

            def flush(self):
                self.raw_log_file.flush()

            def log_command(self, command):
                """专门记录命令 - 确保命令被记录"""
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # 在UI中显示命令
                self.ui_logger.log("命令输入", f"执行命令: {command}")
                # 同时确保命令被写入日志文件
                command_bytes = f"\n[{timestamp}] [COMMAND] 执行命令: {command}\n".encode('utf-8')
                self.raw_log_file.write(command_bytes)
                self.raw_log_file.flush()

        return CompleteTerminalLogger(self.raw_log_file, self.logger)

    def send_command_with_logging(self, command, description=None):
        """发送命令并确保完整记录"""
        if description:
            self.log("程序输出", description)

        # 使用专门的命令记录方法
        self.terminal_logger.log_command(command)

        # 发送命令
        self.child.sendline(command)

    def find_port_number(self, output_before):
        """动态查找 C-line 或 S-line 端口"""
        # 策略 1: 尝试查找 C-line 端口
        c_line_match = re.findall(r'Serial device \((\d+)\)\s*:\s*/dev/cu\.chimp-(\S+-ch-0)', output_before)
        if c_line_match:
            port_number = c_line_match[0][0]
            self.log("程序输出", f"自动找到 C-line 端口: {port_number}")
            return port_number

        # 策略 2: 尝试查找 S-line "base" 端口
        self.log("程序输出", "未找到 C-line (-ch-0) 端口, 尝试 S-line 'base' 端口逻辑")

        all_ports_match = re.findall(r'Serial device \((\d+)\)\s*:\s*(\S+)', output_before)
        if not all_ports_match:
            return None

        port_map = dict(all_ports_match)
        port_paths = port_map.values()

        for number, path in port_map.items():
            is_base_port = any(
                other.startswith(path + "-")
                for other in port_paths
                if other != path
            )

            if is_base_port:
                self.log("程序输出", f"自动找到 S-line 'base' 端口: {number} ({path})")
                return number

        return None

    def wait_for_prompt(self, timeout=30):
        """等待目标提示符出现"""
        try:
            self.child.expect(TARGET_PROMPT_REGEX, timeout=timeout)
            return True
        except pexpect.TIMEOUT:
            self.log("错误", f"等待提示符超时 ({timeout}秒)")
            return False
        except pexpect.EOF:
            self.log("错误", "终端会话意外结束")
            return False

    def main(self, keep_alive=False):
        if not self.setup_logging():
            return

        try:
            self.log("系统", "自动化脚本启动")
            self.log("系统", f"目标 OS 提示符已设为: '{TARGET_PROMPT_STRING}'")

            # 启动 nanocom 进程 - 使用与 terminal_collect.py 相同的参数
            self.child = pexpect.spawn('/bin/bash', ['-c', '/usr/local/bin/nanocom -y'],
                                       encoding='utf-8', codec_errors='replace')

            # 设置终端大小
            self.child.setwinsize(24, 80)

            # 创建完整的终端日志记录器
            self.terminal_logger = self.create_complete_terminal_logger()
            self.child.logfile = self.terminal_logger

            # 动态端口选择
            self.log("程序输出", "正在等待 nanocom 加载设备列表...")

            # 等待设备列表
            try:
                self.child.expect(r'Select a device by its number', timeout=TIMEOUT)
            except (pexpect.exceptions.TIMEOUT, pexpect.exceptions.EOF) as e:
                self.log("错误", "启动 nanocom 后未找到 'Select a device' 提示")
                # 记录错误信息到日志文件
                error_msg = f"\n[ERROR] 未找到设备选择提示: {e}\n"
                self.raw_log_file.write(error_msg.encode('utf-8'))
                return

            # 获取设备列表输出并查找端口
            output_before = self.child.before
            port_number = self.find_port_number(output_before)

            if not port_number:
                self.log("错误", "没有找到可用端口 (C-line 或 S-line)")
                # 记录错误信息到日志文件
                error_msg = f"\n[ERROR] 没有找到可用端口\n设备列表:\n{output_before}\n"
                self.raw_log_file.write(error_msg.encode('utf-8'))
                return

            self.log("程序输出", f"最终选择端口: {port_number}")

            # 发送端口选择命令
            self.send_command_with_logging(port_number, "选择设备端口")

            # 等待连接建立
            time.sleep(2)

            # 发送回车唤醒提示符
            self.send_command_with_logging("", "发送回车唤醒提示符")

            # 检测系统状态
            self.log("程序输出", "正在检测机台状态...")

            index = self.child.expect([
                TARGET_PROMPT_REGEX,  # 索引 0 (OS Mode)
                r'(?i)login:|(?i)username:',  # 索引 1 (Login needed)
                r'(?i)password:',  # 索引 2 (Password only)
                re.escape(":)"),  # 索引 3 (Diags)
                # re.escape("]"),  # 索引 4 (Recovery)
                pexpect.TIMEOUT,  # 索引 4 (Booting/Unknown)
                pexpect.EOF  # 索引 5 (Crashed)
            ], timeout=TIMEOUT)

            if index == 0:  # OS Mode
                self.log("程序输出", f"状态: OS 模式 (检测到 '{TARGET_PROMPT_STRING}')")
                self.log("程序输出", "无需登录, 准备执行命令")

            elif index == 1:  # login/username
                if not USERNAME or not PASSWORD:
                    self.log("错误", "检测到登录提示, 但脚本中未配置 USERNAME/PASSWORD")
                    return
                self.log("程序输出", "状态: 需要登录。正在发送用户名")
                self.send_command_with_logging(USERNAME, "发送用户名")
                self.child.expect(r'(?i)password:')
                self.log("程序输出", "正在发送密码")
                self.send_command_with_logging(PASSWORD, "发送密码")
                if not self.wait_for_prompt():
                    return
                self.log("程序输出", f"登录成功, 已进入 OS 模式 ({TARGET_PROMPT_STRING})")

            elif index == 2:  # password only
                if not PASSWORD:
                    self.log("错误", "检测到密码提示, 但脚本中未配置 PASSWORD")
                    return
                self.log("程序输出", "状态: 需要密码。正在发送密码")
                self.send_command_with_logging(PASSWORD, "发送密码")
                if not self.wait_for_prompt():
                    return
                self.log("程序输出", f"登录成功, 已进入 OS 模式 ({TARGET_PROMPT_STRING})")

            elif index == 3:  # Diags
                self.log("错误", "检测到 Diags 模式 (':)')")
                self.log("错误", "命令无法在此模式下执行, 脚本终止。")
                return

            elif index == 4:  # TIMEOUT
                self.log("错误", f"发送 'Enter' 后超时 ({TIMEOUT}秒)")
                self.log("错误", "状态: 未知或正在 Booting (未收到任何已知提示符)")
                return

            elif index == 5:  # EOF
                self.log("错误", "进程在检测状态时意外终止 (EOF)")
                return

            # 执行命令循环
            self.log("系统", "机台已就绪, 正在开始执行命令...")

            for cmd in COMMANDS_TO_RUN:
                # 发送命令
                self.send_command_with_logging(cmd, f"执行命令: {cmd}")

                # 等待命令完成
                if not self.wait_for_prompt():
                    break

                time.sleep(0.5)  # 命令间的小延迟

            self.log("系统", "所有命令在机台执行完毕")

        except (pexpect.exceptions.TIMEOUT, pexpect.exceptions.EOF) as e:
            self.log("错误", f"脚本执行期间发生严重错误: {e}")
            # 记录错误到日志文件
            error_msg = f"\n[ERROR] 严重错误: {e}\n"
            self.raw_log_file.write(error_msg.encode('utf-8'))
        except Exception as e:
            self.log("错误", f"发生意外的 Python 错误: {e}")
            # 记录错误到日志文件
            error_msg = f"\n[ERROR] Python错误: {e}\n"
            self.raw_log_file.write(error_msg.encode('utf-8'))
        finally:
            # 记录会话结束
            end_time = datetime.now()
            duration = end_time - self.session_start_time
            session_end = f"\n\n=== 会话结束 ===\n时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n持续时间: {duration}\n"
            self.raw_log_file.write(session_end.encode('utf-8'))

            # 清理资源
            if self.child and self.child.isalive():
                self.child.terminate()
            if self.raw_log_file:
                self.raw_log_file.close()
            self.log("系统", f"脚本结束，完整日志保存在: {self.test_session_path}")


if __name__ == "__main__":
    instance = sys_read()
    instance.main()