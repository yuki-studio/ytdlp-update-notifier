import requests
import json
from src.utils import logger

class FeishuClient:
    def __init__(self, webhook_url, timeout=5000):
        self.webhook_url = webhook_url
        self.timeout = timeout / 1000.0

    def send_update_notification(self, latest_version, previous_version, release_url):
        previous_version_display = previous_version if previous_version else "无记录"
        
        # Construct the interactive card
        card_content = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "template": "blue",
                    "title": {
                        "tag": "plain_text",
                        "content": "yt-dlp 版本更新提示"
                    }
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"📦 **最新版本：** {latest_version}"
                        }
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"⏮️ **上一版本：** {previous_version_display}"
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "⚠️ 请及时迭代以保证产品正常运行"
                        }
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "点击查看 Release Notes"
                                },
                                "type": "primary",
                                "url": release_url
                            }
                        ]
                    }
                ]
            }
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=card_content,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                logger.error(f"Feishu API returned error: {result}")
                return False
            
            logger.info("Feishu notification sent successfully.")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Feishu notification: {e}")
            return False
