import json
import urllib.error
import urllib.request

import config
from modules.logger import logger


class NotificationManager:
    COLOR_MAP = {
        "info": 0x3498DB,
        "success": 0x2ECC71,
        "warning": 0xF1C40F,
        "error": 0xE74C3C,
    }

    @staticmethod
    def send_discord(title: str, message: str, level: str = "info"):
        webhook_url = getattr(config, "DISCORD_WEBHOOK_URL", "")
        if not webhook_url:
            return False

        color = NotificationManager.COLOR_MAP.get(level, 0x3498DB)
        payload = {
            "username": "Bomb Crypto Bot",
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": color,
                }
            ],
        }

        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "BombCryptoBot/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status in (200, 204):
                    logger.debug(f"[NOTIFICATION] Discord webhook sent: {title}")
                    return True
        except Exception as e:
            logger.warning(f"[NOTIFICATION] Failed to send Discord webhook: {e}")
        return False

    @staticmethod
    def send_telegram(title: str, message: str, level: str = "info"):
        token = getattr(config, "TELEGRAM_BOT_TOKEN", "")
        chat_id = getattr(config, "TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        text = f"🤖 *{title}*\n{message}"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    logger.debug(f"[NOTIFICATION] Telegram message sent: {title}")
                    return True
        except Exception as e:
            logger.warning(f"[NOTIFICATION] Failed to send Telegram notification: {e}")
        return False

    @classmethod
    def send_notification(cls, title: str, message: str, level: str = "info"):
        if not getattr(config, "ENABLE_NOTIFICATIONS", True):
            return

        cls.send_discord(title, message, level=level)
        cls.send_telegram(title, message, level=level)

    @classmethod
    def notify_hero_cycle(cls, details: str = "Heroes sent to work successfully."):
        cls.send_notification("Hero Work Cycle", details, level="success")

    @classmethod
    def notify_error_cleared(cls, error_name: str):
        cls.send_notification(
            "Error Popup Cleared", f"Cleared error state: {error_name}", level="warning"
        )

    @classmethod
    def notify_map_cleared(cls):
        cls.send_notification(
            "Map Cleared",
            "Treasure Hunt map completion detected! Transitioning map...",
            level="info",
        )

    @classmethod
    def notify_stuck_recovery(
        cls, details: str = "Bot stall threshold exceeded. Refreshing browser..."
    ):
        cls.send_notification("Anti-Stuck Recovery Triggered", details, level="error")
