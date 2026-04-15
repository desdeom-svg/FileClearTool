"""
主程序入口：
- 启动 CustomTkinter GUI
- 启动后台守护轮询线程（按全局间隔检查所有规则）
- 集成系统托盘（关闭窗口时最小化到托盘）
- 持久化运行日志到 cleanup_history.log
"""

import os
import sys
import threading
import time
from datetime import datetime

import customtkinter as ctk

import config_manager
import cleaner_logic
from gui import MainWindow
from tray_manager import TrayManager


# ─────────────────────────────────────────────────────────────────────────────
# 全局状态
# ─────────────────────────────────────────────────────────────────────────────
_window: MainWindow = None
_tray: TrayManager = None
_poll_event = threading.Event()   # 用于打断等待，立即触发检查


def _get_log_path() -> str:
    """获取日志文件路径（与 EXE / 脚本同级）。"""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "cleanup_history.log")


def _write_log_file(message: str):
    """将日志追加写入 cleanup_history.log，带时间戳。"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}\n"
    try:
        with open(_get_log_path(), "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def log_cb(message: str):
    """统一日志回调：同时更新 GUI 日志框和本地日志文件。"""
    _write_log_file(message)
    if _window:
        try:
            _window.log(message)
        except Exception:
            pass


def run_check_all():
    """执行一轮所有规则的检查与清理。"""
    config = config_manager.load_config()
    rules = config.get("rules", [])
    if not rules:
        log_cb("[提示] 当前没有配置任何监控规则，跳过检查。")
        return
    log_cb(f"[开始] 开始检查所有 {len(rules)} 条监控规则...")
    for i, rule in enumerate(rules):
        drive = rule.get("drive", "?:")
        log_cb(f"[规则 {i+1}] 检查驱动器 {drive}...")
        try:
            cleaner_logic.delete_oldest_until_free(rule, log_cb)
        except Exception as e:
            log_cb(f"[错误] 规则 {i+1} 执行异常: {e}")
    log_cb("[完成] 本轮检查结束。")


def _poll_loop():
    """后台守护轮询线程主函数：按间隔循环检查，支持事件打断。"""
    log_cb("[守护] 后台监控线程已启动。")
    while True:
        run_check_all()
        config = config_manager.load_config()
        interval_min = int(config.get("global_interval_min", 5))
        interval_sec = interval_min * 60
        log_cb(f"[等待] 下次检查将在 {interval_min} 分钟后进行，或等待手动触发...")
        # 等待间隔，但可被 _poll_event 打断
        triggered = _poll_event.wait(timeout=interval_sec)
        if triggered:
            _poll_event.clear()
            log_cb("[手动] 检测到立即检查请求，正在执行...")


def trigger_immediate_check():
    """供 GUI 调用：立即触发一次轮询（打断等待）。"""
    _poll_event.set()


# ─────────────────────────────────────────────────────────────────────────────
# 应用程序生命周期管理
# ─────────────────────────────────────────────────────────────────────────────
def on_show_window():
    """托盘菜单"显示界面"回调。"""
    if _window:
        _window.after(0, _window.show)


def on_quit():
    """完全退出应用程序。"""
    if _tray:
        _tray.stop()
    os._exit(0)


def main():
    global _window, _tray

    # 初始化主窗口
    _window = MainWindow(
        on_trigger_check=trigger_immediate_check,
        on_quit=on_quit
    )
    # 拦截关闭事件 → 最小化到托盘
    _window.protocol("WM_DELETE_WINDOW", _window.on_close)

    # 启动系统托盘
    _tray = TrayManager(show_window_cb=on_show_window, quit_app_cb=on_quit)
    _tray.start()

    # 启动后台轮询守护线程
    poll_thread = threading.Thread(target=_poll_loop, daemon=True)
    poll_thread.start()

    # 启动日志记录
    log_cb("━━━━━━━━━━ 磁盘清理助手启动 ━━━━━━━━━━")

    # 进入 Tkinter 主循环（阻塞）
    _window.mainloop()


if __name__ == "__main__":
    main()
