import re
import time
import pexpect
from pathlib import Path


class RebootLogCollector:
    def __init__(self):
        self.host_desktop_path = Path.home() / "Desktop"
        self.child = None
        self.logger = None
        self.terminal_logger = None
        self.device_serial = None

    def set_logger(self, logger):
        self.logger = logger
        if logger:
            self.terminal_logger = logger.get_terminal_logger()

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

    def expect_with_logging(self, pattern_list, timeout=None):
        """带日志记录的expect方法，增加对quote>状态的检测"""
        # 确保包含 quote> 检测
        full_patterns = list(pattern_list) + ["quote>"]

        self.log_terminal_expect(full_patterns)
        try:
            result = self.child.expect(full_patterns, timeout=timeout)

            # 记录匹配到的内容
            if self.child.before:
                self.log_terminal_receive(self.child.before)
            if self.child.after:
                self.log_terminal_receive(self.child.after)

            # 如果检测到 quote> 状态，进行处理
            if result == full_patterns.index("quote>"):
                self.log("警告", "检测到 quote> 状态，发送 Ctrl+C 退出")
                self.child.sendintr()  # 发送 Ctrl+C
                time.sleep(0.5)
                # 重新尝试期望的模式
                result = self.child.expect(pattern_list, timeout=timeout)

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

    def get_device_serial_number(self) -> str:
        """获取设备序列号"""
        if not self.child:
            return "unknown_device"

        self.log("程序输出", "正在获取设备序列号...")
        self.sendline_with_logging("sysconfig read -a")
        self.expect_with_logging("local@locals-Mac", timeout=5)
        response = self.child.before.decode()

        # 提取序列号
        lines = response.split('\n')
        for line in lines:
            if 'SrNm | STR  |' in line:
                sn = line.split('|')[3].strip()
                self.log("程序输出", f"获取到设备序列号: {sn}")
                return sn

        self.log("警告", "无法获取设备序列号，使用默认名称")
        return "unknown_device"

    def find_port_number(self, output_before):
        """获取端口"""
        c_line_match = re.findall(r'Serial device \((\d+)\)\s*:\s*/dev/cu\.chimp-(\S+-ch-0)', output_before)
        if c_line_match:
            port_number = c_line_match[0][0]
            self.log("程序输出", f"找到端口: {port_number}")
            return port_number
        else:
            self.log("错误", "未找到合适的端口")
            return None

    def auto_login_via_nanocom(self) -> bool:
        """通过nanocom自动登录设备"""
        self.log("程序输出", "开始通过nanocom连接设备...")

        try:
            # 启动nanocom并自动选择端口
            self.child = pexpect.spawn('/usr/local/bin/nanocom -y')
            # 记录初始输出
            if self.child.before:
                self.log_terminal_receive(self.child.before)

            expect_result = self.expect_with_logging(
                [pexpect.TIMEOUT, "Select a device by its number"],
                timeout=5
            )

            if expect_result == 1:
                output_before = self.child.before.decode('utf-8', 'ignore')
                port = self.find_port_number(output_before)

                if port is None:
                    self.log("错误", "未找到可用的串口设备")
                    return False
                self.sendline_with_logging(port)
                start_time = time.time()
                while time.time() - start_time <= 2:
                    self.sendline_with_logging("")
                    time.sleep(1)

            # 等待登录提示
            expect_result = self.expect_with_logging(
                [pexpect.TIMEOUT, "login:", "local@locals-Mac"], timeout=30
            )

            if expect_result == 1:  # 检测到登录提示
                self.log("程序输出", "输入用户名local")
                self.sendline_with_logging("local")

                # 检查是否需要密码
                auth_result = self.expect_with_logging([pexpect.TIMEOUT, "Password:"], timeout=5)
                if auth_result == 1:
                    self.log("程序输出", "输入密码local")
                    self.sendline_with_logging("local")

                # 验证登录成功
                if self.expect_with_logging([pexpect.TIMEOUT, "local@locals-Mac"], timeout=60) == 1:
                    self.log("程序输出", "登录成功!")

                    # 获取设备序列号和IP地址
                    self.device_serial = self.get_device_serial_number()
                    return True

            if expect_result == 2:
                self.log("程序输出", "已进入OS")
                return True

            self.log("错误", "登录失败")
            return False

        except Exception as e:
            self.log("错误", f"nanocom连接失败: {e}")
            return False

    def run_command_and_save(self, command: str, filename: str) -> bool:

        self.log("程序输出", f"开始在设备上运行命令: {command}")

        try:
            # 构建保存路径
            save_path = f"/var/tmp/{self.device_serial}/{filename}.txt"

            # 运行命令并重定向输出到文件
            full_command = f"{command} > {save_path}"
            self.sendline_with_logging(full_command)

            except_result = self.expect_with_logging(
                [pexpect.TIMEOUT, "local@locals-Mac"],
                timeout=10  # 稍微增加超时时间
            )

            if except_result == 1:
                self.log("程序输出", f"✅ {filename}.txt 已生成并保存到设备")

                # 验证文件是否创建成功
                self.sendline_with_logging(f"test -f {save_path} && echo 'FILE_EXISTS' || echo 'FILE_MISSING'")
                self.expect_with_logging("local@locals-Mac")
                response = self.child.before.decode()

                if "FILE_EXISTS" in response:
                    self.log("程序输出", f"✅ 文件创建验证成功: {filename}.txt")
                    return True
                else:
                    self.log("警告", f"文件可能未成功创建: {filename}.txt")
                    return False
            else:
                self.log("错误", f"命令执行超时: {command}")
                return False

        except Exception as e:
            self.log("错误", f"运行命令 {command} 失败: {e}")
            return False

    def run_nvram(self) -> bool:
        """运行nvram命令并保存结果"""
        return self.run_command_and_save("nvram -p", "nvram")

    def run_astro(self) -> bool:
        """运行astro命令并保存结果"""
        return self.run_command_and_save("astro status", "astro_status")

    def run_sysdiagnose(self) -> bool:
        """在设备上运行sysdiagnose命令"""
        self.log("程序输出", "开始在设备上运行sysdiagnose...")

        try:
            # 发送sudo sysdiagnose命令
            self.sendline_with_logging("sudo sysdiagnose")

            # 等待密码提示或继续提示
            expect_result = self.expect_with_logging(
                [pexpect.TIMEOUT, "Press 'Enter' to continue"],
                timeout=5
            )

            if expect_result == 1:  # 检测到继续提示
                self.log("程序输出", "按下Enter继续...")
                self.sendline_with_logging("")  # 发送回车

                # 等待sysdiagnose完成
                self.log("程序输出", "等待sysdiagnose完成")
                expect_result = self.expect_with_logging(
                    [pexpect.TIMEOUT, "Output available at", "local@locals-Mac"],
                    timeout=600  # 10分钟超时
                )

                if expect_result == 1 or expect_result == 2:  # sysdiagnose完成
                    self.log("程序输出", "sysdiagnose完成")
                    return True
                else:
                    self.log("错误", "sysdiagnose执行超时")
                    return False
            else:
                self.log("错误", "未找到sysdiagnose的继续提示")
                return False

        except Exception as e:
            self.log("错误", f"运行sysdiagnose失败: {e}")
            return False

    def copy_files_on_device(self) -> str:
        """在设备上创建文件夹并复制日志文件"""
        # 日志路径定义
        log_paths = {
            # "kernel_panics": "/private/var/tmp/kernel_panics",
            # "sys_tmp": "/private/var/tmp",
            "crash_reporter": "/Library/logs/CrashReporter/CoreCapture",
            "burnin": "/Users/local/Library/Logs/Astro/@osdiags/factory/burnin.astro",
            "os_logs": "/FactoryLogs/"
        }

        # 在设备上创建文件夹
        device_folder = f"/var/tmp/{self.device_serial}"
        self.log("程序输出", f"在设备上创建文件夹: {device_folder}")
        self.sendline_with_logging(f"mkdir -p {device_folder}")
        self.expect_with_logging("local@locals-Mac", timeout=5)

        # 复制文件到设备上的文件夹
        for log_name, device_path in log_paths.items():
            self.log("程序输出", f"复制: {device_path} 到 {device_folder}")

            # 检查设备上路径是否存在
            self.sendline_with_logging(f"test -e {device_path} && echo 'EXISTS' || echo 'NOT_EXISTS'")
            self.expect_with_logging("local@locals-Mac")
            response = self.child.before.decode()

            if "EXISTS" in response:
                # 复制文件或目录
                self.sendline_with_logging(f"cp -r {device_path} {device_folder}/")
                self.expect_with_logging("local@locals-Mac")
                self.log("程序输出", f"已复制: {device_path}")
            else:
                self.log("警告", f"路径不存在: {device_path}")

        return device_folder

    def close_nanocom(self):
        """关闭nanocom连接"""
        if self.child and self.child.isalive():
            try:
                self.sendline_with_logging("exit")
                self.child.sendcontrol("a")
                self.child.sendcontrol("x")
                self.child.close()
                self.log("程序输出", "nanocom连接已关闭")
            except:
                pass

    def get_device_ip(self) -> str:
        """获取设备的 IP 地址"""
        if not self.child:
            return "locals-Mac.local"

        self.log("程序输出", "正在获取设备 IP 地址...")

        try:
            # 方法1: 使用 ifconfig 获取 IP
            self.sendline_with_logging("ifconfig | grep 'inet ' | grep -v 127.0.0.1 | head -1")
            self.expect_with_logging("local@locals-Mac", timeout=5)
            response = self.child.before.decode()

            # 提取 IP 地址
            lines = response.split('\n')
            for line in lines:
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if ip_match:
                    ip = ip_match.group(1)
                    self.log("程序输出", f"获取到设备 IP 地址: {ip}")
                    return ip

            self.log("警告", "无法获取设备 IP 地址，使用默认主机名")
            return "locals-Mac.local"

        except Exception as e:
            self.log("错误", f"获取设备 IP 地址失败: {e}")
            return "locals-Mac.local"

    def scp_from_device(self, device_folder: str):
        """在主机上执行SCP命令从设备复制文件夹"""
        # 在主机上创建目标文件夹
        host_folder = self.host_desktop_path / self.device_serial
        host_folder.mkdir(parents=True, exist_ok=True)

        device_ip = self.get_device_ip()

        try:
            ssh_known_hosts_path = Path.home() / ".ssh" / "known_hosts"
            if ssh_known_hosts_path.exists():
                ssh_known_hosts_path.unlink()  # 删除文件
                self.log("程序输出", "已删除 ~/.ssh/known_hosts 文件")
            else:
                self.log("调试", "~/.ssh/known_hosts 文件不存在，无需删除")
        except Exception as e:
            self.log("警告", f"删除 known_hosts 文件失败: {e}")

        # 通过scp将文件夹从设备复制到主机
        self.log("程序输出", "在主机上执行SCP命令...")
        scp_command = f"scp -r local@{device_ip}:{device_folder} {host_folder}"
        self.log("程序输出", f"执行SCP命令: {scp_command}")

        try:
            # 记录命令
            if self.logger:
                self.logger.log_command(
                    "文件传输",
                    f"SCP从设备复制文件夹: {device_folder}",
                    "开始",
                    {"源路径": device_folder, "目标路径": str(host_folder)}
                )

            # 使用pexpect执行SCP命令并自动输入密码
            scp_child = pexpect.spawn(scp_command, encoding='utf-8')

            # 设置终端日志记录
            if self.terminal_logger:
                scp_child.logfile_read = self.terminal_logger.log_file
                scp_child.logfile_send = self.terminal_logger.log_file

            scp_result = scp_child.expect(['Are you sure you want to continue connecting',
                                           pexpect.TIMEOUT,
                                           pexpect.EOF], timeout=10)

            if scp_result == 0:  # 首次连接确认
                scp_child.sendline("yes")
                scp_result = scp_child.expect(['Password:', pexpect.TIMEOUT, pexpect.EOF], timeout=5)

                if scp_result == 0:  # 需要密码
                    scp_child.sendline("local")
                    self.log("程序输出", "开始SCP传输")

                    # 等待传输完成
                    scp_child.expect(pexpect.EOF, timeout=600)
                    self.log("程序输出", "SCP传输完成")

                    # 记录成功
                    if self.logger:
                        self.logger.log_command(
                            "文件传输",
                            f"SCP从设备复制文件夹: {device_folder}",
                            "成功",
                            {"源路径": device_folder, "目标路径": str(host_folder)}
                        )
            else:
                self.log("错误", "SCP传输失败或超时")
                if self.logger:
                    self.logger.log_command(
                        "文件传输",
                        f"SCP从设备复制文件夹: {device_folder}",
                        "失败",
                        {"错误": "连接失败或超时"}
                    )

        except Exception as e:
            self.log("错误", f"SCP传输失败: {e}")
            if self.logger:
                self.logger.log_command(
                    "文件传输",
                    f"SCP从设备复制文件夹: {device_folder}",
                    "失败",
                    {"错误": str(e)}
                )

    def main(self):
        self.log("系统", "=== 设备日志自动收集脚本 ===")

        try:
            if self.auto_login_via_nanocom():
                # 在设备上运行sysdiagnose
                self.run_sysdiagnose()
                # 在设备上复制文件
                device_folder = self.copy_files_on_device()

                self.run_nvram()
                self.run_astro()

                # 在主机上执行SCP命令
                self.scp_from_device(device_folder)

                host_folder = self.host_desktop_path / self.device_serial
                self.log("系统", f"日志收集完成! 保存到: {host_folder}")
                self.close_nanocom()
            else:
                self.log("错误", "设备连接失败")

        except Exception as e:
            self.log("错误", f"脚本执行错误: {e}")

            # 确保关闭nanocom连接
            self.close_nanocom()


def main():

    # 创建日志记录器
    from utils.logger import UnifiedLogger
    logger = UnifiedLogger()

    collector = RebootLogCollector()
    collector.set_logger(logger)

    try:
        collector.main()
    finally:
        logger.close()


if __name__ == "__main__":
    main()
