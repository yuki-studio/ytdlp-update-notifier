# yt-dlp Update Notifier

一个用于监控 yt-dlp 官方版本更新并推送到飞书的自动化工具。

## 功能
- 自动检测 GitHub 上的 yt-dlp 最新 Release。
- 与本地记录的版本比对，发现新版本时触发飞书通知。
- 支持 CLI 手动检测和 Daemon 守护模式（定时任务）。
- 消息卡片包含版本对比、警示语及 Release Notes 链接。

## 目录结构
```
.
├── config.yaml          # 配置文件
├── requirements.txt     # Python 依赖
├── src/                 # 源码目录
│   ├── main.py          # 入口
│   ├── github.py        # GitHub API 客户端
│   ├── feishu.py        # 飞书消息客户端
│   ├── storage.py       # 状态存储
│   └── utils.py         # 工具函数
├── docs/                # 文档
└── .state/              # 运行时状态（自动生成）
```

## 快速开始

### 1. 安装依赖
确保已安装 Python 3.8+。
```bash
pip install -r requirements.txt
```

### 2. 配置
编辑 `config.yaml`，填入你的飞书 Webhook 地址（已默认填入你提供的地址）。
你也可以调整检测频率（cron 表达式）和 GitHub Token（可选，用于提升 API限额）。

### 3. 运行检测
手动运行一次检测：
```bash
python -m src.main check
```
如果是首次运行且 `config.yaml` 中 `initial_push: false`，则只会记录当前版本，不会发送通知。

### 4. 守护模式
启动定时任务（默认每天 09:00）：
```bash
python -m src.main daemon
```

## 开发说明
- 状态文件存储在 `.state/last_version.json`。如果需要测试推送功能，可以手动修改此文件中的 `last_version` 为一个旧版本号，然后运行 `check` 命令。
