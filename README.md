# yt-dlp Update Notifier

An automated notifier that monitors new releases in `yt-dlp/yt-dlp` and sends alerts to a Feishu bot webhook.

## What It Does
- Checks the latest official release from GitHub (`/releases/latest`).
- Compares the latest release version with the last recorded version.
- Sends a Feishu interactive card when a new version is detected.
- Supports one-time checks, daemon mode, and manual test notifications.
- Supports GitHub Actions for unattended cloud execution.

## Project Structure
```text
.
|-- .github/workflows/   # GitHub Actions workflow
|-- config.yaml          # Runtime configuration
|-- requirements.txt     # Python dependencies
|-- src/
|   |-- main.py          # CLI entrypoint
|   |-- github.py        # GitHub release client
|   |-- feishu.py        # Feishu webhook client
|   |-- storage.py       # State persistence
|   `-- utils.py         # Config and logging utilities
|-- docs/
|   `-- PRD.md
`-- .state/              # Runtime state files (auto-created)
```

## Configuration
Edit `config.yaml`:
- `github.repo`: target repository to monitor (default: `yt-dlp/yt-dlp`)
- `check.cron`: daemon schedule expression
- `check.initial_push`: whether to push notification when no previous record exists
- `feishu.webhook`: Feishu incoming webhook URL
- `storage.path`: local state file path

## Run Locally
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run a one-time check:
```bash
python -m src.main check
```

3. Run daemon mode:
```bash
python -m src.main daemon
```

4. Send a test notification directly:
```bash
python -m src.main test-notify
```

## GitHub Actions Deployment (Recommended)
1. Push this project to your GitHub repository.
2. Add repository secret `FEISHU_WEBHOOK` under:
   `Settings -> Secrets and variables -> Actions`.
3. Open `Actions -> Daily yt-dlp Check -> Run workflow`.
4. Choose command:
   - `check` for normal release detection
   - `test-notify` for webhook validation

The workflow is scheduled every 4 hours to reduce missed release windows.

## State and Idempotency
- State is stored in `.state/last_version.json`.
- If the latest version equals the saved version, no notification is sent.
- On send failure, state is not updated, so the next run can retry.
- In CI, if state is missing unexpectedly, notification is not silently skipped.

## Quick Troubleshooting
- No notification but run succeeded:
  - Check `Latest version` vs `Last version` in logs.
  - Confirm `FEISHU_WEBHOOK` secret exists and is valid.
  - Check logs for Feishu API errors.
- Local run fails with socket permission errors:
  - Your local firewall or endpoint policy is blocking outbound HTTPS.
  - Run from GitHub Actions to validate cloud-side behavior.
