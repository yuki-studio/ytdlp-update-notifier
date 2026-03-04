# PRD: yt-dlp Release Monitoring and Feishu Notification

## 1. Background and Goal
This project monitors official `yt-dlp` releases and notifies stakeholders through Feishu when a new version is published.

Goals:
- Detect the latest official release from `yt-dlp/yt-dlp` on GitHub.
- Compare with the previously stored version.
- Send a structured Feishu notification when a new version is found.
- Minimize false negatives (missed notifications).

## 2. Users and Scenarios
Primary users:
- Product managers
- Developers
- Operations engineers

Main scenarios:
- Scheduled checks in GitHub Actions.
- Manual checks from CLI.
- Manual webhook validation via `test-notify`.

## 3. Scope and Non-Goals
In scope:
- GitHub release query
- Version comparison
- State persistence
- Feishu webhook notification

Out of scope:
- Auto-upgrading dependent systems
- Compatibility testing of downstream products
- Changelog summarization

## 4. Data Source and Parsing Rules
Primary API:
- `GET https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest`

Parsing priority:
1. `tag_name`
2. `name` (fallback)

Normalization:
- Strip leading `v` from version tags when present.

## 5. Trigger Strategy
- GitHub Actions schedule: every 4 hours.
- Manual trigger from Actions UI.
- Manual local command.

Commands:
- `python -m src.main check`
- `python -m src.main daemon`
- `python -m src.main test-notify`

## 6. Configuration
`config.yaml` includes:
- `github.repo`
- `github.timeout`
- `check.cron`
- `check.initial_push`
- `feishu.webhook`
- `feishu.timeout`
- `storage.path`

## 7. Storage
State file: `.state/last_version.json`

Fields:
- `last_version`
- `last_checked_at`

## 8. Notification Design
Feishu interactive card fields:
- Title: `yt-dlp Update Alert`
- Latest version
- Previous version (or `No previous record`)
- Action button to open release notes

## 9. End-to-End Flow
1. Load config.
2. Query GitHub latest release.
3. Load previous state.
4. Compare versions.
5. Send Feishu message if version changed.
6. Persist new state only after successful send.

## 10. Reliability and Retry Behavior
- If GitHub request fails, log error and exit current run.
- If Feishu send fails, do not update state to allow retry on next run.
- In CI mode, if state is missing unexpectedly, do not silently skip first notification.

## 11. Security
- Keep webhook in GitHub secret `FEISHU_WEBHOOK`.
- Environment variable can override local config value.

## 12. Acceptance Criteria
- New official `yt-dlp` release triggers notification.
- Repeated checks on same version do not duplicate notifications.
- Missing state in CI does not cause silent missed alerts.
- `test-notify` can send a manual validation message.
