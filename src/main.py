import argparse
import schedule
import time
import sys
import os
from datetime import datetime
from src.utils import load_config, logger
from src.github import GitHubClient
from src.feishu import FeishuClient
from src.storage import Storage

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

def main():
    parser = argparse.ArgumentParser(description="yt-dlp Update Notifier")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Check command
    check_parser = subparsers.add_parser("check", help="Run a one-time check")
    
    # Daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Run in daemon mode")

    # Test notification command
    test_parser = subparsers.add_parser("test-notify", help="Send a test Feishu notification")

    args = parser.parse_args()

    config = load_config()

    # Allow environment variable to override webhook URL (for GitHub Actions security)
    env_webhook = os.environ.get("FEISHU_WEBHOOK")
    if env_webhook:
        config['feishu']['webhook'] = env_webhook

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
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
