# 磁盘清理助手 (Disk Cleaner Assistant)

`Disk Cleaner Assistant` 是一款基于 **Python 3 + CustomTkinter** 开发的 Windows 工业机台与个人工作站自动化后台磁盘空间监控与智能清理工具。主要用于长时间连续运行的工控视觉检测设备、图像录制台或高负载测试机，在磁盘剩余空间不足时自动安全清理历史图样、缓存与日志文件，保障宿主主程序不因磁盘打满而崩溃。

---

## 🌟 核心功能与亮点

- **多驱动器容量实时探针**：
  - 基于 `psutil` 周期性检测系统各个磁盘驱动器（C/D/E等）的总量、已用量与剩余可用容量；
  - 动态预警指示条，剩余空间低于设定警戒线时自动触发静默回收流水线。
- **渐进式智能安全删除（FIFO）**：
  - 支持指定多个需要定期维护的文件夹；
  - 严格按文件最后修改时间（mtime）进行先后排序，按需逐个淘汰清理最旧的文件，达到目标释放阈值即停，绝不粗暴清空整目录。
- **双重回收保护机制**：
  - **软回收模式（隔离区）**：支持将过期文件移入指定的回收归档目录，防止误删重要数据；
  - **硬删除模式（直接回收）**：对确认无用的临时抓图与日志直接永久释放磁盘空间。
- **级联空目录清理**：
  - 文件清理完毕后，自底向上智能递归回收由于文件删除留下的空子文件夹。
- **系统托盘后台静默驻留**：
  - 支持隐藏主窗体并常驻 Windows 系统托盘区，支持开机自启与静默守护。
- **持久化配置管理**：
  - 路径配置、监控周期、警戒阈值持久化于 JSON，历史清理动作自动记入滚动日志。

---

## 📁 目录结构

```text
FileClearTool/
├── cleaner_logic.py          # 核心清理引擎（磁盘容量扫描、文件时间排序与清理逻辑）
├── config_manager.py         # 配置文件读取与写入序列化管理
├── gui.py                    # 基于 CustomTkinter 的现代化暗色交互界面
├── tray_manager.py           # 基于 pystray 的系统托盘常驻与右键菜单组件
├── main.py                   # 启动入口（含单实例运行保护）
├── build.bat                 # PyInstaller 一键打包独立 EXE 脚本
├── app_icon.ico              # 应用程序图标文件
└── README.md                 # 项目详细说明文档
```

---

## 🚀 快速上手与运行

### 1. 运行环境
- 操作系统：Windows 10 / 11 / Windows Server (x64)
- Python 3.8+

### 2. 安装必要依赖
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install customtkinter pystray pillow psutil
```

### 3. 启动运行
```powershell
python main.py
```

### 4. 生产独立 EXE 打包
在项目根目录下双击运行 `build.bat` 或在终端执行：
```powershell
pyinstaller --noconsole --onefile --icon=app_icon.ico --name "DiskCleanerAssistant" main.py
```
构建成功后独立可执行文件将生成于 `dist/DiskCleanerAssistant.exe`，可直接拷贝至工控机免 Python 环境运行。

---

## ⚠️ 注意事项与安全准则
- 建议仅将清理路径配置为工业相机的临时图样缓存目录（如 `D:\TempImages\`）或运行日志目录（如 `D:\Logs\`）。
- **严禁**将系统关键路径（如 `C:\Windows`、`C:\Program Files`）或项目源码根目录加入清理列表，以防数据丢失。
