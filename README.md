# yt-dlp Update Notifier

一个用于监控 yt-dlp 官方版本更新并推送到飞书的自动化工具。

## 功能
- 自动检测 GitHub 上的 yt-dlp 最新 Release。
- 与本地记录的版本比对，发现新版本时触发飞书通知。
- 支持 CLI 手动检测和 Daemon 守护模式（定时任务）。
- **支持 GitHub Actions 自动运行（无需本地挂机）。**
- 消息卡片包含版本对比、警示语及 Release Notes 链接。

## 目录结构
```
.
├── .github/workflows/   # GitHub Actions 配置
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

## 部署方式 1：GitHub Actions (推荐)
**无需本地电脑开机，由 GitHub 免费服务器每天自动运行。**

1. Fork 或 Clone 本项目到你的 GitHub。
2. 进入仓库 **Settings** -> **Secrets and variables** -> **Actions**。
3. 点击 **New repository secret**，添加密钥：
   - Name: `FEISHU_WEBHOOK`
   - Secret: `你的飞书 Webhook 地址`
4. 配置完成！系统将在每天北京时间 **06:00** 自动检查更新。
   - 你也可以在 **Actions** 页面手动点击 "Run workflow" 立即触发测试。

## 部署方式 2：本地运行

### 1. 安装依赖
确保已安装 Python 3.8+。
```bash
pip install -r requirements.txt
```

### 2. 配置
编辑 `config.yaml`，填入你的飞书 Webhook 地址。
你也可以调整检测频率（cron 表达式）。

### 3. 运行检测
- **手动运行一次**：双击 `check_now.bat` 或运行 `python -m src.main check`
- **开启自动监控**：双击 `start_daemon.bat` 或运行 `python -m src.main daemon`
  - *注意：本地模式需要电脑一直开机并保持联网。*

## 开发说明
- 状态文件存储在 `.state/last_version.json`。
- 如果需要测试推送功能，可以手动修改此文件中的 `last_version` 为一个旧版本号，然后运行 `check` 命令。
