import pexpect
import sys
import re
import time
import os
import os.path

# --- 配置区: 请根据你的需求修改 ---

# 1. 要执行的命令列表
COMMANDS_TO_RUN = [
    "pwd",
    "ls",
    "date"
    # 在这里添加更多你需要的命令...
]

# 2. 登录凭据 (如果不需要登录, 保持为 None)
USERNAME = 'localll'
PASSWORD = 'local'

# 3. [重要] 机台的 OS 模式提示符 (来自你的 Chimp_serial.txt 日志)
#    这是脚本用来识别“机台已在 OS 模式”的唯一信号
TARGET_PROMPT_STRING = "local@locals-Mac ~ %"
TARGET_PROMPT_REGEX = re.escape(TARGET_PROMPT_STRING)

# 4. 日志文件名 (脚本会自动将其放在桌面上)
LOG_FILE_NAME = "nanocom_session_full.log"

# 5. 超时设置 (秒)
TIMEOUT = 15


# --- 脚本主逻辑 ---

def find_port_number(output_before):
    """
    动态查找 C-line 或 S-line 端口。
    """

    # 策略 1: 尝试查找 C-line 端口 (如 Chimp_serial.txt)
    c_line_match = re.search(r'Serial device \((\d+)\)\s*:\s*(\S+-ch-0)', output_before)
    if c_line_match:
        port_number = c_line_match.group(1)
        port_path = c_line_match.group(2)
        print(f"\n--- 自动找到 C-line 端口: {port_number} ({port_path}) ---")
        return port_number

    # 策略 2: 尝试查找 S-line "base" 端口
    print(f"\n--- 未找到 C-line (-ch-0) 端口, 尝试 S-line 'base' 端口逻辑 ---")

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
            print(f"--- 自动找到 S-line 'base' 端口: {number} ({path}) ---")
            return number

    return None


