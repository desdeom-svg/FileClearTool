"""
系统托盘管理模块：使用 pystray 在 Windows 任务栏托盘区域显示图标。
右键菜单提供"显示界面"和"退出"两个选项。
"""

import os
import sys
import threading
import pystray
from PIL import Image


def _get_icon_path() -> str:
    """获取图标文件路径，兼容 PyInstaller 打包。"""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "app_icon.ico")


class TrayManager:
    """管理系统托盘图标的生命周期。"""

    def __init__(self, show_window_cb, quit_app_cb):
        """
        :param show_window_cb: 点击"显示界面"时调用的回调函数
        :param quit_app_cb:    点击"退出"时调用的回调函数
        """
        self.show_window_cb = show_window_cb
        self.quit_app_cb = quit_app_cb
        self.icon: pystray.Icon = None
        self._thread: threading.Thread = None

    def _build_icon_image(self) -> Image.Image:
        """加载图标图像；若不存在则生成简单占位图。"""
        icon_path = _get_icon_path()
        if os.path.exists(icon_path):
            return Image.open(icon_path).convert("RGBA")
        # 生成一个简单的蓝色占位图标
        img = Image.new("RGBA", (64, 64), color=(30, 100, 200, 255))
        return img

    def _on_show(self, icon, item):
        """托盘菜单"显示界面"回调。"""
        self.show_window_cb()

    def _on_quit(self, icon, item):
        """托盘菜单"退出"回调。"""
        icon.stop()
        self.quit_app_cb()

    def start(self):
        """在独立线程中启动托盘图标（非阻塞）。"""
        img = self._build_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("显示界面", self._on_show, default=True),
            pystray.MenuItem("退出", self._on_quit)
        )
        self.icon = pystray.Icon(
            name="DiskCleanerAssistant",
            icon=img,
            title="磁盘清理助手",
            menu=menu
        )
        self._thread = threading.Thread(target=self.icon.run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止并移除托盘图标。"""
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
