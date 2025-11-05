import re
import time
import pexpect
from pathlib import Path


class RebootLogCollector:
    def __init__(self):
        self.host_desktop_path = Path.home() / "Desktop"
        self.child = None
        self.logger = None
        self.device_serial = None
        self.device_ip = None

    def set_logger(self, logger):
        self.logger = logger

    def log(self, level, message):
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")

    def get_device_serial_number(self) -> str:
        """获取设备序列号"""
        if not self.child:
            return "unknown_device"

        self.log("程序输出", "正在获取设备序列号...")
        self.child.sendline("system_profiler SPHardwareDataType | grep 'Serial Number' | awk '{print $4}'")
        self.child.expect("local@locals-Mac ~ %",timeout=5)
        response = self.child.before.decode()

        # 提取序列号
        lines = response.split('\n')
        for line in lines:
            if len(line.strip()) > 5 and not line.startswith("system_profiler"):
                serial = line.strip()
                self.log("程序输出", f"获取到设备序列号: {serial}")
                return serial

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
            expect_result = self.child.expect(
                [pexpect.TIMEOUT, "Select a device by its number"],
                timeout=5
            )

            if expect_result == 1:
                output_before = self.child.before.decode('utf-8', 'ignore')
                port = self.find_port_number(output_before)

                if port is None:
                    self.log("错误", "未找到可用的串口设备")
                    return False
                self.child.sendline(port)

            # 等待登录提示
            expect_result = self.child.expect(
                [pexpect.TIMEOUT, "login:", "local@locals-Mac ~ %"], timeout=30
            )

            if expect_result == 1:  # 检测到登录提示
                self.log("程序输出", "输入用户名...")
                self.child.sendline("local")

                # 检查是否需要密码
                auth_result = self.child.expect([pexpect.TIMEOUT, "Password:"], timeout=5)
                if auth_result == 1:
                    self.log("程序输出", "输入密码...")
                    self.child.sendline("local")

                # 验证登录成功
                if self.child.expect([pexpect.TIMEOUT, "local@locals-Mac ~ %"], timeout=60) == 1:
                    self.log("程序输出", "登录成功!")

                    # 获取设备序列号和IP地址
                    self.device_serial = self.get_device_serial_number()
                    return True

            self.log("错误", "登录失败")
            return False

        except Exception as e:
            self.log("错误", f"nanocom连接失败: {e}")
            return False

    def run_sysdiagnose(self) -> bool:
        """在设备上运行sysdiagnose命令"""
        self.log("程序输出", "开始在设备上运行sysdiagnose...")

        try:
            # 发送sudo sysdiagnose命令
            self.child.sendline("sudo sysdiagnose")

            # 等待密码提示或继续提示
            expect_result = self.child.expect(
                [pexpect.TIMEOUT, "Press 'Enter' to continue. Ctrl+\\ to cancel."],
                timeout=5
            )

            if expect_result == 1:  # 检测到继续提示
                self.log("程序输出", "按下Enter继续...")
                self.child.sendline("")  # 发送回车

                # 等待sysdiagnose完成
                self.log("程序输出", "等待sysdiagnose完成...")
                expect_result = self.child.expect(
                    [pexpect.TIMEOUT, "Output available at", "local@locals-Mac ~ %"],
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
            "kernel_panics": "/private/var/tmp/kernel_panics",
            "sys_tmp": "/private/var/tmp",
            "crash_reporter": "/Library/logs/CrashReporter/CoreCapture",
            "burnin": "/Users/local/Library/Logs/Astro/@osdiags/factory/burnin.astro",
            "os_logs": "/FactoryLogs/"
        }


        # 在设备上创建文件夹
        device_folder = f"/tmp/{self.device_serial}"
        self.log("程序输出", f"在设备上创建文件夹: {device_folder}")
        self.child.sendline(f"mkdir -p {device_folder}")
        self.child.expect("local@locals-Mac ~ %",timeout=5)

        # 复制文件到设备上的文件夹
        for log_name, device_path in log_paths.items():
            self.log("程序输出", f"复制: {device_path} 到 {device_folder}")

            # 检查设备上路径是否存在
            self.child.sendline(f"test -e {device_path} && echo 'EXISTS' || echo 'NOT_EXISTS'")
            self.child.expect("local@locals-Mac ~ %")
            response = self.child.before.decode()

            if "EXISTS" in response:
                # 复制文件或目录
                self.child.sendline(f"cp -r {device_path} {device_folder}/")
                self.child.expect("local@locals-Mac ~ %")
                self.log("程序输出", f"已复制: {device_path}")
            else:
                self.log("警告", f"路径不存在: {device_path}")

        return device_folder

    def close_nanocom(self):
        """关闭nanocom连接"""
        if self.child and self.child.isalive():
            try:
                self.child.sendcontrol("a")
                self.child.sendcontrol("x")
                self.child.close()
                self.log("程序输出", "nanocom连接已关闭")
            except:
                pass

    def scp_from_device(self, device_folder: str):
        """在主机上执行SCP命令从设备复制文件夹"""
        # 在主机上创建目标文件夹
        host_folder = self.host_desktop_path / self.device_serial
        host_folder.mkdir(parents=True, exist_ok=True)

        # 通过scp将文件夹从设备复制到主机
        self.log("程序输出", "在主机上执行SCP命令...")
        scp_command = f"scp -r local@locals-Mac ~.local:{device_folder} {host_folder}"
        self.log("程序输出", f"执行SCP命令: {scp_command}")

        try:
            # 使用pexpect执行SCP命令并自动输入密码
            scp_child = pexpect.spawn(scp_command)
            scp_result = scp_child.expect(['Are you sure you want to continue connecting (yes/no/[fingerprint])?:', pexpect.TIMEOUT, pexpect.EOF], timeout=10)

            if scp_result == 0:
                scp_child.sendline("yes")
                scp_child.expect(pexpect.EOF, timeout=5)

                scp_child.expect("Password:", timeout=5)
                scp_child.sendline("local")
                self.log("程序输出", "开始SCP传输")

                scp_child.expect("local@locals-Mac ~ %", timeout=60)
                self.log("程序输出", "SCP传输完成")
            else:
                self.log("错误", "SCP传输失败或超时")

        except Exception as e:
            self.log("错误", f"SCP传输失败: {e}")

    def main(self):
        self.log("系统", "=== 设备日志自动收集脚本 ===")

        try:
            if self.auto_login_via_nanocom():
                # 在设备上运行sysdiagnose
                if self.run_sysdiagnose():
                    # 在设备上复制文件
                    device_folder = self.copy_files_on_device()

                    # 关闭nanocom连接
                    self.close_nanocom()

                    # 在主机上执行SCP命令
                    self.scp_from_device(device_folder)

                    host_folder = self.host_desktop_path / self.device_serial
                    self.log("系统", f"日志收集完成! 保存到: {host_folder}")
                else:
                    self.log("错误", "sysdiagnose执行失败")
            else:
                self.log("错误", "设备连接失败")

        except Exception as e:
            self.log("错误", f"脚本执行错误: {e}")

            # 确保关闭nanocom连接
            self.close_nanocom()


def main():
    try:
        import pexpect
    except ImportError:
        print("错误: 需要 pexpect 模块")
        print("请运行: pip install pexpect")
        return

    collector = RebootLogCollector()
    collector.main()


if __name__ == "__main__":
    main()