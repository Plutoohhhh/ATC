import time
import re
import os
import shutil
import subprocess
import glob
import pexpect
from typing import Optional, List, Dict, Tuple
from pathlib import Path


class DeviceLogCollector:
    def __init__(self):
        self.serial_connection = None
        self.device_serial = None
        self.host_desktop_path = Path.home() / "Desktop"
        self.nanocom_process = None
        self.logger = None  # 改为使用统一的logger

    def set_logger(self, logger):
        """设置统一的日志记录器"""
        self.logger = logger

    def log(self, level, message):
        """使用统一的日志方法"""
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")

    def run_command(self, cmd: str, capture_output: bool = True) -> Optional[str]:
        """Execute shell command and return output"""
        try:
            if capture_output:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, check=True
                )
                return result.stdout.strip()
            subprocess.run(cmd, shell=True, check=True)
            return None
        except subprocess.CalledProcessError as e:
            self.log("错误", f"命令执行错误: {cmd}")
            self.log("错误", f"错误详情: {e}")
            return None

    def get_host_serial_number(self) -> Optional[str]:
        """Get host serial number"""
        self.log("程序输出", "正在获取主机序列号...")
        sp_hardware_data = "/usr/sbin/system_profiler SPHardwareDataType"
        serial_output = self.run_command(sp_hardware_data)

        if serial_output:
            for line in serial_output.split("\n"):
                if "Serial" in line and len(line.split()) >= 4:
                    serial_num = line.split()[3]
                    self.log("程序输出", f"获取到主机序列号: {serial_num}")
                    return serial_num
        self.log("警告", "无法获取主机序列号，使用默认名称")
        return None

    def find_nanocom_ports(self) -> Optional:
        """Find available serial ports, specifically identifying those with -ch-0"""
        self.log("程序输出", "正在扫描可用的串行端口...")

        nanocom_output = self.run_command("nanocom -y")
        if not nanocom_output:
            self.log("错误", "无法获取 nanocom 输出")
            return None

        self.log("系统输出", "nanocom -y 输出:")
        self.log("系统输出", nanocom_output)

        # Use regex to match serial ports, specifically focusing on those with -ch-0
        pattern = r"Serial device \((\d+)\)\s*:\s*/dev/cu\.chimp-(\S+-ch-0)"
        matches = re.findall(pattern, nanocom_output)

        if not matches:
            self.log("错误", "未找到带有 '-ch-0' 的设备")
            return None

        # Extract the first matching device number
        port = matches[0][0]
        self.log("程序输出", f"找到端口: {port}")
        return port

    def auto_login_via_nanocom(self) -> bool:
        """Automatically connect and log in to device via nanocom"""
        self.log("程序输出", "开始通过 nanocom 自动连接设备...")

        port = self.find_nanocom_ports()
        if port is None:
            self.log("错误", "未找到合适的端口")
            return False

        try:
            self.log("程序输出", f"启动 nanocom 并选择设备 {port}...")
            self.nanocom_process = pexpect.spawn("nanocom -y")

            # Wait for nanocom to start and display device list
            self.nanocom_process.expect("Serial device", timeout=10)

            # Enter device number
            self.nanocom_process.sendline(str(port))
            self.nanocom_process.sendline('')

            # Wait for login prompt
            login_timeout = 30
            start_time = time.time()

            while time.time() - start_time < login_timeout:
                expect_result = self.nanocom_process.expect(
                    [pexpect.TIMEOUT, "login:", "local@locals-Mac", "%", "#"], timeout=2
                )

                if expect_result == 1:  # Detected login prompt
                    self.log("程序输出", "检测到登录提示，输入用户名...")
                    self.nanocom_process.sendline("local")
                    self.nanocom_process.sendline("")
                    time.sleep(2)

                    # Check if password is needed
                    auth_result = self.nanocom_process.expect(
                        [pexpect.TIMEOUT, "Password:", "password:", "local@locals-Mac", "%", "#"],
                        timeout=5
                    )
                    if auth_result in [1, 2]:
                        self.log("程序输出", "输入密码...")
                        self.nanocom_process.sendline("local")
                        time.sleep(2)

                    # Verify login success
                    if self.nanocom_process.expect([pexpect.TIMEOUT, "local@locals-Mac", "%", "#"], timeout=5) >= 1:
                        self.log("程序输出", "登录成功!")
                        return True

                time.sleep(1)

            self.log("错误", "登录超时或失败")
            return False

        except pexpect.ExceptionPexpect as e:
            self.log("错误", f"nanocom 连接失败: {e}")
            return False

    def send_nanocom_command(self, command: str, wait_time: float = 2.0) -> str:
        """Send command via nanocom"""
        if not self.nanocom_process:
            return ""

        try:
            # Send command
            self.log("命令输入", f"发送命令: {command}")
            self.nanocom_process.sendline(command)
            time.sleep(wait_time)

            # Get response
            response = ""
            try:
                while True:
                    # Read output in non-blocking way
                    if self.nanocom_process.expect([pexpect.TIMEOUT, pexpect.EOF, "."], timeout=0.1) == 2:
                        response += self.nanocom_process.before + self.nanocom_process.after
            except (pexpect.TIMEOUT, pexpect.EOF):
                pass

            if response.strip():
                self.log("系统输出", f"命令响应: {response}")

            return response

        except Exception as e:
            self.log("错误", f"发送命令失败: {e}")
            return ""

    def execute_on_device_via_nanocom(self, command: str, description: str = "") -> str:
        """Execute command on device via nanocom"""
        self.log("程序输出", f"执行命令: {description or command}")
        response = self.send_nanocom_command(command, wait_time=3.0)
        if response:
            self.log("程序输出", f"命令输出 (前200字符): {response[:200]}...")
        return response

    def collect_host_logs(self, destination_path: str):
        """Collect host logs"""
        self.log("程序输出", "开始收集主机日志...")

        # Log path definitions
        log_paths = {
            "kernel_panics": "/private/var/tmp/kernel_panics",
            "sys_tmp": "/private/var/tmp",
            "crash_reporter": "/Library/logs/CrashReporter/CoreCapture",
            "burnin": "/Users/local/Library/Logs/Astro/@osdiags/factory/burnin.astro",
            "burnin_offline": "/Users/local/Library/Logs/Astro/@osdiags/factory/burnin_offline.astro",
            "os_logs": "/FactoryLogs/"
        }

        dest_path = Path(destination_path)

        # Get astro status
        self.log("程序输出", "获取 astro 状态...")
        astro_output = self.run_command("astro status")
        if astro_output:
            (dest_path / "astro_status.txt").write_text(astro_output, encoding="utf-8")
            self.log("程序输出", "astro 状态已保存")

        # Copy various log files
        for log_name, log_path in log_paths.items():
            src_path = Path(log_path)
            if not src_path.exists():
                self.log("警告", f"日志路径不存在: {log_path}")
                continue

            try:
                target_path = dest_path / log_name
                if src_path.is_dir():
                    if target_path.exists():
                        shutil.rmtree(target_path)
                    shutil.copytree(src_path, target_path)
                    self.log("程序输出", f"已复制目录: {log_path} -> {target_path}")
                else:
                    shutil.copy2(src_path, target_path)
                    self.log("程序输出", f"已复制文件: {log_path} -> {target_path}")
            except Exception as e:
                self.log("错误", f"复制 {log_path} 失败: {e}")

        # Run sysdiagnose
        try:
            self.log("程序输出", "运行 sysdiagnose...")
            subprocess.run(
                "echo '\n' | sudo sysdiagnose",
                shell=True,
                check=True,
                timeout=300
            )
            self.log("程序输出", "sysdiagnose 完成")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self.log("错误", f"运行 sysdiagnose 失败: {e}")

        # Copy the latest sysdiagnose file
        try:
            tmp_path = Path("/private/var/tmp")
            tar_files = list(tmp_path.glob("sysdiagnose*.tar.gz"))
            if tar_files:
                # Sort by modification time, newest first
                tar_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest_tar = tar_files[0]
                shutil.copy2(latest_tar, dest_path / latest_tar.name)
                self.log("程序输出", f"已复制 sysdiagnose 文件: {latest_tar.name}")
        except Exception as e:
            self.log("错误", f"复制 sysdiagnose 文件失败: {e}")

    def main(self):
        """Main function"""
        self.log("系统", "=== 设备日志自动收集脚本 ===")

        # Get host serial number and create directory
        host_serial = self.get_host_serial_number() or "unknown_device"
        if host_serial == "unknown_device":
            self.log("警告", "无法获取主机序列号，使用默认名称")

        destination_path = self.host_desktop_path / host_serial
        destination_path.mkdir(parents=True, exist_ok=True)
        self.log("系统", f"日志将保存到: {destination_path}")

        try:
            if self.auto_login_via_nanocom():
                self.collect_host_logs(str(destination_path))
            else:
                self.log("错误", "设备连接失败")

            self.log("系统", f"\n日志收集完成! 所有日志已保存到: {destination_path}")

        except Exception as e:
            self.log("错误", f"脚本执行错误: {e}")

        finally:
            # Close nanocom process
            if self.nanocom_process and self.nanocom_process.isalive():
                try:
                    self.nanocom_process.sendcontrol("a")
                    self.nanocom_process.sendcontrol("x")
                    self.nanocom_process.close()
                    self.log("程序输出", "nanocom 连接已关闭")
                except Exception:
                    pass


def main():
    # Check if pexpect is installed
    try:
        import pexpect
    except ImportError:
        print("错误: 需要 pexpect 模块")
        print("请运行: pip install pexpect")
        return

    collector = DeviceLogCollector()
    collector.main()


if __name__ == "__main__":
    main()