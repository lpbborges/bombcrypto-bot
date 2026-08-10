import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGETS_DIR = os.path.join(BASE_DIR, "targets")

# Direct Game Landing URL & Browser Settings
DIRECT_TREASURE_URL = "https://game.bombcrypto.io/web/v13d/index.html?landing=treasure"
DIRECT_LANDING_MODE = True     # When True, directly targets Treasure Hunt URL, skipping menu icon navigation
TARGET_BROWSER = "brave"       # Targeted browser ("brave")
AUTO_LAUNCH_BRAVE = True       # Automatically launch Brave with direct game URL if not running

# Vision & Debugging Settings
DEFAULT_MATCH_THRESHOLD = 0.70  # Accurate match threshold (prevents false positives)
SCREENSHOT_MONITOR_INDEX = 1   # 1 for primary monitor
SAVE_DEBUG_IMAGES = True       # Saves debug_last_screen.png and debug_last_match.png on every capture
LOG_FILE_PATH = os.path.join(BASE_DIR, "bot_activity.log")

# Human-like Interaction Settings
MOUSE_CLICK_OFFSET = 5          # Random offset +/- pixels from center
MIN_CLICK_DURATION = 0.2        # Minimum mouse move time (seconds)
MAX_CLICK_DURATION = 0.5        # Maximum mouse move time (seconds)
MIN_ACTION_DELAY = 1.0          # Min delay between UI clicks (seconds)
MAX_ACTION_DELAY = 2.5          # Max delay between UI clicks (seconds)

# Bot Logic Timers (in seconds)
HERO_WORK_INTERVAL_MINUTES = 30 # Time to sleep while heroes mine / recover stamina
ERROR_CHECK_INTERVAL_SECONDS = 15 # Frequency to scan for game errors/disconnects
MAX_STUCK_TIMEOUT_MINUTES = 10   # Refresh page if stuck in same screen state

# Target Image Filenames
TARGET_IMAGES = {
    "connect_wallet": os.path.join(TARGETS_DIR, "connect_wallet.png"),
    "select_metamask": os.path.join(TARGETS_DIR, "select_metamask.png"),
    "metamask_sign": os.path.join(TARGETS_DIR, "confirm_metamask.png"),
    "confirm_profile_ok": os.path.join(TARGETS_DIR, "confirm_profile.png"),
    "bottom_arrow": os.path.join(TARGETS_DIR, "arrow_menu_button.png"),
    "heroes_button": os.path.join(TARGETS_DIR, "heroes_icon.png"),
    "work_all_button": os.path.join(TARGETS_DIR, "work_all_button.png"),
    "close_button": os.path.join(TARGETS_DIR, "close_button.png"),
    "treasure_hunt_icon": os.path.join(TARGETS_DIR, "treasure_hunt_icon.png"),
    "back_button": os.path.join(TARGETS_DIR, "back_button.png"),
    "error_ok": os.path.join(TARGETS_DIR, "error_ok.png"),
    "unknown_error": os.path.join(TARGETS_DIR, "unknown_error.png"),
}
