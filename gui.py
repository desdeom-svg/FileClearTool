"""
主 GUI 模块：基于 CustomTkinter 的现代深色模式磁盘清理助手界面。
包含：监控规则卡片列表、添加/编辑规则弹窗、实时日志框、立即检查按钮。
"""

import os
import string
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime
from typing import Callable, Optional

import config_manager
from config_manager import make_rule


# ─────────────────────────────────────────────────────────────────────────────
# 颜色与样式常量
# ─────────────────────────────────────────────────────────────────────────────
DARK_BG        = "#0d1117"
CARD_BG        = "#161b22"
CARD_HOVER     = "#1f2937"
ACCENT_BLUE    = "#2563eb"
ACCENT_CYAN    = "#06b6d4"
ACCENT_GREEN   = "#10b981"
ACCENT_RED     = "#ef4444"
TEXT_PRIMARY   = "#f0f6fc"
TEXT_SECONDARY = "#8b949e"
BORDER_COLOR   = "#30363d"
LOG_BG         = "#0d1117"
LOG_TEXT       = "#39d353"


def get_available_drives() -> list:
    """枚举当前系统中可用的固定磁盘盘符列表。"""
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:"
        path = drive + "\\"
        if os.path.exists(path):
            drives.append(drive)
    return drives if drives else ["C:"]


