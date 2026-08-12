from __future__ import annotations

import os
from dataclasses import dataclass, field

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGETS_DIR = os.path.join(BASE_DIR, "targets")
DEBUG_DIR = os.path.join(BASE_DIR, "debug")

# Named UI Layout Constants & Region Offsets
STAMINA_CROP_XMIN_OFFSET = 180
STAMINA_CROP_XMAX_OFFSET = 45
STAMINA_CROP_Y_OFFSET = 18
DEFAULT_FALLBACK_CENTER_X = 960
DEFAULT_FALLBACK_CENTER_Y = 540

# Load environment variables from .env file if available
env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file):
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(env_file)
    except ImportError:
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip("'\""))

# Ensure debug directory exists
os.makedirs(DEBUG_DIR, exist_ok=True)

# Game Version & Direct Landing Configuration
GAME_VERSION = os.environ.get("GAME_VERSION", "auto").lower()  # Supported: "auto", "v13d", "v10l"

if "DIRECT_TREASURE_URL" in os.environ:
    DIRECT_TREASURE_URL = os.environ["DIRECT_TREASURE_URL"]
else:
    if GAME_VERSION == "v10l":
        DIRECT_TREASURE_URL = "https://game.bombcrypto.io/web/v10l/index.html"
    else:
        DIRECT_TREASURE_URL = "https://game.bombcrypto.io/web/v13d/index.html?landing=treasure"

if "DIRECT_LANDING_MODE" in os.environ:
    DIRECT_LANDING_MODE = os.environ["DIRECT_LANDING_MODE"].lower() in (
        "true",
        "1",
        "yes",
    )
else:
    # v13d directly targets Treasure Hunt URL; v10l requires main menu Treasure Hunt button click
    DIRECT_LANDING_MODE = GAME_VERSION != "v10l"

TARGET_BROWSER = (
    os.environ.get("TARGET_BROWSER", "brave").lower()
)  # Target browser: "brave", "chrome", "firefox", "edge", "opera", "vivaldi", "default", "auto"
BROWSER_EXECUTABLE_PATH = os.environ.get(
    "BROWSER_EXECUTABLE_PATH", ""
)  # Custom browser executable path
AUTO_LAUNCH_BROWSER = os.environ.get("AUTO_LAUNCH_BROWSER", "true").lower() in (
    "true",
    "1",
    "yes",
)  # Automatically launch browser with direct game URL if not running
AUTO_LAUNCH_BRAVE = AUTO_LAUNCH_BROWSER  # Backward compatibility alias

# Vision & Debugging Settings
DEFAULT_MATCH_THRESHOLD = float(
    os.environ.get("DEFAULT_MATCH_THRESHOLD", "0.70")
)  # Accurate match threshold (prevents false positives)
SCREENSHOT_MONITOR_INDEX = int(
    os.environ.get("SCREENSHOT_MONITOR_INDEX", "1")
)  # Monitor index (1 for primary monitor in mss, 0 for all combined)
SAVE_DEBUG_IMAGES = os.environ.get("SAVE_DEBUG_IMAGES", "true").lower() in (
    "true",
    "1",
    "yes",
)  # Saves debug_last_screen.png and debug_last_match.png inside debug/ folder
LOG_FILE_PATH = os.path.join(DEBUG_DIR, "bot_activity.log")

# Human-like Interaction Settings
MOUSE_CLICK_OFFSET = int(
    os.environ.get("MOUSE_CLICK_OFFSET", "5")
)  # Random offset +/- pixels from center
MIN_CLICK_DURATION = float(
    os.environ.get("MIN_CLICK_DURATION", "0.08")
)  # Minimum mouse move time (seconds)
MAX_CLICK_DURATION = float(
    os.environ.get("MAX_CLICK_DURATION", "0.20")
)  # Maximum mouse move time (seconds)
MIN_ACTION_DELAY = float(
    os.environ.get("MIN_ACTION_DELAY", "1.0")
)  # Min delay between UI clicks (seconds)
MAX_ACTION_DELAY = float(
    os.environ.get("MAX_ACTION_DELAY", "2.5")
)  # Max delay between UI clicks (seconds)

