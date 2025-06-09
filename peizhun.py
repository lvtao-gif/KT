#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程序启动辅助脚本（带进度条版本）
用于选择文件夹并启动 img_reg 项目的评估程序
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import platform
import threading
import time
import queue

class ProgressWindow:
    """进度条窗口类"""
    
    def __init__(self, title="程序执行中"):
        self.root = tk.Toplevel()
        self.root.title(title)
        self.root.geometry("500x200")
        self.root.resizable(False, False)
        
        # 设置窗口居中
        self.center_window()
        
        # 设置窗口属性
        self.root.attributes('-topmost', True)  # 保持在最前面
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 创建界面元素
        self.setup_ui()
        
        # 控制变量
        self.cancelled = False
        self.process = None
        
    def center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 状态标签
        self.status_label = ttk.Label(
            main_frame, 
            text="正在初始化...", 
            font=("Arial", 10)
        )
        self.status_label.pack(pady=(0, 10))
        
        # 进度条
        self.progress = ttk.Progressbar(
            main_frame, 
            mode='indeterminate',
            length=400
        )
        self.progress.pack(pady=(0, 15))
        
        # 详细状态标签
        self.detail_label = ttk.Label(
            main_frame, 
            text="", 
            font=("Arial", 9),
            foreground="gray"
        )
        self.detail_label.pack(pady=(0, 15))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # 取消按钮
        self.cancel_button = ttk.Button(
            button_frame, 
            text="取消", 
            command=self.on_cancel
        )
        self.cancel_button.pack(side=tk.RIGHT)
        
        # 开始进度条动画
        self.progress.start(10)
        
    def update_status(self, status, detail=""):
        """更新状态信息"""
        self.status_label.config(text=status)
        self.detail_label.config(text=detail)
        self.root.update()
        
    def on_cancel(self):
        """取消按钮点击事件"""
        if messagebox.askyesno("确认取消", "确定要取消程序执行吗？"):
            self.cancelled = True
            if self.process:
                try:
                    self.process.terminate()
                    print("用户取消了程序执行")
                except:
                    pass
                    
    def on_close(self):
        """窗口关闭事件"""
        self.on_cancel()
        
    def close(self):
        """关闭窗口"""
        self.progress.stop()
        self.root.destroy()

def select_folder():
    """
    弹出文件夹选择对话框
    返回: 选择的文件夹路径，如果取消则返回None
    """
    # 创建一个隐藏的根窗口
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 弹出文件夹选择对话框
    folder_path = filedialog.askdirectory(
        title="请选择img_reg项目文件夹",
        initialdir=os.getcwd()  # 从当前目录开始
    )
    
    root.destroy()  # 销毁窗口
    
    return folder_path if folder_path else None