# ─────────────────────────────────────────────────────────────────────────────
# 规则编辑弹窗
# ─────────────────────────────────────────────────────────────────────────────
class RuleDialog(ctk.CTkToplevel):
    """添加/编辑监控规则的弹出窗口。"""

    def __init__(self, parent, rule: Optional[dict] = None, on_save: Optional[Callable] = None):
        super().__init__(parent)
        self.on_save = on_save
        self.result = None
        self._clean_paths: list = list(rule.get("clean_paths", [])) if rule else []

        # 窗口配置
        self.title("添加监控规则" if rule is None else "编辑监控规则")
        self.geometry("580x720")
        self.resizable(False, False)
        self.configure(fg_color=DARK_BG)
        self.grab_set()  # 模态
        self.lift()

        # 已有规则数据（用于编辑模式）
        self._rule = rule or {}

        self._build_ui()

    def _build_ui(self):
        # 标题
        ctk.CTkLabel(
            self, text="配置监控规则",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(pady=(24, 4))
        ctk.CTkLabel(
            self, text="设置磁盘阈值、清理路径和回收站策略",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_SECONDARY
        ).pack(pady=(0, 20))

        form = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12)
        form.pack(fill="x", padx=24, pady=4)

        pad = {"padx": 20, "pady": 8}

        # 盘符选择
        row0 = ctk.CTkFrame(form, fg_color="transparent")
        row0.pack(fill="x", **pad)
        ctk.CTkLabel(row0, text="监控盘符", width=120, anchor="w",
                     text_color=TEXT_PRIMARY,
                     font=ctk.CTkFont(family="Segoe UI", size=13)).pack(side="left")
        drives = get_available_drives()
        default_drive = self._rule.get("drive", drives[0])
        self.drive_var = ctk.StringVar(value=default_drive)
        ctk.CTkOptionMenu(row0, variable=self.drive_var, values=drives,
                          fg_color=CARD_HOVER, button_color=ACCENT_BLUE,
                          dropdown_fg_color=CARD_BG,
                          text_color=TEXT_PRIMARY, width=120).pack(side="right")

        # 阈值输入
        row1 = ctk.CTkFrame(form, fg_color="transparent")
        row1.pack(fill="x", **pad)
        ctk.CTkLabel(row1, text="最小剩余 (GB)", width=120, anchor="w",
                     text_color=TEXT_PRIMARY,
                     font=ctk.CTkFont(family="Segoe UI", size=13)).pack(side="left")
        self.threshold_var = ctk.StringVar(value=str(self._rule.get("threshold_gb", "10")))
        ctk.CTkEntry(row1, textvariable=self.threshold_var, width=120,
                     fg_color=CARD_HOVER, border_color=BORDER_COLOR,
                     text_color=TEXT_PRIMARY).pack(side="right")

        # 清理路径列表
        ctk.CTkLabel(form, text="清理路径", anchor="w",
                     text_color=TEXT_PRIMARY,
                     font=ctk.CTkFont(family="Segoe UI", size=13)).pack(fill="x", padx=20, pady=(8, 2))

        self.path_frame = ctk.CTkScrollableFrame(form, fg_color=CARD_HOVER,
                                                 height=120, corner_radius=8)
        self.path_frame.pack(fill="x", padx=20, pady=(0, 4))
        self._refresh_path_list()

        ctk.CTkButton(form, text="+ 浏览添加目录",
                      fg_color="transparent", border_color=ACCENT_CYAN,
                      border_width=1, text_color=ACCENT_CYAN, height=32,
                      hover_color=CARD_HOVER,
                      command=self._add_path).pack(padx=20, pady=(2, 8))

        # 回收站开关
        row2 = ctk.CTkFrame(form, fg_color="transparent")
        row2.pack(fill="x", **pad)
        ctk.CTkLabel(row2, text="回收站模式", width=120, anchor="w",
                     text_color=TEXT_PRIMARY,
                     font=ctk.CTkFont(family="Segoe UI", size=13)).pack(side="left")
        self.recycle_var = ctk.BooleanVar(value=self._rule.get("use_recycle_bin", False))
        ctk.CTkSwitch(row2, variable=self.recycle_var, text="",
                      progress_color=ACCENT_BLUE,
                      command=self._toggle_recycle).pack(side="right")

        # 回收站路径
        row3 = ctk.CTkFrame(form, fg_color="transparent")
        row3.pack(fill="x", **pad)
        ctk.CTkLabel(row3, text="临时目录路径", width=120, anchor="w",
                     text_color=TEXT_SECONDARY,
                     font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="left")
        self.recycle_path_var = ctk.StringVar(value=self._rule.get("recycle_bin_path", ""))
        self.recycle_entry = ctk.CTkEntry(row3, textvariable=self.recycle_path_var, width=240,
                                          fg_color=CARD_HOVER, border_color=BORDER_COLOR,
                                          text_color=TEXT_PRIMARY)
        self.recycle_entry.pack(side="left", padx=(8, 4))
        self.recycle_browse_btn = ctk.CTkButton(row3, text="浏览", width=60,
                                                fg_color=ACCENT_BLUE,
                                                command=self._browse_recycle)
        self.recycle_browse_btn.pack(side="left")
        self._toggle_recycle()  # 初始化状态

        # 按钮区（放在底部，保证可见）
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(16, 24), side="bottom")
        ctk.CTkButton(btn_frame, text="取消", fg_color=CARD_HOVER,
                      text_color=TEXT_SECONDARY, hover_color=CARD_BG,
                      width=140, height=40,
                      font=ctk.CTkFont(family="Segoe UI", size=14),
                      command=self.destroy).pack(side="left", expand=True, padx=(0, 8))
        ctk.CTkButton(btn_frame, text="✅  确认保存", fg_color=ACCENT_GREEN,
                      text_color="#000000",
                      width=200, height=40,
                      font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                      command=self._save).pack(side="right", expand=True, padx=(8, 0))

    def _refresh_path_list(self):
        for w in self.path_frame.winfo_children():
            w.destroy()
        if not self._clean_paths:
            ctk.CTkLabel(self.path_frame, text="尚未添加任何清理路径",
                         text_color=TEXT_SECONDARY,
                         font=ctk.CTkFont(family="Segoe UI", size=11)).pack(pady=8)
            return
        for i, p in enumerate(self._clean_paths):
            row = ctk.CTkFrame(self.path_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=p, text_color=TEXT_PRIMARY,
                         font=ctk.CTkFont(family="Segoe UI", size=11),
                         anchor="w").pack(side="left", fill="x", expand=True)
            idx = i
            ctk.CTkButton(row, text="✕", width=28, height=24,
                          fg_color="transparent", text_color=ACCENT_RED,
                          hover_color=CARD_BG,
                          command=lambda ix=idx: self._remove_path(ix)).pack(side="right")

    def _add_path(self):
        p = filedialog.askdirectory(title="选择清理目录", parent=self)
        if p:
            # 规范化路径分隔符
            p = os.path.normpath(p)
            if p not in self._clean_paths:
                self._clean_paths.append(p)
                self._refresh_path_list()

    def _remove_path(self, idx: int):
        if 0 <= idx < len(self._clean_paths):
            self._clean_paths.pop(idx)
            self._refresh_path_list()

    def _toggle_recycle(self):
        state = "normal" if self.recycle_var.get() else "disabled"
        self.recycle_entry.configure(state=state)
        self.recycle_browse_btn.configure(state=state)

    def _browse_recycle(self):
        p = filedialog.askdirectory(title="选择临时存储目录", parent=self)
        if p:
            self.recycle_path_var.set(os.path.normpath(p))

    def _save(self):
        try:
            threshold = float(self.threshold_var.get())
            if threshold <= 0:
                raise ValueError("阈值必须大于 0")
        except ValueError as e:
            messagebox.showerror("输入错误", f"请输入有效的 GB 数值：{e}", parent=self)
            return

        if not self._clean_paths:
            messagebox.showerror("输入错误", "请至少添加一个清理路径。", parent=self)
            return

        self.result = make_rule(
            drive=self.drive_var.get(),
            threshold_gb=threshold,
            clean_paths=self._clean_paths,
            use_recycle_bin=self.recycle_var.get(),
            recycle_bin_path=self.recycle_path_var.get()
        )
        if self.on_save:
            self.on_save(self.result)
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# 规则卡片组件
# ─────────────────────────────────────────────────────────────────────────────
class RuleCard(ctk.CTkFrame):
    """在列表中展示单条监控规则的卡片组件。"""

    def __init__(self, parent, rule: dict, index: int,
                 on_edit: Callable, on_remove: Callable, **kwargs):
        super().__init__(parent, fg_color=CARD_BG, corner_radius=10,
                         border_color=BORDER_COLOR, border_width=1, **kwargs)
        self._rule = rule
        self._index = index
        self._build(on_edit, on_remove)

    def _build(self, on_edit, on_remove):
        rule = self._rule
        drive = rule.get("drive", "?:")
        threshold = rule.get("threshold_gb", 0)
        paths = rule.get("clean_paths", [])
        use_rb = rule.get("use_recycle_bin", False)

        # 顶行：盘符 + 阈值
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 4))

        # 盘符徽章
        badge = ctk.CTkFrame(top, fg_color=ACCENT_BLUE, corner_radius=6, width=42, height=28)
        badge.pack(side="left")
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text=drive, text_color="white",
                     font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).place(relx=0.5, rely=0.5, anchor="center")

        # 阈值信息
        info_frame = ctk.CTkFrame(top, fg_color="transparent")
        info_frame.pack(side="left", padx=12, fill="x", expand=True)
        ctk.CTkLabel(info_frame,
                     text=f"阈值: {threshold:.1f} GB   {'🗑 回收站模式' if use_rb else '🗑 直接删除'}",
                     text_color=TEXT_PRIMARY,
                     font=ctk.CTkFont(family="Segoe UI", size=13)).pack(anchor="w")

        # 编辑/删除按钮
        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(side="right")
        idx = self._index
        ctk.CTkButton(btn_frame, text="编辑", width=60, height=28,
                      fg_color="transparent", border_color=ACCENT_CYAN,
                      border_width=1, text_color=ACCENT_CYAN,
                      hover_color=CARD_HOVER,
                      command=lambda: on_edit(idx)).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_frame, text="移除", width=60, height=28,
                      fg_color="transparent", border_color=ACCENT_RED,
                      border_width=1, text_color=ACCENT_RED,
                      hover_color=CARD_HOVER,
                      command=lambda: on_remove(idx)).pack(side="left")

        # 路径列表
        paths_text = "\n".join(f"  📁 {p}" for p in paths) if paths else "  （无清理路径）"
        ctk.CTkLabel(self, text=paths_text,
                     text_color=TEXT_SECONDARY,
                     font=ctk.CTkFont(family="Segoe UI", size=11),
                     justify="left", anchor="w").pack(fill="x", padx=16, pady=(0, 12))