# Anti-Detection & Humanization Settings
USE_BEZIER_CURVES = os.environ.get("USE_BEZIER_CURVES", "true").lower() in (
    "true",
    "1",
    "yes",
)  # Non-linear smooth cursor movement paths
BEZIER_MIN_STEPS = int(os.environ.get("BEZIER_MIN_STEPS", "5"))  # Minimum steps for curve movement
USE_GAUSSIAN_DELAYS = os.environ.get("USE_GAUSSIAN_DELAYS", "true").lower() in (
    "true",
    "1",
    "yes",
)  # Gaussian/normal distribution reaction delays
ENABLE_IDLE_JITTER = os.environ.get("ENABLE_IDLE_JITTER", "true").lower() in (
    "true",
    "1",
    "yes",
)  # Periodic subtle mouse movement while resting
IDLE_JITTER_INTERVAL_SECONDS = float(
    os.environ.get("IDLE_JITTER_INTERVAL_SECONDS", "30")
)  # Minimum seconds between anti-AFK mouse jitters
IDLE_JITTER_MAX_OFFSET = int(
    os.environ.get("IDLE_JITTER_MAX_OFFSET", "15")
)  # Max pixel variation for idle jitter

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("true", "1", "yes")
ENABLE_NOTIFICATIONS = os.environ.get("ENABLE_NOTIFICATIONS", "true").lower() in (
    "true",
    "1",
    "yes",
)
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Bot Logic Timers
HERO_WORK_INTERVAL_MINUTES = float(
    os.environ.get("HERO_WORK_INTERVAL_MINUTES", "30")
)  # Time to sleep while heroes mine / recover stamina
ERROR_CHECK_INTERVAL_SECONDS = float(
    os.environ.get("ERROR_CHECK_INTERVAL_SECONDS", "15")
)  # Frequency to scan for game errors/disconnects
MAX_STUCK_TIMEOUT_MINUTES = float(
    os.environ.get("MAX_STUCK_TIMEOUT_MINUTES", "10")
)  # Refresh page if stuck in same screen state

# Inner Bot & Refresh Options (For game's native inner bot)
ONLY_REFRESH_ON_ERROR = os.environ.get("ONLY_REFRESH_ON_ERROR", "").lower() in (
    "true",
    "1",
    "yes",
)  # When True, only refreshes page when error/disconnect popups are found
REFRESH_INTERVAL_MINUTES = float(
    os.environ.get("REFRESH_INTERVAL_MINUTES", "0.0")
)  # Periodic page refresh interval in minutes to unstuck heroes (0.0 = disabled)
ENABLE_HERO_WORK_ACTIONS = os.environ.get("ENABLE_HERO_WORK_ACTIONS", "true").lower() in (
    "true",
    "1",
    "yes",
)  # Enable manual hero work clicking in hero menu (set to False when using inner bot)

# Hero Work Selection & Stamina Mode Settings (Default: stamina mode with min 60% threshold)
HERO_WORK_MODE = os.environ.get(
    "HERO_WORK_MODE", "stamina"
).lower()  # Options: "stamina" (default), "all"
WORK_ONLY_STAMINA = HERO_WORK_MODE != "all" and os.environ.get(
    "WORK_ONLY_STAMINA", "true"
).lower() in ("true", "1", "yes")
HERO_MIN_STAMINA = float(
    os.environ.get("HERO_MIN_STAMINA", "60")
)  # Default min stamina threshold (60%)
HERO_MODAL_MAX_SCROLLS = int(
    os.environ.get("HERO_MODAL_MAX_SCROLLS", "4")
)  # Number of scroll passes in hero modal

# Home Strategy Settings (Prioritize resting higher tier heroes at home for faster stamina load)
ENABLE_HOME_STRATEGY = os.environ.get("ENABLE_HOME_STRATEGY", "true").lower() in (
    "true",
    "1",
    "yes",
)

STAMINA_TARGETS_DIR = os.path.join(TARGETS_DIR, "staminas")
TIERS_DIR = os.path.join(TARGETS_DIR, "tiers")

# Priority ranking for hero tiers (higher integer = higher priority)
TIER_PRIORITIES = {
    "super_legendary": 6,
    "legendary": 5,
    "epic": 4,
    "super_rare": 3,
    "rare": 2,
    "common": 1,
}


