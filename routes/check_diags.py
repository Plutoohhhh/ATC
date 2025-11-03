#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pexpect
import sys
import re
import time
import argparse


class SimpleDiagsChecker:
    def __init__(self, device_num=None, timeout=30, verbose=False, spartan_modem_name=None):
        self.child = None
        self.device_num = device_num
        self.timeout = timeout
        self.verbose = verbose
        self.spartan_modem_name = spartan_modem_name
        self.initial_output = ""
        self.logger = None  # 添加统一的logger

    def set_logger(self, logger):
        """设置统一的日志记录器"""
        self.logger = logger

    def log(self, level, message, show_always=True):
        """统一的日志方法"""
        if self.logger:
            self.logger.log(level, message)
        elif show_always or self.verbose:
            print(f"[{level}] {message}")

    def find_target_device(self, output):
        """查找目标设备编号"""
        # 检查是否提供了 SpartanModemName
        if self.spartan_modem_name:
            # 转义特殊字符，确保安全匹配
            escaped_name = re.escape(self.spartan_modem_name)
            # 构建匹配模式：Serial device (编号) : <SpartanModemName>
            pattern = rf'Serial device \((\d+)\) : {escaped_name}'
            matches = re.findall(pattern, output)
            if matches:
                return matches[0]
        return None

    def connect_device(self):
        """连接设备 - 修复版"""
        try:
            self.log("系统输出", "连接设备...", False)

            self.child = pexpect.spawn('nanocom -y', timeout=self.timeout)

            # 等待设备列表
            index = self.child.expect(['Select a device by its number', pexpect.TIMEOUT])
            if index == 1:
                self.log("错误", "设备连接超时")
                return False

            output = self.child.before.decode('utf-8', errors='ignore')

            # 选择设备
            if self.device_num:
                device_num = self.device_num
            else:
                device_num = self.find_target_device(output)
                if not device_num:
                    self.log("错误", "未找到合适设备，请指定设备编号或设置SpartanModemName")
                    return False

            self.log("系统输出", f"选择设备: {device_num}", False)

            self.child.sendline(str(device_num))

            # 等待连接确认
            try:
                self.child.expect(['Use Ctrl-\\] for menu', 'Device selected'], timeout=10)
            except pexpect.TIMEOUT:
                pass

            # 等待设备初始化（修复版）
            self.log("系统输出", "等待设备初始化...", False)

            # 收集初始输出 - 修复版
            initial_output = ""
            start_time = time.time()
            max_wait_time = 20

            while time.time() - start_time < max_wait_time:
                try:
                    # 使用一个不会匹配的模式来读取可用输出
                    self.child.expect(['__NEVER_MATCH__'], timeout=1)
                except pexpect.TIMEOUT:
                    # 超时是正常的，读取before中的内容
                    if hasattr(self.child, 'before') and self.child.before:
                        new_output = self.child.before.decode('utf-8', errors='ignore')
                        initial_output += new_output
                        # 如果看到提示符，可以提前结束等待
                        if ':-' in new_output:
                            self.log("系统输出", "检测到提示符，提前结束等待", False)
                            break
                except pexpect.EOF:
                    break
                except Exception as e:
                    self.log("错误", f"读取输出时出错: {e}", False)
                    break

                time.sleep(0.5)  # 减少sleep时间，提高响应性

            # 保存初始输出供后续检测使用
            self.initial_output = initial_output
            return True

        except Exception as e:
            self.log("错误", f"连接失败: {e}")
            return False

    def check_diags_mode(self):
        """检测diags模式 - 修复版"""
        if not self.child:
            return False

        self.log("程序输出", "检测diags模式...")

        # 首先检查初始输出
        if self.initial_output and ':-) ' in self.initial_output:
            self.log("系统输出", "初始输出中发现diags提示符", False)
            return True

        # 清空缓存输出 - 修复版
        try:
            self.child.expect(['__NEVER_MATCH__'], timeout=0.5)
        except pexpect.TIMEOUT:
            pass
        except Exception:
            pass

        # 测试多个命令
        test_commands = ['1', '2', '3', '4']
        diags_detected = False

        for cmd in test_commands:
            try:
                self.log("命令输入", f"测试命令: {cmd}", False)

                # 发送命令
                self.child.sendline(cmd)

                # 收集输出，等待适当时间 - 修复版
                output = ""
                start_time = time.time()
                max_wait_time = 3

                while time.time() - start_time < max_wait_time:
                    try:
                        self.child.expect(['__NEVER_MATCH__'], timeout=0.5)
                    except pexpect.TIMEOUT:
                        # 读取可用的输出
                        if hasattr(self.child, 'before') and self.child.before:
                            new_output = self.child.before.decode('utf-8', errors='ignore')
                            output += new_output
                    except pexpect.EOF:
                        break
                    except Exception as e:
                        self.log("错误", f"读取命令输出时出错: {e}", False)
                        break

                # 检查多种diags特征
                diags_indicators = []

                # 1. 检查带命令的提示符
                if f':-) {cmd}' in output:
                    diags_indicators.append(f'prompt_with_cmd_{cmd}')

                # 2. 检查一般提示符
                if ':-) ' in output or ':-)\n' in output:
                    diags_indicators.append('general_prompt')

                # 3. 检查时间戳格式提示符
                timestamp_pattern = r'\[[\dA-F]+:[\dA-F]+\]\s*:-\)'
                if re.search(timestamp_pattern, output):
                    diags_indicators.append('timestamp_prompt')

                if diags_indicators:
                    diags_detected = True
                    # 找到并显示关键行
                    for line in output.split('\n'):
                        if ':-) ' in line:
                            self.log("系统输出", f"发现: {line.strip()}", False)
                            break
                    break

                # 短暂延迟再测试下一个命令
                time.sleep(0.5)

            except Exception as e:
                self.log("错误", f"测试命令 {cmd} 异常: {e}", False)
                continue

        return diags_detected

    def close(self):
        """关闭连接"""
        if self.child:
            try:
                self.child.close()
            except:
                pass