# ─────────────────────────────────────────────────────────────────────────────
# 主窗口
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(ctk.CTk):
    """磁盘清理助手主窗口。"""

    def __init__(self, on_trigger_check: Callable, on_quit: Callable):
        super().__init__()

        self.on_trigger_check = on_trigger_check  # 外部传入：触发一次立即检查
        self.on_quit = on_quit
        self._log_lock = threading.Lock()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("磁盘清理助手 — Disk Cleaner Assistant")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(fg_color=DARK_BG)

        # 设置令牌图标（若存在）
        self._set_icon()
        self._build_ui()

        # 加载配置并渲染规则卡片
        self._config = config_manager.load_config()
        self._render_rules()

    def _set_icon(self):
        try:
            import sys
            if getattr(sys, 'frozen', False):
                base = sys._MEIPASS
            else:
                base = os.path.dirname(os.path.abspath(__file__))
            ico_path = os.path.join(base, "app_icon.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
        except Exception:
            pass

    def _build_ui(self):
        # ── 顶部标题栏 ──
        header = ctk.CTkFrame(self, fg_color=CARD_BG, height=64, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="🧹  磁盘清理助手",
                     font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=24, pady=16)
        ctk.CTkLabel(header, text="Disk Cleaner Assistant",
                     font=ctk.CTkFont(family="Segoe UI", size=13),
                     text_color=TEXT_SECONDARY).pack(side="left", pady=16)

        # 运行状态指示灯
        self.status_dot = ctk.CTkLabel(header, text="● 后台监控运行中",
                                       font=ctk.CTkFont(family="Segoe UI", size=12),
                                       text_color=ACCENT_GREEN)
        self.status_dot.pack(side="right", padx=24)

        # ── 主体区域（左右分栏）──
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # ── 左侧面板 ──
        left = ctk.CTkFrame(body, fg_color="transparent", width=500)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # 全局间隔设置行
        interval_frame = ctk.CTkFrame(left, fg_color=CARD_BG, corner_radius=10)
        interval_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(interval_frame, text="全局检查间隔（分钟）",
                     text_color=TEXT_PRIMARY,
                     font=ctk.CTkFont(family="Segoe UI", size=13)).pack(side="left", padx=16, pady=10)
        self._interval_var = ctk.StringVar(value=str(self._get_interval()))
        interval_entry = ctk.CTkEntry(interval_frame, textvariable=self._interval_var,
                                      width=70, fg_color=CARD_HOVER,
                                      border_color=BORDER_COLOR, text_color=TEXT_PRIMARY)
        interval_entry.pack(side="right", padx=(4, 8))
        ctk.CTkButton(interval_frame, text="应用", width=60, height=32,
                      fg_color=ACCENT_BLUE,
                      command=self._apply_interval).pack(side="right")

        # 规则列表标签行
        rule_header = ctk.CTkFrame(left, fg_color="transparent")
        rule_header.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(rule_header, text="监控规则",
                     text_color=TEXT_PRIMARY,
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold")).pack(side="left")

        ctk.CTkButton(rule_header, text="+ 添加规则", width=100, height=32,
                      fg_color=ACCENT_BLUE, text_color=TEXT_PRIMARY,
                      command=self._open_add_dialog).pack(side="right", padx=(0, 4))

        # 立即检查按钮
        ctk.CTkButton(rule_header, text="⚡ 立即检查", width=100, height=32,
                      fg_color=ACCENT_GREEN, text_color="#000000",
                      command=self._check_now).pack(side="right", padx=(0, 8))

        # 规则卡片滚动区
        self.rules_scroll = ctk.CTkScrollableFrame(left, fg_color="transparent",
                                                    corner_radius=0)
        self.rules_scroll.pack(fill="both", expand=True)

        # ── 右侧日志面板 ──
        right = ctk.CTkFrame(body, fg_color="transparent", width=380)
        right.pack(side="right", fill="both", padx=(8, 0))
        right.pack_propagate(False)

        log_header = ctk.CTkFrame(right, fg_color="transparent")
        log_header.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(log_header, text="运行日志",
                     text_color=TEXT_PRIMARY,
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold")).pack(side="left")
        ctk.CTkButton(log_header, text="清空", width=60, height=28,
                      fg_color=CARD_HOVER, text_color=TEXT_SECONDARY,
                      command=self._clear_log).pack(side="right")

        self.log_box = ctk.CTkTextbox(right, fg_color=LOG_BG, text_color=LOG_TEXT,
                                       font=ctk.CTkFont(family="Consolas", size=11),
                                       wrap="word", state="disabled",
                                       corner_radius=10, border_color=BORDER_COLOR,
                                       border_width=1)
        self.log_box.pack(fill="both", expand=True)

    def _get_interval(self) -> int:
        """从已加载/或待加载的配置中获取全局间隔。"""
        try:
            return int(self._config.get("global_interval_min", 5))
        except Exception:
            return 5

    def _apply_interval(self):
        try:
            val = int(self._interval_var.get())
            if val <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的正整数分钟数。")
            return
        self._config["global_interval_min"] = val
        config_manager.save_config(self._config)
        self.log(f"[设置] 全局检查间隔已更新为 {val} 分钟。")

    def _render_rules(self):
        """清空并重新渲染所有规则卡片。"""
        for w in self.rules_scroll.winfo_children():
            w.destroy()
        rules = self._config.get("rules", [])
        if not rules:
            ctk.CTkLabel(self.rules_scroll,
                         text="暂无监控规则\n点击「+ 添加规则」开始配置",
                         text_color=TEXT_SECONDARY,
                         font=ctk.CTkFont(family="Segoe UI", size=13)).pack(pady=50)
            return
        for i, rule in enumerate(rules):
            card = RuleCard(self.rules_scroll, rule, i,
                            on_edit=self._open_edit_dialog,
                            on_remove=self._remove_rule)
            card.pack(fill="x", pady=4, padx=2)

    def _open_add_dialog(self):
        RuleDialog(self, rule=None, on_save=self._on_rule_saved)

    def _open_edit_dialog(self, index: int):
        rules = self._config.get("rules", [])
        if 0 <= index < len(rules):
            def _on_edit_save(new_rule, idx=index):
                self._config["rules"][idx] = new_rule
                config_manager.save_config(self._config)
                self._render_rules()
                self.log(f"[设置] 规则 {idx+1}（{new_rule['drive']}）已更新。")
                # 立即触发一次检查
                threading.Thread(target=self.on_trigger_check, daemon=True).start()
            RuleDialog(self, rule=rules[index], on_save=_on_edit_save)

    def _on_rule_saved(self, new_rule: dict):
        self._config.setdefault("rules", []).append(new_rule)
        config_manager.save_config(self._config)
        self._render_rules()
        self.log(f"[设置] 已添加新规则：监控 {new_rule['drive']}，阈值 {new_rule['threshold_gb']:.1f} GB。")
        # 立即触发一次检查
        threading.Thread(target=self.on_trigger_check, daemon=True).start()

    def _remove_rule(self, index: int):
        rules = self._config.get("rules", [])
        if not (0 <= index < len(rules)):
            return
        drive = rules[index].get("drive", "?:")
        if messagebox.askyesno("确认移除", f"确定要移除 {drive} 的监控规则吗？"):
            rules.pop(index)
            config_manager.save_config(self._config)
            self._render_rules()
            self.log(f"[设置] 已移除 {drive} 的监控规则。")

    def _check_now(self):
        self.log("[手动] 触发立即全盘检查...")
        threading.Thread(target=self.on_trigger_check, daemon=True).start()

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def log(self, message: str):
        """线程安全地向日志框追加一条消息。"""
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}\n"
        with self._log_lock:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", line)
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

    def get_config(self) -> dict:
        """返回当前加载的配置（供外部轮询线程读取）。"""
        return self._config

    def on_close(self):
        """拦截关闭事件，最小化到托盘。"""
        self.withdraw()

    def show(self):
        """从托盘恢复显示主窗口。"""
        self.deiconify()
        self.lift()
        self.focus_force()