# Target Image Filenames
TARGET_IMAGES = {
    "connect_wallet": os.path.join(TARGETS_DIR, "connect_wallet.png"),
    "select_metamask": os.path.join(TARGETS_DIR, "select_metamask.png"),
    "metamask_sign": os.path.join(TARGETS_DIR, "confirm_metamask.png"),
    "confirm_profile_ok": os.path.join(TARGETS_DIR, "confirm_profile.png"),
    "bottom_arrow": os.path.join(TARGETS_DIR, "arrow_menu_button.png"),
    "heroes_button": os.path.join(TARGETS_DIR, "heroes_icon.png"),
    "work_all_button": os.path.join(TARGETS_DIR, "work_all_button.png"),
    "work_button": os.path.join(TARGETS_DIR, "work_button.png"),
    "rest_all_button": os.path.join(TARGETS_DIR, "rest_all_button.png"),
    "available_home": os.path.join(TARGETS_DIR, "available_home.png"),
    "without_space_home": os.path.join(TARGETS_DIR, "without_space_home.png"),
    "full_bar": os.path.join(TARGETS_DIR, "full_bar.png"),
    "80_bar": os.path.join(TARGETS_DIR, "80_bar.png"),
    "close_button": os.path.join(TARGETS_DIR, "close_button.png"),
    "treasure_hunt_icon": (
        os.path.join(TARGETS_DIR, "treasure_hunt_button.png")
        if os.path.exists(os.path.join(TARGETS_DIR, "treasure_hunt_button.png"))
        else os.path.join(TARGETS_DIR, "treasure_hunt_icon.png")
    ),
    "treasure_hunt_button": os.path.join(TARGETS_DIR, "treasure_hunt_button.png"),
    "back_button": os.path.join(TARGETS_DIR, "back_button.png"),
    "error_ok": os.path.join(TARGETS_DIR, "error_ok.png"),
    "error_message": os.path.join(TARGETS_DIR, "error_message.png"),
    "unknown_error": os.path.join(TARGETS_DIR, "unknown_error.png"),
    "map_complete": os.path.join(TARGETS_DIR, "map_complete.png"),
    "map_complete_button": os.path.join(TARGETS_DIR, "map_complete_button.png"),
    "captcha_popup": os.path.join(TARGETS_DIR, "captcha_popup.png"),
    "captcha_verify": os.path.join(TARGETS_DIR, "captcha_verify.png"),
    "captcha_ok": os.path.join(TARGETS_DIR, "captcha_ok.png"),
}

# Per-Target Vision Thresholds (Phase 2)
TARGET_THRESHOLDS = {
    "connect_wallet": 0.70,
    "select_metamask": 0.70,
    "metamask_sign": 0.70,
    "confirm_profile_ok": 0.75,
    "bottom_arrow": 0.70,
    "heroes_button": 0.70,
    "work_all_button": 0.75,
    "work_button": 0.70,
    "rest_all_button": 0.75,
    "available_home": 0.70,
    "without_space_home": 0.70,
    "full_bar": 0.70,
    "80_bar": 0.70,
    "close_button": 0.70,
    "treasure_hunt_icon": 0.70,
    "treasure_hunt_button": 0.70,
    "back_button": 0.70,
    "error_ok": 0.75,
    "error_message": 0.70,
    "unknown_error": 0.70,
    "map_complete": 0.70,
    "map_complete_button": 0.70,
    "captcha_popup": 0.70,
    "captcha_verify": 0.70,
    "captcha_ok": 0.75,
}

# Per-Target Regions of Interest (ROI) (Phase 2)
# Formats supported: (ymin, xmin, ymax, xmax) normalized floats 0.0-1.0 or (x, y, w, h) pixels
TARGET_ROIS = {
    "bottom_arrow": (0.60, 0.0, 1.0, 1.0),
    "heroes_button": (0.50, 0.0, 1.0, 1.0),
    "connect_wallet": (0.0, 0.0, 1.0, 1.0),
    "confirm_profile_ok": (0.0, 0.0, 1.0, 1.0),
    "work_all_button": (0.15, 0.15, 0.85, 0.85),
    "work_button": (0.15, 0.15, 0.85, 0.85),
    "rest_all_button": (0.15, 0.15, 0.85, 0.85),
    "available_home": (0.15, 0.15, 0.85, 0.85),
    "without_space_home": (0.15, 0.15, 0.85, 0.85),
    "full_bar": (0.15, 0.15, 0.85, 0.85),
    "80_bar": (0.15, 0.15, 0.85, 0.85),
    "close_button": (0.0, 0.0, 1.0, 1.0),
    "map_complete": (0.10, 0.10, 0.90, 0.90),
    "map_complete_button": (0.30, 0.10, 0.95, 0.90),
}


