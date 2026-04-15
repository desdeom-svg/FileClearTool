#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图标转换脚本：将 PNG 转换为多尺寸 ICO 文件。
运行方式：python make_icon.py
"""

import os
import sys
from PIL import Image


def make_ico(png_path: str, ico_path: str):
    """将 PNG 文件转换为多尺寸的 ICO 图标文件。"""
    if not os.path.exists(png_path):
        print(f"[错误] PNG 文件不存在: {png_path}")
        sys.exit(1)

    img = Image.open(png_path).convert("RGBA")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    icons = []
    for size in sizes:
        resized = img.resize(size, Image.LANCZOS)
        icons.append(resized)
    
    # 保存为 ICO（第一张为主图标，其余为额外尺寸）
    icons[0].save(
        ico_path,
        format="ICO",
        sizes=[s for s in sizes],
        append_images=icons[1:]
    )
    print(f"[成功] 已生成图标: {ico_path}")
    print(f"       包含尺寸: {[f'{s[0]}x{s[1]}' for s in sizes]}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 查找 PNG 图标文件（优先找 disk_cleaner_icon 开头的文件）
    png_candidates = [
        f for f in os.listdir(base_dir)
        if f.lower().endswith(".png") and "icon" in f.lower()
    ]
    
    if not png_candidates:
        print("[错误] 未找到 PNG 图标文件，请确保目录内有 *icon*.png 文件。")
        sys.exit(1)
    
    png_path = os.path.join(base_dir, sorted(png_candidates)[0])
    ico_path = os.path.join(base_dir, "app_icon.ico")
    
    print(f"[信息] 使用 PNG 文件: {png_path}")
    make_ico(png_path, ico_path)
