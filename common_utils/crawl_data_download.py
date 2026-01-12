import subprocess
import concurrent.futures
from functools import partial
from datetime import datetime
import os
from pathlib import Path

def run_exe(executable_path, log_dir, input_var):
    """
    实时捕获可执行程序的输出，即时写入指定文件（支持传入输入变量）
    
    Args:
        executable_path (str): 可执行程序路径（如./my_program）
        output_file_path (str): 输出日志文件路径
        input_var (str/None): 要传入程序的输入变量（None则不传入）
    """
    # 确保日志文件目录存在
    # log_dir = os.path.dirname(output_file_path)
    # if log_dir and not os.path.exists(log_dir):
    #     os.makedirs(log_dir)
    log_path = Path(log_dir) / f"{input_var}.log"
    # print(log_path)

    try:
        # 启动子进程，设置管道为非阻塞实时读取
        process = subprocess.Popen(
            executable_path,
            stdin=subprocess.PIPE if input_var else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 将stderr合并到stdout，统一捕获
            text=True,
            bufsize=1,  # 无缓冲，实时输出
            universal_newlines=True
        )

        # 写入输入变量（如果有）
        if input_var:
            process.stdin.write(input_var + "\n")
            process.stdin.flush()
            process.stdin.close()  # 关闭输入流，避免程序等待输入

        # 打开日志文件（追加模式，避免覆盖）
        with open(log_path, "a", encoding="utf-8") as log_file:
            # 写入执行头部信息，方便区分不同次执行
            log_file.write(f"\n===== 执行开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n")
            log_file.write(f"执行程序: {executable_path}\n")
            if input_var:
                log_file.write(f"传入输入: {input_var}\n")
            log_file.write("----------------------------------------\n")

            # 实时读取并写入输出
            while True:
                # 逐行读取输出（实时）
                output_line = process.stdout.readline()
                if not output_line and process.poll() is not None:
                    break  # 无输出且进程已结束，退出循环

                if output_line:
                    # 同时输出到控制台和文件
                    # print(output_line.strip())
                    log_file.write(output_line)
                    log_file.flush()  # 强制刷盘，确保即时写入

            # 写入执行尾部信息
            log_file.write("----------------------------------------\n")
            log_file.write(f"执行结束: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"程序返回码: {process.returncode}\n")
            log_file.write(f"===== 执行结束 =====\n")

        print(f"\n程序执行完成，所有输出已实时写入文件: {os.path.abspath(log_path)}")

    except FileNotFoundError:
        error_msg = f"错误：找不到可执行程序 {executable_path}，请检查路径/权限"
        print(error_msg)
        # 即使程序找不到，也记录错误到日志
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n【错误】{datetime.now()}: {error_msg}\n")
    except Exception as e:
        error_msg = f"执行异常: {str(e)}"
        print(error_msg)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n【异常】{datetime.now()}: {error_msg}\n")

# 示例调用
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe_path", type=str, default="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/代码/gpt导出工具-导出单文件_主节点_linux")
    parser.add_argument("--save_dir", type=str, required=True)
    parser.add_argument("--task_name", type=str, required=True)
    args = parser.parse_args()
    log_dir = args.save_dir + "/logs/"
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    os.chdir(args.save_dir)
    run_exe(args.exe_path, log_dir, args.task_name)