@dataclass
class BotConfig:
    """Encapsulated Bot Configuration Dataclass."""

    game_version: str = GAME_VERSION
    direct_treasure_url: str = DIRECT_TREASURE_URL
    direct_landing_mode: bool = DIRECT_LANDING_MODE
    target_browser: str = TARGET_BROWSER
    browser_executable_path: str = BROWSER_EXECUTABLE_PATH
    auto_launch_browser: bool = AUTO_LAUNCH_BROWSER
    default_match_threshold: float = DEFAULT_MATCH_THRESHOLD
    screenshot_monitor_index: int = SCREENSHOT_MONITOR_INDEX
    save_debug_images: bool = SAVE_DEBUG_IMAGES
    mouse_click_offset: int = MOUSE_CLICK_OFFSET
    min_click_duration: float = MIN_CLICK_DURATION
    max_click_duration: float = MAX_CLICK_DURATION
    min_action_delay: float = MIN_ACTION_DELAY
    max_action_delay: float = MAX_ACTION_DELAY
    use_bezier_curves: bool = USE_BEZIER_CURVES
    bezier_min_steps: int = BEZIER_MIN_STEPS
    use_gaussian_delays: bool = USE_GAUSSIAN_DELAYS
    enable_idle_jitter: bool = ENABLE_IDLE_JITTER
    idle_jitter_interval_seconds: float = IDLE_JITTER_INTERVAL_SECONDS
    idle_jitter_max_offset: int = IDLE_JITTER_MAX_OFFSET
    dry_run: bool = DRY_RUN
    enable_notifications: bool = ENABLE_NOTIFICATIONS
    discord_webhook_url: str = DISCORD_WEBHOOK_URL
    telegram_bot_token: str = TELEGRAM_BOT_TOKEN
    telegram_chat_id: str = TELEGRAM_CHAT_ID
    hero_work_interval_minutes: float = HERO_WORK_INTERVAL_MINUTES
    error_check_interval_seconds: float = ERROR_CHECK_INTERVAL_SECONDS
    max_stuck_timeout_minutes: float = MAX_STUCK_TIMEOUT_MINUTES
    only_refresh_on_error: bool = ONLY_REFRESH_ON_ERROR
    refresh_interval_minutes: float = REFRESH_INTERVAL_MINUTES
    enable_hero_work_actions: bool = ENABLE_HERO_WORK_ACTIONS
    hero_work_mode: str = HERO_WORK_MODE
    work_only_stamina: bool = WORK_ONLY_STAMINA
    hero_min_stamina: float = HERO_MIN_STAMINA
    hero_modal_max_scrolls: int = HERO_MODAL_MAX_SCROLLS
    enable_home_strategy: bool = ENABLE_HOME_STRATEGY

    # Added fields
    target_images: dict = field(default_factory=lambda: TARGET_IMAGES)
    target_thresholds: dict = field(default_factory=lambda: TARGET_THRESHOLDS)
    target_rois: dict = field(default_factory=lambda: TARGET_ROIS)
    debug_dir: str = DEBUG_DIR
    targets_dir: str = TARGETS_DIR
    stamina_crop_xmin_offset: int = STAMINA_CROP_XMIN_OFFSET
    stamina_crop_xmax_offset: int = STAMINA_CROP_XMAX_OFFSET
    stamina_crop_y_offset: int = STAMINA_CROP_Y_OFFSET
    stamina_y_tolerance: int = 25
    stamina_min_distance: int = 30

    def get_target_key(self, target_name_or_path: str) -> str:
        if not target_name_or_path:
            return ""
        if target_name_or_path in self.target_images:
            return target_name_or_path
        base = os.path.basename(target_name_or_path)
        filename, _ = os.path.splitext(base)
        for key, path in self.target_images.items():
            if path == target_name_or_path or key == filename:
                return key
        return filename

    def get_target_threshold(self, target_name_or_path: str) -> float:
        key = self.get_target_key(target_name_or_path)
        return self.target_thresholds.get(key, self.default_match_threshold)

    def get_target_roi(self, target_name_or_path: str):
        key = self.get_target_key(target_name_or_path)
        return self.target_rois.get(key, None)

    def load_stamina_targets(self, min_stamina=None):
        if min_stamina is None:
            min_stamina = self.hero_min_stamina
        targets = []
        stamina_dir = os.path.join(self.targets_dir, "staminas")
        if not os.path.exists(stamina_dir):
            return targets
        for fname in os.listdir(stamina_dir):
            if not fname.endswith(".png"):
                continue
            name_no_ext = fname.rsplit(".", 1)[0].lower()
            if name_no_ext == "full":
                pct = 100.0
            else:
                try:
                    pct = float(name_no_ext)
                except ValueError:
                    continue
            if pct >= min_stamina:
                targets.append((os.path.join(stamina_dir, fname), pct))
        targets.sort(key=lambda x: x[1], reverse=True)
        return targets

    def load_tier_targets(self):
        targets = []
        tiers_dir = os.path.join(self.targets_dir, "tiers")
        if not os.path.exists(tiers_dir):
            return targets
        for fname in os.listdir(tiers_dir):
            if not fname.endswith(".png"):
                continue
            tier_name = fname.rsplit(".", 1)[0].lower()
            priority = TIER_PRIORITIES.get(tier_name, 0)
            targets.append((os.path.join(tiers_dir, fname), tier_name, priority))
        targets.sort(key=lambda x: x[2], reverse=True)
        return targets
