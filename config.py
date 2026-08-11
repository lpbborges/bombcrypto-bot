import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGETS_DIR = os.path.join(BASE_DIR, "targets")
DEBUG_DIR = os.path.join(BASE_DIR, "debug")

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

# Target Image Filenames
TARGET_IMAGES = {
    "connect_wallet": os.path.join(TARGETS_DIR, "connect_wallet.png"),
    "select_metamask": os.path.join(TARGETS_DIR, "select_metamask.png"),
    "metamask_sign": os.path.join(TARGETS_DIR, "confirm_metamask.png"),
    "confirm_profile_ok": os.path.join(TARGETS_DIR, "confirm_profile.png"),
    "bottom_arrow": os.path.join(TARGETS_DIR, "arrow_menu_button.png"),
    "heroes_button": os.path.join(TARGETS_DIR, "heroes_icon.png"),
    "work_all_button": os.path.join(TARGETS_DIR, "work_all_button.png"),
    "rest_all_button": os.path.join(TARGETS_DIR, "rest_all_button.png"),
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
    "rest_all_button": 0.75,
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
    "rest_all_button": (0.15, 0.15, 0.85, 0.85),
    "close_button": (0.0, 0.0, 1.0, 1.0),
    "map_complete": (0.10, 0.10, 0.90, 0.90),
    "map_complete_button": (0.30, 0.10, 0.95, 0.90),
}


def get_target_key(target_name_or_path: str) -> str:
    """Helper to resolve target_name_or_path to a standard target key."""
    if not target_name_or_path:
        return ""
    if target_name_or_path in TARGET_IMAGES:
        return target_name_or_path
    base = os.path.basename(target_name_or_path)
    filename, _ = os.path.splitext(base)
    for key, path in TARGET_IMAGES.items():
        if path == target_name_or_path or key == filename:
            return key
    return filename


def get_target_threshold(target_name_or_path: str) -> float:
    """Returns the per-template matching threshold from config or DEFAULT_MATCH_THRESHOLD."""
    key = get_target_key(target_name_or_path)
    return TARGET_THRESHOLDS.get(key, DEFAULT_MATCH_THRESHOLD)


def get_target_roi(target_name_or_path: str):
    """Returns the per-template Region of Interest (ROI) tuple or None."""
    key = get_target_key(target_name_or_path)
    return TARGET_ROIS.get(key, None)
