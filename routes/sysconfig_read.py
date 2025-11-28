import pexpect
import sys
import re
import time
import os
import os.path
from datetime import datetime

# 导入工具类
from utils.session_manager import SessionManager, EventHandlers

# --- 配置区: 请根据你的需求修改 ---

# --- 配置区: 请根据你的需求修改 ---
COMMANDS_TO_RUN = ["pwd", "ls", "date"]
USERNAME = 'local'
PASSWORD = 'local'
TARGET_PROMPT_STRING = "local@locals-Mac ~ %"
TARGET_PROMPT_REGEX = re.escape(TARGET_PROMPT_STRING)
LOG_FILE_NAME = "nanocom_session.log"
TIMEOUT = 15


class sys_read:
    def __init__(self):
        self.logger = None
        self.child = None
        self.session_manager = SessionManager("ATC_Logs")

    def set_logger(self, logger):
        """设置统一的日志记录器"""
        self.logger = logger
        self.session_manager.set_logger(logger)

    def log(self, level, message):
        """统一的日志方法"""
        self.session_manager.log(level, message)

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

            # 打开原始日志文件 - 使用二进制写入模式，避免编码问题
            self.raw_log_file = open(log_file_path, 'wb')
            self.session_start_time = datetime.now()

            self.log("系统", f"完整终端会话日志将保存到: {log_file_path}")
            return True

        except Exception as e:
            self.log("错误", f"设置日志文件失败: {e}")
            return False

    def create_raw_terminal_logger(self):
        """创建原始终端日志记录器 - 直接记录所有原始数据，不进行额外处理"""

        class RawTerminalLogger:
            def __init__(self, raw_log_file, ui_logger):
                self.raw_log_file = raw_log_file
                self.ui_logger = ui_logger
                self.buffer = b''  # 使用字节缓冲区

            def write(self, data):
                # 如果是字符串，转换为字节
                if isinstance(data, str):
                    data_bytes = data.encode('utf-8', errors='replace')
                else:
                    data_bytes = data

                # 直接写入原始字节到文件，不进行额外处理
                self.raw_log_file.write(data_bytes)
                self.raw_log_file.flush()

                # 同时更新缓冲区用于UI显示
                self.buffer += data_bytes
                self._process_buffer_for_ui()

            def _process_buffer_for_ui(self):
                """处理缓冲区数据用于UI显示"""
                try:
                    # 尝试解码为UTF-8
                    decoded = self.buffer.decode('utf-8', errors='ignore')

                    # 按行分割，处理完整的行
                    lines = decoded.split('\n')

                    # 如果最后一行不完整，保留在缓冲区中
                    if not decoded.endswith('\n'):
                        self.buffer = lines[-1].encode('utf-8')
                        lines = lines[:-1]
                    else:
                        self.buffer = b''

                    # 处理完整的行
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
                    # 如果解码失败，清空缓冲区
                    self.buffer = b''

            def flush(self):
                self.raw_log_file.flush()

            def log_command(self, command):
                """专门记录命令"""
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # 在UI中显示命令
                self.ui_logger.log("命令输入", f"执行命令: {command}")
                # 同时确保命令被写入日志文件
                command_bytes = f"\n[{timestamp}] [COMMAND] 执行命令: {command}\n".encode('utf-8')
                self.raw_log_file.write(command_bytes)
                self.raw_log_file.flush()

        return RawTerminalLogger(self.raw_log_file, self.logger)

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
            self.expect_with_logging(TARGET_PROMPT_REGEX, timeout=timeout)
            return True
        except pexpect.TIMEOUT:
            self.log("错误", f"等待提示符超时 ({timeout}秒)")
            return False
        except pexpect.EOF:
            self.log("错误", "终端会话意外结束")
            return False

    def main(self, keep_alive=False):
        # 使用会话管理器设置完整会话
        event_handlers = {
            r'serial device': lambda line: self.logger.log("系统输出", f"发现设备: {line}"),
            r'select a device by its number': lambda line: self.logger.log("系统输出", "等待选择设备..."),
            r'login:|username:': EventHandlers.create_login_handler(self.logger),
            r'password:': lambda line: self.logger.log("系统输出", "需要密码"),
            TARGET_PROMPT_STRING: EventHandlers.create_prompt_handler(self.logger, TARGET_PROMPT_REGEX)
        }

        if not self.session_manager.setup_complete_session("nanocom", LOG_FILE_NAME, event_handlers):
            self.log("错误", "会话设置失败")
            return

        try:
            self.log("系统", "自动化脚本启动")
            self.log("系统", f"目标 OS 提示符已设为: '{TARGET_PROMPT_STRING}'")

            # 启动 nanocom 进程
            self.child = pexpect.spawn('/usr/local/bin/nanocom -y', timeout=TIMEOUT)

            # 设置终端日志记录
            if self.session_manager.raw_terminal_logger:
                self.child.logfile = self.session_manager.raw_terminal_logger

            # 动态端口选择
            self.log("程序输出", "正在等待 nanocom 加载设备列表...")

            # 等待设备列表
            try:
                self.expect_with_logging([r'Select a device by its number'], timeout=TIMEOUT)
            except (pexpect.TIMEOUT, pexpect.EOF) as e:
                self.log("错误", "启动 nanocom 后未找到 'Select a device' 提示")
                return

            # 获取设备列表输出并查找端口
            output_before = self.child.before.decode('utf-8', errors='ignore') if self.child.before else ""
            port_number = self.find_port_number(output_before)

            if not port_number:
                self.log("错误", "没有找到可用端口 (C-line 或 S-line)")
                return

            self.log("程序输出", f"最终选择端口: {port_number}")

            # 发送端口选择命令
            self.sendline_with_logging(port_number)

            # 等待连接建立
            time.sleep(2)

            # 发送回车唤醒提示符
            self.sendline_with_logging("")

            # 检测系统状态
            self.log("程序输出", "正在检测机台状态...")

            index = self.expect_with_logging([
                TARGET_PROMPT_REGEX,  # 索引 0 (OS Mode)
                r'(?i)login:|(?i)username:',  # 索引 1 (Login needed)
                r'(?i)password:',  # 索引 2 (Password only)
                re.escape(":)"),  # 索引 3 (Diags)
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
                self.sendline_with_logging(USERNAME)
                self.expect_with_logging([r'(?i)password:'], timeout=5)
                self.log("程序输出", "正在发送密码")
                self.sendline_with_logging(PASSWORD)
                if not self.wait_for_prompt():
                    return
                self.log("程序输出", f"登录成功, 已进入 OS 模式 ({TARGET_PROMPT_STRING})")

            elif index == 2:  # password only
                if not PASSWORD:
                    self.log("错误", "检测到密码提示, 但脚本中未配置 PASSWORD")
                    return
                self.log("程序输出", "状态: 需要密码。正在发送密码")
                self.sendline_with_logging(PASSWORD)
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
                self.child.sendline(cmd)
                if self.session_manager.raw_terminal_logger:
                    self.session_manager.raw_terminal_logger.log_command(cmd)

                # 等待命令完成
                if not self.wait_for_prompt():
                    break

                time.sleep(0.5)

            self.log("系统", "所有命令在机台执行完毕")

        except (pexpect.TIMEOUT, pexpect.EOF) as e:
            self.log("错误", f"脚本执行期间发生严重错误: {e}")
        except Exception as e:
            self.log("错误", f"发生意外的 Python 错误: {e}")
        finally:
            # 清理资源
            if self.child and self.child.isalive():
                self.child.terminate()

            # 清理会话管理器资源
            self.session_manager.cleanup()
            self.log("系统", f"脚本结束，完整日志保存在: {self.session_manager.get_session_path()}")


if __name__ == "__main__":
    instance = sys_read()
    instance.main()