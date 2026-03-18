import argparse
import json
import schedule
import time
import sys
import os
import subprocess
from datetime import datetime
from src.utils import load_config, logger
from src.github import GitHubClient
from src.feishu import FeishuClient
from src.storage import Storage


def mask_webhook(webhook_url):
    if not webhook_url:
        return "unset"
    return f"...{webhook_url[-8:]}"


def get_committed_state():
    try:
        result = subprocess.run(
            ["git", "show", "HEAD:.state/last_version.json"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"Failed to read committed state from git: {e}")
        return {}

def check_update(config):
    logger.info("Starting update check...")
    
    # Initialize clients
    github_client = GitHubClient(
        repo=config['github']['repo'],
        token=config['github'].get('token'),
        timeout=config['github'].get('timeout', 5000)
    )
    
    storage = Storage(config['storage']['path'])
    
    feishu_client = FeishuClient(
        webhook_url=config['feishu']['webhook'],
        timeout=config['feishu'].get('timeout', 5000)
    )

    # 1. Get latest release
    latest_release = github_client.get_latest_release()
    if not latest_release:
        logger.error("Failed to get latest release.")
        return

    latest_version = latest_release['version']
    release_url = latest_release['release_url']
    
    # 2. Get last version
    state = storage.load()
    last_version = state.get("last_version")
    last_notified_version = state.get("last_notified_version")
    
    logger.info(f"Latest version: {latest_version}, Last version: {last_version}")

    # 3. Compare
    if last_version == latest_version:
        logger.info("No new version found.")
        return

    # Deduplicate notifications by version.
    if last_notified_version == latest_version:
        logger.info(f"Version {latest_version} has already been notified. Skipping duplicate push.")
        storage.update_last_version(latest_version)
        return

    # 4. Notify
    # If it's the first run (last_version is None), check config to see if we should push
    initial_push = config['check'].get('initial_push', False)
    
    should_push = True
    if last_version is None and not initial_push:
        # In CI (GitHub Actions), state reset can happen due cache misses.
        # Override skip behavior to avoid silently missing a real release.
        if os.environ.get("CI", "").lower() == "true":
            logger.warning("State file missing in CI; overriding initial_push=false to send notification.")
        else:
            logger.info("First run and initial_push is false. Skipping notification.")
            should_push = False
    
    if should_push:
        success = feishu_client.send_update_notification(
            latest_version=latest_version,
            previous_version=last_version,
            release_url=release_url
        )
        if not success:
            logger.error("Failed to send notification. Will not update state to retry later.")
            return
        storage.mark_notified(latest_version)
        logger.info(f"Notification marked for version {latest_version}")
        return

    # 5. Update state
    storage.update_last_version(latest_version)
    logger.info(f"State updated to version {latest_version}")

def test_notify(config):
    logger.info("Sending test notification...")

    feishu_client = FeishuClient(
        webhook_url=config['feishu']['webhook'],
        timeout=config['feishu'].get('timeout', 5000)
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    release_url = f"https://github.com/{config['github']['repo']}/releases"
    success = feishu_client.send_update_notification(
        latest_version=f"TEST {now}",
        previous_version="MANUAL_TEST",
        release_url=release_url
    )

    if not success:
        logger.error("Failed to send test notification.")
        sys.exit(1)

    logger.info("Test notification sent successfully.")

def force_notify_latest(config):
    logger.info("Forcing notification for latest release...")

    github_client = GitHubClient(
        repo=config['github']['repo'],
        token=config['github'].get('token'),
        timeout=config['github'].get('timeout', 5000)
    )

    storage = Storage(config['storage']['path'])

    feishu_client = FeishuClient(
        webhook_url=config['feishu']['webhook'],
        timeout=config['feishu'].get('timeout', 5000)
    )

    latest_release = github_client.get_latest_release()
    if not latest_release:
        logger.error("Failed to get latest release.")
        sys.exit(1)

    latest_version = latest_release['version']
    release_url = latest_release['release_url']
    state = storage.load()
    previous_version = state.get("last_version")
    if previous_version == latest_version:
        committed_state = get_committed_state()
        previous_version = committed_state.get("last_version") or committed_state.get("last_notified_version")
    if previous_version == latest_version or not previous_version:
        previous_version = "MANUAL_RESEND"

    success = feishu_client.send_update_notification(
        latest_version=latest_version,
        previous_version=previous_version,
        release_url=release_url
    )

    if not success:
        logger.error("Failed to send forced notification.")
        sys.exit(1)

    storage.mark_notified(latest_version)
    logger.info(f"Forced notification sent and marked for version {latest_version}.")

def main():
    parser = argparse.ArgumentParser(description="yt-dlp Update Notifier")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Check command
    check_parser = subparsers.add_parser("check", help="Run a one-time check")
    
    # Daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Run in daemon mode")

    # Test notification command
    test_parser = subparsers.add_parser("test-notify", help="Send a test Feishu notification")

    # Force notification command
    force_parser = subparsers.add_parser("force-notify", help="Send the latest release notification regardless of saved state")

    args = parser.parse_args()

    config = load_config()

    # Prefer the committed config webhook so local runs and CI runs stay consistent.
    env_webhook = os.environ.get("FEISHU_WEBHOOK")
    config_webhook = config['feishu'].get('webhook')
    if config_webhook:
        if env_webhook and env_webhook != config_webhook:
            logger.warning(
                "FEISHU_WEBHOOK does not match config.yaml; using config webhook "
                f"{mask_webhook(config_webhook)} instead of environment webhook {mask_webhook(env_webhook)}"
            )
        else:
            logger.info(f"Using Feishu webhook from config: {mask_webhook(config_webhook)}")
    elif env_webhook:
        config['feishu']['webhook'] = env_webhook
        logger.info(f"Using Feishu webhook from environment fallback: {mask_webhook(env_webhook)}")
    else:
        logger.warning("No Feishu webhook configured.")

    if args.command == "check":
        check_update(config)
    elif args.command == "daemon":
        cron_expr = config['check'].get('cron', "0 9 * * *")
        # Simple schedule mapping for now since 'schedule' lib doesn't support full cron syntax directly
        # For simplicity in this demo, we'll just use "every day at 09:00" if the cron matches standard
        # Or just run periodically based on simple parsing. 
        # Since 'schedule' is simple, let's just support "every X minutes" or "daily at X"
        
        # NOTE: Parsing complex cron is hard without a library like 'croniter'. 
        # Given the requirements, I'll stick to a simple daily schedule or interval.
        # For now, let's just schedule it to run every hour as a fallback or parse the HH:MM
        
        logger.info(f"Starting daemon mode. Schedule: {cron_expr}")
        
        # Basic parsing for "0 9 * * *" -> Daily at 09:00
        parts = cron_expr.split()
        if len(parts) == 5 and parts[0] == "0" and parts[2] == "*" and parts[3] == "*" and parts[4] == "*":
             hour = parts[1].zfill(2)
             schedule.every().day.at(f"{hour}:00").do(check_update, config)
             logger.info(f"Scheduled to run daily at {hour}:00")
        elif cron_expr == "0 * * * *":
             schedule.every().hour.do(check_update, config)
             logger.info("Scheduled to run every hour.")
        else:
             # Default fallback: every hour
             schedule.every().hour.do(check_update, config)
             logger.info("Complex cron not fully supported in this demo version. Defaulting to every hour.")

        # Run once on startup
        check_update(config)
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in daemon loop: {e}")
                time.sleep(60)  # Wait a bit before retrying
    elif args.command == "test-notify":
        test_notify(config)
    elif args.command == "force-notify":
        force_notify_latest(config)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