def check_diags_status(spartan_modem_name=None, device_num=None, timeout=30, verbose=False, logger=None):
    """
    检测设备是否处于diags模式的主函数

    参数:
        spartan_modem_name: 调制解调器名称，用于自动选择设备
        device_num: 手动指定设备编号
        timeout: 连接超时时间（秒）
        verbose: 是否显示详细输出
        logger: 统一的日志记录器

    返回:
        dict: {
            'success': bool,      # 是否成功完成检测
            'is_diags': bool,     # 是否处于diags模式
            'error_message': str, # 错误信息（如果有）
            'device_num': int     # 使用的设备编号（如果成功）
        }
    """
    checker = SimpleDiagsChecker(
        device_num=device_num,
        timeout=timeout,
        verbose=verbose,
        spartan_modem_name=spartan_modem_name
    )

    # 设置统一的logger
    if logger:
        checker.set_logger(logger)

    result = {
        'success': False,
        'is_diags': False,
        'error_message': '',
        'device_num': device_num
    }

    try:
        # 连接设备
        if not checker.connect_device():
            result['error_message'] = '设备连接失败'
            return result

        # 检测diags模式
        is_diags = checker.check_diags_mode()

        result['success'] = True
        result['is_diags'] = is_diags

        if is_diags:
            if logger:
                logger.log("系统", "✅ 检测到diags模式")
            elif verbose:
                print("✅ 检测到diags模式")
        else:
            if logger:
                logger.log("系统", "❌ 未检测到diags模式")
            elif verbose:
                print("❌ 未检测到diags模式")

        return result

    except KeyboardInterrupt:
        result['error_message'] = '用户中断'
        return result
    except Exception as e:
        result['error_message'] = f'程序错误: {e}'
        return result
    finally:
        checker.close()


def check_diags_and_return_status(spartan_name, logger=None):
    """带重试的diags检测函数，兼容统一日志系统"""
    max_retries = 3
    retry_delay = 5  # 重试间隔时间（秒）

    for attempt in range(max_retries):
        if logger:
            logger.log("系统", f"正在进行第 {attempt + 1} 次检测...")
        else:
            print(f"正在进行第 {attempt + 1} 次检测...")

        # 调用检测函数
        result = check_diags_status(spartan_modem_name=spartan_name, verbose=True, logger=logger)

        # 如果检测成功且处于diags模式，直接返回True
        if result['success'] and result['is_diags']:
            if logger:
                logger.log("系统", "✅ 目标机器处于diags模式")
            else:
                print("✅ 目标机器处于diags模式")
            return True

        # 如果这不是最后一次尝试，显示失败信息并准备重试
        if attempt < max_retries - 1:
            if result['success']:
                if logger:
                    logger.log("系统", f"❌ 目标机器不在diags模式 (第 {attempt + 1} 次尝试)")
                else:
                    print(f"❌ 目标机器不在diags模式 (第 {attempt + 1} 次尝试)")
            else:
                if logger:
                    logger.log("系统",
                               f"❌ 检测失败: {result.get('error_message', '未知错误')} (第 {attempt + 1} 次尝试)")
                else:
                    print(f"❌ 检测失败: {result.get('error_message', '未知错误')} (第 {attempt + 1} 次尝试)")

            if logger:
                logger.log("系统", f"等待 {retry_delay} 秒后进行第 {attempt + 2} 次尝试...")
            else:
                print(f"等待 {retry_delay} 秒后进行第 {attempt + 2} 次尝试...")
            time.sleep(retry_delay)
        else:
            # 最后一次尝试失败，输出最终结果并直接返回
            if result['success']:
                if logger:
                    logger.log("系统", "❌ 目标机器不在diags模式 (所有尝试均失败)")
                else:
                    print("❌ 目标机器不在diags模式 (所有尝试均失败)")
            else:
                if logger:
                    logger.log("系统", f"❌ 检测失败: {result.get('error_message', '未知错误')} (所有尝试均失败)")
                else:
                    print(f"❌ 检测失败: {result.get('error_message', '未知错误')} (所有尝试均失败)")

            if logger:
                logger.log("系统", f"经过 {max_retries} 次尝试，检测均未成功")
            else:
                print(f"经过 {max_retries} 次尝试，检测均未成功")
            return False

    return False


def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description='Diags检测工具')
    parser.add_argument('-d', '--device', type=int, help='指定设备编号')
    parser.add_argument('-t', '--timeout', type=int, default=30, help='连接超时时间（秒）')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('-s', '--spartan-name', type=str, help='SpartanModemName用于自动选择设备')

    args = parser.parse_args()

    # 检查是否有全局的SpartanModemName变量（保持向后兼容）
    spartan_name = args.spartan_name
    if not spartan_name and 'SpartanModemName' in globals():
        spartan_name = globals()['SpartanModemName']

    result = check_diags_status(
        spartan_modem_name=spartan_name,
        device_num=args.device,
        timeout=args.timeout,
        verbose=args.verbose
    )

    if not result['success']:
        print(f"❌ {result['error_message']}")
        return 1

    if result['is_diags']:
        print("✅ 检测到diags模式")
        return 0
    else:
        print("❌ 未检测到diags模式")
        return 1


if __name__ == "__main__":
    try:
        import pexpect
    except ImportError:
        print("❌ 请先安装 pexpect: pip install pexpect")
        sys.exit(1)

    sys.exit(main())