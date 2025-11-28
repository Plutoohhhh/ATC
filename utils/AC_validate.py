import subprocess


class AC_vali():

    def __init__(self):
        self.logger = None

    def log(self, level, message):
        """统一的日志方法 - 使用UnifiedLogger"""
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")

    def check_AC(self):
        try:
            # 使用 subprocess 执行命令
            result = subprocess.run(
                ['/usr/local/bin/scout', 'insight --check_user_access'],
                capture_output=True,
                text=True,
                timeout=10
            )

            # 打印完整的输出用于调试
            self.log("调试", f"命令输出: {result.stdout}")
            if result.stderr:
                self.log("调试", f"错误输出: {result.stderr}")

            # 检查输出中是否包含 "Account"
            if "Account" in result.stdout:
                self.log("系统", "检测到AppleConnect账户已登录")
                print("True")
                return True
            else:
                self.log("错误", "——————请先登录AppleConnect账户！！——————")
                print("False")
                return False

        except subprocess.TimeoutExpired:
            self.log("错误", "命令执行超时")
            return False
        except Exception as e:
            self.log("错误", f"执行AppleConnect命令时发生异常: {e}")
            return False

    def check_Scout(self):
        try:
            # 使用 subprocess 执行命令
            result = subprocess.run(
                ['/usr/local/bin/AppleConnect', 'userList'],
                capture_output=True,
                text=True,
                timeout=10
            )

            # 打印完整的输出用于调试
            self.log("调试", f"命令输出: {result.stdout}")
            if result.stderr:
                self.log("调试", f"错误输出: {result.stderr}")

            # 检查输出中是否包含 "Account"
            if "Account" in result.stdout:
                self.log("系统", "检测到AppleConnect账户已登录")
                print("True")
                return True
            else:
                self.log("错误", "——————请先登录AppleConnect账户！！——————")
                print("False")
                return False

        except subprocess.TimeoutExpired:
            self.log("错误", "命令执行超时")
            return False
        except Exception as e:
            self.log("错误", f"执行AppleConnect命令时发生异常: {e}")
            return False



if __name__ == "__main__":
    instance = AC_vali()
    instance.check_AC()