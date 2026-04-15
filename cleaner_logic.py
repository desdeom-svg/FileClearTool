"""
核心清理引擎：
- 文件级递归扫描 + 按时间排序删除
- 删除后空间动态校验，满足阈值立即停止
- 空目录回收
- 回收站模式（移动到临时目录，重名加时间戳后缀）
"""

import os
import shutil
import psutil
from datetime import datetime
from typing import Callable, Optional


def get_free_gb(drive: str) -> float:
    """获取指定盘符的当前剩余空间（GB）。"""
    try:
        # 确保盘符格式正确，例如 "C:\"
        path = drive if drive.endswith("\\") or drive.endswith("/") else drive + "\\"
        usage = psutil.disk_usage(path)
        return usage.free / (1024 ** 3)
    except Exception:
        return -1.0


def scan_files_sorted(clean_path: str, log_cb: Callable[[str], None] = None) -> list:
    """
    递归扫描指定目录中的所有文件，
    返回按 mtime（最后修改时间）升序排列的 (mtime, path) 元组列表。
    """
    file_list = []
    if not os.path.isdir(clean_path):
        if log_cb:
            log_cb(f"[警告] 清理路径不存在或不是目录: {clean_path}")
        return file_list
    if log_cb:
        log_cb(f"[扫描] 正在扫描目录: {clean_path} ...")
    error_count = 0
    try:
        for root, dirs, files in os.walk(clean_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    file_list.append((mtime, fpath))
                except Exception:
                    error_count += 1
    except Exception as e:
        if log_cb:
            log_cb(f"[错误] 扫描目录时异常: {clean_path} — {e}")
    # 按修改时间升序排列（最旧的在前）
    file_list.sort(key=lambda x: x[0])
    if log_cb:
        msg = f"[扫描] {clean_path} 找到 {len(file_list)} 个文件"
        if error_count > 0:
            msg += f"（{error_count} 个无法读取）"
        log_cb(msg)
    return file_list


def _resolve_dest_path(dest_dir: str, filename: str) -> str:
    """
    计算目标路径；若目标已存在同名文件，
    则在文件名后追加时间戳以避免覆盖。
    """
    dest_path = os.path.join(dest_dir, filename)
    if not os.path.exists(dest_path):
        return dest_path
    # 拆分扩展名并插入时间戳
    name, ext = os.path.splitext(filename)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return os.path.join(dest_dir, f"{name}_{ts}{ext}")


def delete_oldest_until_free(
    rule: dict,
    log_cb: Callable[[str], None]
) -> None:
    """
    核心清理流程：
    1. 检查剩余空间是否低于阈值
    2. 若是，扫描所有清理路径，逐个删除最旧文件
    3. 每删完一个文件，重新校验空间；满足则停止
    4. 若启用回收站模式，改为移动文件
    5. 完成后清理空目录
    """
    drive = rule.get("drive", "C:")
    threshold_gb = rule.get("threshold_gb", 10.0)
    clean_paths = rule.get("clean_paths", [])
    use_recycle_bin = rule.get("use_recycle_bin", False)
    recycle_bin_path = rule.get("recycle_bin_path", "")

    free_gb = get_free_gb(drive)
    if free_gb < 0:
        log_cb(f"[错误] 无法读取 {drive} 的空间信息，跳过。")
        return

    log_cb(f"[检查] {drive} 当前剩余: {free_gb:.2f} GB，阈值: {threshold_gb:.2f} GB")

    if free_gb >= threshold_gb:
        log_cb(f"[正常] {drive} 空间充足，无需清理。")
        return

    log_cb(f"[触发] {drive} 空间不足！开始执行清理...")

    # 若启用回收站模式，确保回收站目录存在
    if use_recycle_bin:
        if not recycle_bin_path:
            log_cb("[警告] 已开启回收站模式但未设置路径，改为直接删除。")
            use_recycle_bin = False
        else:
            try:
                os.makedirs(recycle_bin_path, exist_ok=True)
            except Exception as e:
                log_cb(f"[警告] 无法创建回收站目录: {e}，改为直接删除。")
                use_recycle_bin = False

    # 收集所有清理路径的文件（带时间元组），合并后全局排序
    all_file_tuples = []
    for cp in clean_paths:
        try:
            all_file_tuples.extend(scan_files_sorted(cp, log_cb))
        except Exception as e:
            log_cb(f"[错误] 扫描路径 {cp} 时发生异常: {e}")

    if not all_file_tuples:
        log_cb("[提示] 清理路径中没有找到可删除的文件。")
        return

    # 全局按修改时间升序排序（最旧的在前）
    all_file_tuples.sort(key=lambda x: x[0])
    all_files = [fp for _, fp in all_file_tuples]

    log_cb(f"[汇总] 共发现 {len(all_files)} 个候选文件，开始逐个清理...")

    deleted_count = 0
    for fpath in all_files:
        # 重新检查空间
        free_gb = get_free_gb(drive)
        if free_gb >= threshold_gb:
            log_cb(f"[完成] {drive} 剩余空间已恢复至 {free_gb:.2f} GB，停止清理。")
            break

        if not os.path.isfile(fpath):
            continue  # 可能已被上轮删除或外部删除

        try:
            file_size_mb = os.path.getsize(fpath) / (1024 * 1024)
            if use_recycle_bin:
                filename = os.path.basename(fpath)
                dest_path = _resolve_dest_path(recycle_bin_path, filename)
                shutil.move(fpath, dest_path)
                log_cb(f"[移动] ({file_size_mb:.1f}MB) {fpath} → {dest_path}")
            else:
                os.remove(fpath)
                log_cb(f"[删除] ({file_size_mb:.1f}MB) {fpath}")
            deleted_count += 1
        except Exception as e:
            log_cb(f"[错误] 处理文件失败: {fpath} — {e}")

    free_gb = get_free_gb(drive)
    if free_gb < threshold_gb:
        log_cb(f"[警告] 清理完毕但 {drive} 仍只剩 {free_gb:.2f} GB，可能清理路径内文件不足。")
    else:
        log_cb(f"[汇总] 共处理 {deleted_count} 个文件，{drive} 当前剩余 {free_gb:.2f} GB。")

    # 清理空目录
    for cp in clean_paths:
        remove_empty_dirs(cp, log_cb)


def remove_empty_dirs(root_path: str, log_cb: Optional[Callable[[str], None]] = None) -> None:
    """
    从下往上删除 root_path 下的所有空文件夹，
    但不删除 root_path 自身。
    """
    if not os.path.isdir(root_path):
        return
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
        if dirpath == root_path:
            continue
        try:
            if not os.listdir(dirpath):  # 目录完全为空
                os.rmdir(dirpath)
                if log_cb:
                    log_cb(f"[清目录] 已删除空文件夹: {dirpath}")
        except Exception as e:
            if log_cb:
                log_cb(f"[错误] 无法删除空文件夹 {dirpath}: {e}")
