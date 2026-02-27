# yt-dlp 版本监控与飞书通知 PRD

## 1. 背景与目标
- 背景：公司产品依赖开源库 yt-dlp，需在官方发布新版本时及时跟进。
- 目标：
  - 自动检测 yt-dlp 官方最新版本（GitHub Releases）。
  - 当检测到新版本且不同于上次记录时，推送飞书通知。
  - 通知卡片风格参考示例截图，包含“最新版本”“上一版本”“提示语”“Release Notes 链接”。

## 2. 用户与场景
- 主要用户：产品经理、研发、运维。
- 触发场景：
  - 定时巡检（建议每 1 小时/每日 09:00 两种可配模式）。
  - 手动触发（CLI）。

## 3. 范围与非目标
- 范围：
  - 检测数据源：yt-dlp 官方 GitHub 仓库（yt-dlp/yt-dlp）Releases。
  - 版本比较、持久化上次记录、飞书 Webhook 推送。
- 非目标：
  - 自动升级公司产品、兼容性验证、变更公告撰写。

## 4. 数据源与规则
- 数据源：
  - GitHub API：GET https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest
  - 备选：GET https://api.github.com/repos/yt-dlp/yt-dlp/releases（取首个非草稿、非预发布）
  - 退化方案：爬取 https://github.com/yt-dlp/yt-dlp/releases（仅在 API 受限时启用）
- 版本字段解析优先级：
  1) tag_name（例如“2026.02.04”或“v2026.02.04”）
  2) name（如未提供 tag）
- 版本格式：yyyy.mm.dd（允许带前缀 v），按语义：字符串等值比较为主；如需排序，以日期解析为主。
- Release Notes 链接：
  - 优先使用 html_url（某个 release 的网页地址）
  - 备选：构造 https://github.com/yt-dlp/yt-dlp/releases/tag/{tag_name}

## 5. 触发策略
- 定时：支持 cron 表达式（默认 0 9 * * * 每日 09:00）。
- 手动：命令行 ytdlp-notify check。
- 首次运行：若无历史记录，则仅记录版本，不推送；支持配置首次是否推送。

## 6. 配置项
config.yaml
- github:
  - repo: "yt-dlp/yt-dlp"
  - token: 可选（提升速率限制）
  - timeout: 5000ms
- check:
  - cron: "0 9 * * *"
  - initial_push: false
- feishu:
  - webhook: "<由用户提供>"
  - timeout: 5000ms
  - card_style: "default"（保留截图风格）
- storage:
  - path: ".state/last_version.json"

## 7. 存储设计
.state/last_version.json
{
  "repo": "yt-dlp/yt-dlp",
  "last_version": "2026.02.04",
  "last_checked_at": "2026-02-04T10:22:00Z"
}

## 8. 飞书消息设计（对齐截图风格）
- 消息要素：
  - 标题：yt-dlp 版本更新提示
  - 最新版本：{latest_version}
  - 上一版本：{previous_version | 无记录}
  - 警示语：请及时迭代以保证产品正常运行
  - Release Notes 链接：{release_notes_url}
- 建议使用飞书“富文本/交互卡片消息”（post/card）。
- 示例 payload（简化版，兼容 Incoming Webhook）：

POST {feishu.webhook}
Content-Type: application/json
{
  "msg_type": "interactive",
  "card": {
    "header": {
      "template": "blue",
      "title": { "tag": "plain_text", "content": "yt-dlp 版本更新提示" }
    },
    "elements": [
      {
        "tag": "div",
        "fields": [
          {
            "is_short": true,
            "text": { "tag": "lark_md", "content": "**最新版本：** ${latest_version}" }
          },
          {
            "is_short": true,
            "text": { "tag": "lark_md", "content": "**上一版本：** ${previous_version:-无记录}" }
          }
        ]
      },
      {
        "tag": "hr"
      },
      {
        "tag": "div",
        "text": { "tag": "lark_md", "content": "⚠️ 请及时迭代以保证产品正常运行" }
      },
      {
        "tag": "action",
        "actions": [
          {
            "tag": "button",
            "text": { "tag": "plain_text", "content": "点击查看 Release Notes" },
            "type": "primary",
            "url": "${release_notes_url}"
          }
        ]
      }
    ]
  }
}

- 文案规则：
  - previous_version 为空时展示“无记录”。
  - 若 latest_version == previous_version：不推送。
  - 推送频控：同一版本在 24h 内最多推送一次（可配置）。

## 9. 流程
1) 读取 last_version.json（若不存在，previous=空）。
2) 拉取 GitHub 最新发布（排除 draft/prerelease）。
3) 提取 latest_version、release_notes_url。
4) 若 latest_version 与 previous 相同：结束。
5) 调用飞书 webhook 发送卡片。
6) 写回 last_version.json：更新 last_version、last_checked_at。
7) 记录日志。

## 10. 错误与重试
- GitHub 失败：指数退避重试 3 次；降级为 releases 列表；再失败则告警（可选飞书发送“监控失败”卡片）。
- Webhook 失败：重试 3 次，失败落盘到 .state/failed_notifications/*.json，下一周期补偿。
- 速率限制：若无 token 限流，间隔拉取；若 403，延迟至 X-RateLimit-Reset 后重试。

## 11. 安全与合规
- 不在仓库提交明文 webhook；支持环境变量 FEISHU_WEBHOOK。
- 支持从密钥管理工具读取（可扩展）。

## 12. 性能与可运维性
- 单次检测一次 API 调用，耗时 < 1s。
- 日志：info、warn、error；stdout 和 logs/app.log。
- 健康探针：/health（可选，返回最近一次检测时间与结果）。

## 13. 验收标准
- 首次运行记录版本且不推送（initial_push=false）。
- 当 GitHub 出现新版本时，1 分钟内发送飞书卡片，字段与截图一致。
- 重复运行不产生重复推送。
- Release Notes 按钮跳转正确。
- 无网络时不崩溃，下次恢复后可继续检测。

## 14. 测试用例（核心）
- 新版本出现 -> 推送一次。
- 无新版本 -> 不推送。
- previous 为空 -> 按配置决定是否推送。
- tag 带 v 前缀 -> 能正确解析为版本号。
- API rate limit -> 退避与降级策略生效。
- Webhook 失败 -> 重试与补偿生效。

## 15. 工程目录建议
.
├─ docs/
│  └─ PRD.md
├─ src/
│  ├─ index.ts            # 入口与调度
│  ├─ github.ts           # 拉取与解析 release
│  ├─ feishu.ts           # 构建与发送卡片
│  ├─ storage.ts          # 版本持久化
│  └─ utils.ts            # 比较、重试、日志
├─ .state/
│  └─ last_version.json
├─ config.yaml
├─ package.json / pyproject.toml（任选技术栈）
└─ README.md

## 16. 命令行
- 初始化：ytdlp-notify init
- 检测：ytdlp-notify check
- 守护/定时：ytdlp-notify daemon（或配合 cron）

## 17. 时间排期
- T+1d：接口联通、版本解析。
- T+2d：飞书卡片联通、幂等。
- T+3d：错误处理、文档与验收。
