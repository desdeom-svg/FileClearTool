"""
配置管理模块：负责从 config.json 加载和保存所有监控规则与全局设置。
配置文件与 EXE 同级（或源码目录同级）。
"""

import json
import os
import sys

# 与 EXE / 脚本同级目录
def _get_base_dir() -> str:
    """获取程序所在目录（兼容 PyInstaller 打包后的路径）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(_get_base_dir(), "config.json")

# 默认配置模板
DEFAULT_CONFIG = {
    "global_interval_min": 5,   # 全局轮询间隔（分钟）
    "rules": []                 # 监控规则列表
}

# 单条规则模板
DEFAULT_RULE = {
    "drive": "C:",              # 监控的盘符
    "threshold_gb": 10.0,       # 最小剩余保障容量（GB）
    "clean_paths": [],          # 清理路径列表（字符串数组）
    "use_recycle_bin": False,   # 是否启用回收站模式（移动到临时目录）
    "recycle_bin_path": ""      # 回收站临时目录路径
}


def load_config() -> dict:
    """从磁盘加载配置，如不存在则返回默认配置。"""
    if not os.path.exists(CONFIG_PATH):
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 确保必要字段存在
        data.setdefault("global_interval_min", DEFAULT_CONFIG["global_interval_min"])
        data.setdefault("rules", [])
        return data
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """将当前配置序列化写入 config.json。"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def make_rule(drive: str, threshold_gb: float, clean_paths: list,
              use_recycle_bin: bool = False, recycle_bin_path: str = "") -> dict:
    """构造一条标准监控规则字典。"""
    return {
        "drive": drive,
        "threshold_gb": float(threshold_gb),
        "clean_paths": list(clean_paths),
        "use_recycle_bin": bool(use_recycle_bin),
        "recycle_bin_path": recycle_bin_path
    }