def main():
    try:
        desktop_path = os.path.expanduser("~/Desktop")
        os.makedirs(desktop_path, exist_ok=True)
        full_log_path = os.path.join(desktop_path, LOG_FILE_NAME)
    except Exception as e:
        print(f"--- 严重错误: 无法获取桌面路径。 {e} ---")
        return

    shell_prompt = f"{os.getlogin()}@localhost % "
    command_to_run = "nanocom -y"

    try:
        with open(full_log_path, 'wb') as logfile:

            # 1. 写入模拟的启动命令
            logfile.write(f"{shell_prompt}{command_to_run}\n".encode('utf-8'))
            logfile.flush()

            print(f"--- 自动化脚本启动 ---")
            print(f"--- 目标 OS 提示符已设为: '{TARGET_PROMPT_STRING}' ---")
            print(f"--- 完整会话日志将保存到: {full_log_path} ---")

            # 2. 启动 nanocom 进程
            child = pexpect.spawn(command_to_run, timeout=TIMEOUT)

            # 3. 将所有 nanocom 的输入输出 100% 写入日志
            child.logfile = logfile

            # 4. 动态端口选择
            print(f"\n--- 正在等待 nanocom 加载设备列表... ---")
            try:
                child.expect(r'Select a device by its number')
            except (pexpect.exceptions.TIMEOUT, pexpect.exceptions.EOF) as e:
                print(f"\n--- 错误: 启动 nanocom 后未找到 'Select a device' 提示 ---")
                return

            output_before = child.before.decode('utf-8', 'ignore')
            port_number = find_port_number(output_before)

            if not port_number:
                print(f"\n--- 错误: 没有找到可用端口 (C-line 或 S-line) ---")
                child.terminate()
                return

            print(f"--- 最终选择端口: {port_number} ---")
            child.sendline(port_number)

            # --- 步骤 5: [关键修正] 发送回车并检测系统状态 ---

            print(f"\n--- 端口已连接, 正在发送 'Enter' 键以唤醒提示符... ---")
            child.sendline("")  # 发送一个空行 (回车)

            print("--- 正在检测机台状态 (OS, Login, Diags, Recovery, or Booting)... ---")

            # 0: TARGET_PROMPT_REGEX (OS Mode)
            # 1: login: or username: (Login needed)
            # 2: password: (Password only needed)
            # 3: :) (Diags Mode)
            # 4: ] (Recovery Mode)
            # 5: pexpect.TIMEOUT (Unknown/Booting)
            # 6: pexpect.EOF (Crashed)

            index = child.expect([
                TARGET_PROMPT_REGEX,  # 索引 0 (OS Mode)
                r'(?i)login:|(?i)username:',  # 索引 1 (Login needed)
                r'(?i)password:',  # 索引 2 (Password only)
                re.escape(":)"),  # 索引 3 (Diags)
                re.escape("]"),  # 索引 4 (Recovery)
                pexpect.TIMEOUT,  # 索引 5 (Booting/Unknown)
                pexpect.EOF  # 索引 6 (Crashed)
            ])

            if index == 0:  # 匹配到机台提示符 (OS Mode)
                print(f"--- 状态: OS 模式 (检测到 '{TARGET_PROMPT_STRING}') ---")
                print("--- 无需登录, 准备执行命令 ---")
                # 成功, 继续执行步骤 6

            elif index == 1:  # login/username
                if not USERNAME or not PASSWORD:
                    print(f"--- 错误: 检测到登录提示, 但脚本中未配置 USERNAME/PASSWORD ---")
                    return  # 退出 main
                print("--- 状态: 需要登录。正在发送用户名 ---")
                child.sendline(USERNAME)
                child.expect(r'(?i)password:')
                print("--- 正在发送密码 ---")
                child.sendline(PASSWORD)
                child.expect(TARGET_PROMPT_REGEX)
                print(f"--- 登录成功, 已进入 OS 模式 ({TARGET_PROMPT_STRING}) ---")
                # 成功, 继续执行步骤 6

            elif index == 2:  # password only
                if not PASSWORD:
                    print(f"--- 错误: 检测到密码提示, 但脚本中未配置 PASSWORD ---")
                    return  # 退出 main
                print("--- 状态: 需要密码。正在发送密码 ---")
                child.sendline(PASSWORD)
                child.expect(TARGET_PROMPT_REGEX)
                print(f"--- 登录成功, 已进入 OS 模式 ({TARGET_PROMPT_STRING}) ---")
                # 成功, 继续执行步骤 6

            elif index == 3:  # Diags :)
                print(f"\n--- 错误: 检测到 Diags 模式 (':)') ---")
                print(f"--- 命令无法在此模式下执行, 脚本终止。 ---")
                return  # 退出 main, 不执行步骤 6

            elif index == 4:  # Recovery ]
                print(f"\n--- 错误: 检测到 Recovery 模式 (']') ---")
                print(f"--- 命令无法在此模式下执行, 脚本终止。 ---")
                return  # 退出 main, 不执行步骤 6

            elif index == 5:  # TIMEOUT
                print(f"\n--- 错误: 发送 'Enter' 后超时 ({TIMEOUT}秒) ---")
                print(f"--- 状态: 未知或正在 Booting (未收到任何已知提示符) ---")
                # print(f"--- 状态: 5S 后重试.....---")
                # time.sleep(5)
                # child.sendline('')
                # if child.expect(TARGET_PROMPT_REGEX):
                #     return
                return  # 退出 main, 不执行步骤 6

            elif index == 6:  # EOF
                print(f"\n--- 错误: 进程在检测状态时意外终止 (EOF) ---")
                return  # 退出 main, 不执行步骤 6

            # --- 步骤 6: 循环执行命令 (只有在状态 0, 1, 2 成功后才会到达这里) ---

            print("\n--- [状态] 机台已就绪, 正在开始执行命令... ---")

            for cmd in COMMANDS_TO_RUN:
                print(f"\n--- [状态] 正在发送命令到机台: {cmd} ---")
                child.sendline(cmd)

                # 等待机台返回 OS 提示符, 忽略所有噪音
                child.expect(TARGET_PROMPT_REGEX)

                print(f"--- [状态] 机台已执行完毕 (已收到提示符) ---")
                time.sleep(0.5)

            print("\n--- 所有命令在机台执行完毕 ---")

    except (pexpect.exceptions.TIMEOUT, pexpect.exceptions.EOF) as e:
        print(f"\n--- 脚本执行期间发生严重错误 ---")
        print(f"--- 错误详情: {e} ---")
        print(f"--- 请检查 {full_log_path} 获取最后记录的日志 ---")
    except Exception as e:
        print(f"\n--- 发生意外的 Python 错误 ---")
        print(f"--- 错误详情: {e} ---")
    finally:
        if 'child' in locals() and 'full_log_path' in locals() and child.isalive():
            child.terminate()
            print(f"--- 会话已终止，完整原始日志保存在 {full_log_path} ---")
        elif 'full_log_path' in locals():
            print(f"--- 脚本结束，完整原始日志保存在 {full_log_path} ---")


if __name__ == "__main__":
    main()