def check_conda_environment():
    """
    检查conda是否可用
    """
    try:
        result = subprocess.run(['conda', '--version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def run_evaluation_thread(project_path, progress_window, result_queue):
    """
    在线程中运行评估程序
    
    Args:
        project_path: img_reg项目的根目录路径
        progress_window: 进度条窗口对象
        result_queue: 结果队列
    """
    try:
        # 更新状态
        progress_window.update_status("检查环境...", "验证conda环境和项目文件")
        
        # 检查路径是否存在
        if not os.path.exists(project_path):
            result_queue.put(("error", f"路径不存在: {project_path}"))
            return
            
        # 检查是否存在evaluate/evaluate.py文件
        evaluate_script = os.path.join(project_path, "evaluate", "evaluate.py")
        if not os.path.exists(evaluate_script):
            result_queue.put(("error", f"未找到评估脚本: {evaluate_script}"))
            return
        
        # 检查conda是否可用
        if not check_conda_environment():
            result_queue.put(("error", "未找到conda命令，请确保Anaconda/Miniconda已正确安装并配置环境变量"))
            return
        
        if progress_window.cancelled:
            return
            
        # 更新状态
        progress_window.update_status("激活conda环境...", "激活 img_reg 环境")
        
        print(f"切换到项目目录: {project_path}")
        print("激活conda环境: img_reg")
        print("运行评估程序...")
        
        # 构建命令
        if platform.system() == "Windows":
            # Windows系统使用cmd
            cmd = f'''
            cd /d "{project_path}" && 
            conda activate img_reg && 
            python evaluate/evaluate.py --dataset "{project_path}"
            '''
            
            # 在Windows上使用cmd运行
            process = subprocess.Popen(
                cmd,
                shell=True,
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
        else:
            # Linux/macOS系统使用bash
            cmd = f'''
            source $(conda info --base)/etc/profile.d/conda.sh &&
            conda activate img_reg &&
            cd "{project_path}" &&
            python evaluate/evaluate.py --dataset "{project_path}"
            '''
            
            process = subprocess.Popen(
                cmd,
                shell=True,
                executable='/bin/bash',
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
        
        # 保存进程引用以便取消
        progress_window.process = process
        
        if progress_window.cancelled:
            process.terminate()
            return
            
        # 更新状态
        progress_window.update_status("正在执行评估程序...", f"python evaluate/evaluate.py --dataset \"{project_path}\"")
        
        # 实时输出结果
        print("=" * 50)
        print("程序输出:")
        print("=" * 50)
        
        output_lines = []
        
        # 实时读取输出
        while True:
            if progress_window.cancelled:
                process.terminate()
                result_queue.put(("cancelled", "用户取消了程序执行"))
                return
                
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                line = output.strip()
                print(line)
                output_lines.append(line)
                
                # 更新进度窗口的详细信息（显示最后一行输出）
                if line:
                    # 限制显示长度
                    display_line = line[:80] + "..." if len(line) > 80 else line
                    progress_window.update_status("正在执行评估程序...", display_line)
        
        # 获取剩余输出和错误信息
        stdout, stderr = process.communicate()
        
        if stdout:
            print(stdout)
            output_lines.extend(stdout.strip().split('\n'))
        
        if stderr:
            print("错误信息:")
            print(stderr)
        
        # 检查返回码
        if process.returncode == 0:
            print("=" * 50)
            print("程序执行完成!")
            result_queue.put(("success", "评估程序执行完成!", output_lines))
        else:
            print(f"程序执行失败，返回码: {process.returncode}")
            result_queue.put(("error", f"程序执行失败，返回码: {process.returncode}\n请查看控制台输出获取详细信息"))
            
    except subprocess.TimeoutExpired:
        result_queue.put(("error", "程序执行超时"))
    except Exception as e:
        result_queue.put(("error", f"执行过程中出现异常: {str(e)}"))

def run_evaluation(project_path):
    """
    在指定路径下运行评估程序（带进度条）
    
    Args:
        project_path: img_reg项目的根目录路径
    """
    # 创建进度窗口
    progress_window = ProgressWindow("执行评估程序")
    
    # 创建结果队列
    result_queue = queue.Queue()
    
    # 启动执行线程
    thread = threading.Thread(
        target=run_evaluation_thread, 
        args=(project_path, progress_window, result_queue),
        daemon=True
    )
    thread.start()
    
    # 等待结果
    while thread.is_alive():
        progress_window.root.update()
        time.sleep(0.1)
        
        # 检查是否有结果
        try:
            result = result_queue.get_nowait()
            break
        except queue.Empty:
            continue
    else:
        # 线程结束，获取结果
        try:
            result = result_queue.get_nowait()
        except queue.Empty:
            result = ("error", "程序执行异常结束")
    
    # 关闭进度窗口
    progress_window.close()
    
    # 处理结果
    result_type, message = result[0], result[1]
    
    if result_type == "success":
        messagebox.showinfo("成功", message)
        return True
    elif result_type == "cancelled":
        messagebox.showinfo("已取消", message)
        return False
    else:  # error
        messagebox.showerror("错误", message)
        return False

def main():
    """
    主函数
    """
    # 创建主窗口（隐藏）
    root = tk.Tk()
    root.withdraw()
    
    print("程序启动辅助脚本")
    print("=" * 30)
    
    try:
        # 选择文件夹
        print("请选择img_reg项目文件夹...")
        project_path = select_folder()
        
        if project_path is None:
            print("用户取消了文件夹选择")
            return
        
        print(f"选择的项目路径: {project_path}")
        
        # 确认执行
        confirm = messagebox.askyesno(
            "确认执行", 
            f"将在以下路径执行评估程序:\n{project_path}\n\n"
            f"执行命令:\n"
            f"conda activate img_reg\n"
            f"cd {project_path}\n"
            f"python evaluate/evaluate.py --dataset \"{project_path}\"\n\n"
            f"是否继续?"
        )
        
        if not confirm:
            print("用户取消执行")
            return
        
        # 运行评估程序
        success = run_evaluation(project_path)
        
        if success:
            print("脚本执行完成!")
        else:
            print("脚本执行失败或被取消!")
            
    finally:
        root.destroy()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        print(f"程序异常: {str(e)}")
        messagebox.showerror("程序异常", f"程序运行过程中出现异常:\n{str(e)}")
    finally:
        input("按Enter键退出...")
