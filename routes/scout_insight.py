import pexpect
import re
import time
import os
from typing import Optional, List, Tuple
from pathlib import Path


class ScoutAutomation:
    def __init__(self, logger=None):
        self.logger = logger
        self.terminal_logger = None
        self.child = None
        if logger:
            self.terminal_logger = logger.get_terminal_logger()

    def set_logger(self, logger):
        """设置统一的日志记录器"""
        self.logger = logger
        if logger:
            self.terminal_logger = logger.get_terminal_logger()

    def log(self, level, message):
        """统一的日志记录方法"""
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

    def expect_with_logging(self, patterns, timeout=None):
        """带日志记录的expect方法"""
        self.log_terminal_expect(patterns)
        try:
            result = self.child.expect(patterns, timeout=timeout)

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

    def start_scout_session(self, sn: str, station: str, user_path: str):
        """启动scout会话并执行命令"""
        try:
            # 构建scout命令
            scout_cmd = f"scout insight --sn='{sn}' --station='{station}' --download_log --user_path='{user_path}'"
            self.log("程序输出", f"执行命令: {scout_cmd}")

            # 启动scout进程
            self.child = pexpect.spawn('/bin/bash', ['-c', scout_cmd], encoding='utf-8', timeout=60)

            # 设置终端日志记录
            if self.terminal_logger:
                self.child.logfile_read = self.terminal_logger.log_file
                self.child.logfile_send = self.terminal_logger.log_file

            return True

        except Exception as e:
            self.log("错误", f"启动scout会话失败: {e}")
            return False

    def wait_for_authentication(self):
        """等待认证完成"""
        try:
            # 等待认证阶段完成
            auth_patterns = [
                r'Authenticating user access',
                r'Get unit.*station.*log from Insight',
                r'Please select file \(\d+ - \d+\):'
            ]

            for pattern in auth_patterns:
                self.expect_with_logging(pattern, timeout=30)
                self.log("程序输出", f"检测到: {self.child.after}")

            return True

        except pexpect.TIMEOUT:
            self.log("错误", "认证阶段超时")
            return False
        except Exception as e:
            self.log("错误", f"认证过程中出错: {e}")
            return False

    def parse_file_options(self) -> List[Tuple[int, str, str]]:
        """解析文件选项并返回选项列表"""
        options = []

        try:
            # 获取所有输出
            output = self.child.before + self.child.after

            # 使用正则表达式匹配文件选项
            pattern = r'(\d+):\s+([^\s]+)_(\d+-\d+)[^\s]*\s+\([^)]+\)'
            matches = re.findall(pattern, output)

            for match in matches:
                index = int(match[0])
                filename_prefix = match[1]
                timestamp = match[2]
                options.append((index, filename_prefix, timestamp))
                self.log("程序输出", f"找到选项 {index}: {filename_prefix}_{timestamp}")

            return options

        except Exception as e:
            self.log("错误", f"解析文件选项失败: {e}")
            return []

    def select_file_by_timestamp(self, target_timestamp: str) -> bool:
        """根据时间戳选择文件"""
        try:
            # 首先解析所有可用选项
            options = self.parse_file_options()

            if not options:
                self.log("错误", "未找到任何文件选项")
                return False

            # 查找匹配时间戳的选项
            matching_option = None
            for index, prefix, timestamp in options:
                if target_timestamp in timestamp:
                    matching_option = index
                    break

            if matching_option is None:
                self.log("错误", f"未找到匹配时间戳 {target_timestamp} 的文件")
                # 列出所有可用的时间戳
                available_timestamps = [ts for _, _, ts in options]
                self.log("错误", f"可用时间戳: {available_timestamps}")
                return False

            # 发送选择
            self.log("程序输出", f"选择选项 {matching_option}")
            self.sendline_with_logging(str(matching_option))

            return True

        except Exception as e:
            self.log("错误", f"选择文件失败: {e}")
            return False

    def wait_for_completion(self, timeout=60) -> bool:
        """等待下载完成"""
        try:
            # 等待完成消息
            completion_patterns = [
                r'saved in',
                r'Done',
                r'下载完成',  # 如果有中文提示
                pexpect.EOF  # 进程结束
            ]

            result_index = self.expect_with_logging(completion_patterns, timeout=timeout)

            if result_index in [0, 1, 2]:
                self.log("程序输出", "文件下载成功完成")
                return True
            elif result_index == 3:
                self.log("程序输出", "进程正常结束")
                return True
            else:
                self.log("警告", "未检测到明确的完成消息")
                return False

        except pexpect.TIMEOUT:
            self.log("错误", "等待下载完成超时")
            return False
        except Exception as e:
            self.log("错误", f"等待完成过程中出错: {e}")
            return False

    def run_automated_download(self, sn: str, station: str, user_path: str, target_timestamp: str) -> bool:
        """运行自动下载流程"""
        self.log("系统", "开始自动化scout下载流程")

        try:
            # 1. 启动会话
            if not self.start_scout_session(sn, station, user_path):
                return False

            # 2. 等待认证
            if not self.wait_for_authentication():
                return False

            # 3. 选择文件
            if not self.select_file_by_timestamp(target_timestamp):
                return False

            # 4. 等待完成
            if not self.wait_for_completion():
                return False

            self.log("系统", "自动化scout下载流程成功完成")
            return True

        except Exception as e:
            self.log("错误", f"自动化流程失败: {e}")
            return False
        finally:
            # 清理资源
            if self.child and self.child.isalive():
                self.child.close()


# 使用示例和外部接口函数
def download_scout_log(sn: str, station: str, user_path: str, target_timestamp: str, logger=None) -> bool:
    """
    外部调用接口：下载指定时间戳的scout日志

    Args:
        sn: 设备序列号
        station: 站点名称
        user_path: 用户路径
        target_timestamp: 目标时间戳 (例如: "20250523-210217")
        logger: 统一的日志记录器

    Returns:
        bool: 下载是否成功
    """
    automation = ScoutAutomation(logger)
    return automation.run_automated_download(sn, station, user_path, target_timestamp)


# 批量处理函数
def batch_download_scout_logs(config_list: List[dict], logger=None) -> dict:
    """
    批量下载多个scout日志

    Args:
        config_list: 配置列表，每个元素包含sn, station, user_path, target_timestamp
        logger: 统一的日志记录器

    Returns:
        dict: 结果统计
    """
    results = {
        'total': len(config_list),
        'success': 0,
        'failed': 0,
        'details': []
    }

    for i, config in enumerate(config_list, 1):
        if logger:
            logger.log("系统", f"处理第 {i}/{len(config_list)} 个任务: SN={config['sn']}")

        success = download_scout_log(
            sn=config['sn'],
            station=config['station'],
            user_path=config['user_path'],
            target_timestamp=config['target_timestamp'],
            logger=logger
        )

        result_detail = {
            'sn': config['sn'],
            'timestamp': config['target_timestamp'],
            'success': success
        }

        if success:
            results['success'] += 1
        else:
            results['failed'] += 1

        results['details'].append(result_detail)

    return results