from __future__ import annotations

import os
import shutil
import subprocess
import webbrowser

from config import BotConfig
from modules import platform_utils
from modules.logger import logger

# Known executable paths per browser type across platforms
KNOWN_BROWSER_PATHS = {
    "brave": {
        "linux": [
            "/opt/brave.com/brave-origin-beta/brave",
            "/opt/brave.com/brave/brave",
            "/usr/bin/brave-browser",
            "/usr/bin/brave",
            "/usr/bin/brave-beta",
            "/snap/bin/brave",
            "/snap/bin/brave-browser",
        ],
        "darwin": [
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Brave Browser Beta.app/Contents/MacOS/Brave Browser Beta",
        ],
        "win32": [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ],
        "commands": ["brave-browser", "brave", "brave-beta"],
    },
    "chrome": {
        "linux": [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/snap/bin/chromium",
        ],
        "darwin": [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ],
        "win32": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ],
        "commands": ["google-chrome", "chrome", "chromium", "google-chrome-stable"],
    },
    "firefox": {
        "linux": [
            "/usr/bin/firefox",
            "/usr/bin/firefox-developer-edition",
            "/snap/bin/firefox",
        ],
        "darwin": [
            "/Applications/Firefox.app/Contents/MacOS/firefox",
        ],
        "win32": [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        ],
        "commands": ["firefox"],
    },
    "edge": {
        "linux": [
            "/usr/bin/microsoft-edge",
            "/usr/bin/microsoft-edge-stable",
        ],
        "darwin": [
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ],
        "win32": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "commands": ["microsoft-edge", "msedge", "microsoft-edge-stable"],
    },
}


class BrowserManager:
    @classmethod
    def get_target_browser_name(cls) -> str:
        """Returns normalized target browser type string from config."""
        browser_type = getattr(cls.config, "target_browser", "brave").lower()
        if browser_type in ("auto", "default", ""):
            return "brave"
        return browser_type

    @classmethod
    def get_attached_browser_info(cls):
        """
        Detects active browser processes across Linux, macOS, and Windows.
        Returns: dict: { 'name': str, 'pid': str, 'exe': str, 'status': str }
        """
        target_name = BrowserManager.get_target_browser_name()

        browser_targets = [
            (
                "Brave Browser",
                ["brave-origin-beta", "brave-browser", "brave"],
            ),
            ("Google Chrome / Chromium", ["google-chrome", "chrome", "chromium"]),
            ("Mozilla Firefox", ["firefox"]),
            ("Microsoft Edge", ["msedge", "edge", "microsoft-edge"]),
            ("Opera Browser", ["opera"]),
            ("Vivaldi Browser", ["vivaldi"]),
        ]
        ignore_terms = [
            "crashpad",
            "renderer",
            "utility",
            "zygote",
            "sandbox",
            "type=",
            "grep",
            "helper",
        ]

        # 1. Attempt process search using platform-appropriate mechanism
        try:
            if platform_utils.is_windows():
                # Windows tasklist process table query
                proc = subprocess.run(
                    ["tasklist", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines():
                        line_clean = line.replace('"', "").lower()
                        for bname, keywords in browser_targets:
                            if any(k in line_clean for k in keywords):
                                parts = [p.strip('"') for p in line.split('","')]
                                pid = parts[1] if len(parts) > 1 else "N/A"
                                exe_path = parts[0] if len(parts) > 0 else bname
                                return {
                                    "name": bname,
                                    "pid": pid,
                                    "exe": exe_path,
                                    "status": "ATTACHED & RUNNING",
                                }
            else:
                # POSIX (Linux / macOS) ps command process search
                output = subprocess.check_output(["ps", "-eo", "pid,comm,args"], text=True)
                for bname, keywords in browser_targets:
                    for line in output.splitlines():
                        line_lower = line.lower()
                        if any(k in line_lower for k in keywords) and not any(
                            term in line_lower for term in ignore_terms
                        ):
                            parts = line.strip().split(None, 2)
                            if len(parts) >= 3:
                                pid, _, args = parts[0], parts[1], parts[2]
                                exe_path = args.split()[0]
                                return {
                                    "name": bname,
                                    "pid": pid,
                                    "exe": exe_path,
                                    "status": "ATTACHED & RUNNING",
                                }
        except Exception as e:
            logger.debug(f"[BROWSER] Notice querying process table: {e}")

        # 2. If browser executable is specified or found on system but not running
        exe = BrowserManager.find_browser_executable(target_name)
        if exe:
            return {
                "name": f"{target_name.capitalize()} Browser",
                "pid": "N/A",
                "exe": exe,
                "status": "NOT RUNNING (Auto-launch enabled)",
            }

        return {
            "name": "Unknown / Manual Browser",
            "pid": "N/A",
            "exe": "N/A",
            "status": "WAITING FOR BROWSER",
        }

    @classmethod
    def is_browser_running(cls) -> bool:
        """Checks if a supported browser process is currently active on the system."""
        info = BrowserManager.get_attached_browser_info()
        return info.get("status") == "ATTACHED & RUNNING"

    @classmethod
    def is_brave_running(cls) -> bool:
        """Backward compatible check for Brave browser."""
        info = BrowserManager.get_attached_browser_info()
        return info.get("status") == "ATTACHED & RUNNING"

    @classmethod
    def find_browser_executable(cls, browser_type: str = None) -> str:
        """
        Locates the absolute path of the specified browser binary on the system.
        Supports custom override via BROWSER_EXECUTABLE_PATH or environment variable.
        """
        # 1. Custom path override check
        custom_path = getattr(cls.config, "browser_executable_path", "").strip()
        if custom_path and os.path.exists(custom_path) and os.access(custom_path, os.X_OK):
            return custom_path

        if not browser_type:
            browser_type = BrowserManager.get_target_browser_name()

        browser_type = browser_type.lower()
        if browser_type not in KNOWN_BROWSER_PATHS:
            browser_type = "brave"

        platform_key = (
            "win32"
            if platform_utils.is_windows()
            else ("darwin" if platform_utils.is_mac() else "linux")
        )
        paths_to_check = KNOWN_BROWSER_PATHS[browser_type].get(platform_key, [])

        for path in paths_to_check:
            if os.path.exists(path) and (platform_utils.is_windows() or os.access(path, os.X_OK)):
                return path

        for cmd in KNOWN_BROWSER_PATHS[browser_type].get("commands", []):
            found = shutil.which(cmd)
            if found:
                return found

        return None

    @classmethod
    def find_brave_executable(cls) -> str:
        """Backward compatible helper to find Brave executable."""
        return BrowserManager.find_browser_executable("brave")

    @classmethod
    def launch_browser(cls, url: str = None, browser_type: str = None) -> bool:
        """
        Launches the configured browser with the direct game landing URL.
        """
        if not browser_type:
            browser_type = BrowserManager.get_target_browser_name()

        if browser_type == "default":
            logger.info(f"[BROWSER] Opening default system web browser -> {url}")
            return webbrowser.open(url)

        exe = BrowserManager.find_browser_executable(browser_type)
        if exe:
            logger.info(f"[BROWSER] Launching {browser_type.capitalize()} browser ({exe}) -> {url}")
            try:
                subprocess.Popen([exe, url])
                return True
            except Exception as e:
                logger.error(f"[BROWSER] Failed to launch browser process: {e}")
                return False
        else:
            logger.warning(
                f"[BROWSER] Could not locate binary for target browser '{browser_type}'. "
                "Attempting system default browser fallback..."
            )
            return webbrowser.open(url)

    @classmethod
    def launch_brave(cls, url: str = None) -> bool:
        """Backward compatible helper to launch Brave."""
        return BrowserManager.launch_browser(url, "brave")

    @classmethod
    def verify_and_ensure_browser(cls) -> bool:
        """
        Verifies browser status. If target browser is not running, attempts auto-launch.
        """
        info = BrowserManager.get_attached_browser_info()
        if info["status"] == "ATTACHED & RUNNING":
            return True

        logger.info(
            f"[BROWSER] Target browser ({BrowserManager.get_target_browser_name().capitalize()}) "
            "is not currently running. Launching browser automatically..."
        )
        return BrowserManager.launch_browser()

    @classmethod
    def verify_and_ensure_brave(cls) -> bool:
        """Backward compatible helper to verify and launch browser."""
        return BrowserManager.verify_and_ensure_browser()

    @classmethod
    def get_url_from_process_args(cls) -> str | None:
        """Inspects command-line arguments of active browser processes for game URLs."""
        try:
            if platform_utils.is_windows():
                cmd = [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'bombcrypto|v13d|v10l'} | Select-Object -ExpandProperty CommandLine",
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines():
                        for token in line.split():
                            clean_token = token.strip("'\"")
                            if any(
                                k in clean_token.lower() for k in ["bombcrypto", "v13d", "v10l"]
                            ):
                                return clean_token
            else:
                output = subprocess.check_output(["ps", "-eo", "pid,comm,args"], text=True)
                for line in output.splitlines():
                    if any(
                        b in line.lower()
                        for b in ["chrome", "brave", "firefox", "edge", "opera", "vivaldi"]
                    ):
                        for token in line.split():
                            clean_token = token.strip("'\"")
                            if any(
                                k in clean_token.lower() for k in ["bombcrypto", "v13d", "v10l"]
                            ) and not clean_token.startswith("--"):
                                return clean_token
        except Exception as e:
            logger.debug(f"[BROWSER] Notice scanning process arguments: {e}")
        return None

    @classmethod
    def get_browser_window_title(cls) -> str:
        """Gets window title string of active browser window."""
        if platform_utils.is_linux():
            if shutil.which("hyprctl"):
                try:
                    proc = subprocess.run(
                        ["hyprctl", "clients", "-j"], capture_output=True, text=True, timeout=2
                    )
                    if proc.returncode == 0:
                        import json

                        clients = json.loads(proc.stdout)
                        for c in clients:
                            cls = c.get("class", "").lower()
                            title = c.get("title", "")
                            if any(
                                b in cls
                                for b in [
                                    "chrome",
                                    "brave",
                                    "firefox",
                                    "edge",
                                    "opera",
                                    "vivaldi",
                                    "chromium",
                                ]
                            ):
                                if title:
                                    return title
                except Exception as e:
                    logger.debug(f"Exception caught: {e}", exc_info=True)
            if shutil.which("xdotool"):
                try:
                    proc = subprocess.run(
                        ["xdotool", "getactivewindow", "getwindowname"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    if proc.returncode == 0 and proc.stdout.strip():
                        return proc.stdout.strip()
                except Exception as e:
                    logger.debug(f"Exception caught: {e}", exc_info=True)
        elif platform_utils.is_windows():
            try:
                cmd = [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-Process | Where-Object {$_.MainWindowTitle -and ($_.ProcessName -match 'chrome|brave|firefox|msedge')} | Select-Object -ExpandProperty MainWindowTitle",
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                if proc.returncode == 0 and proc.stdout.strip():
                    return proc.stdout.strip()
            except Exception as e:
                logger.debug(f"Exception caught: {e}", exc_info=True)
        elif platform_utils.is_mac():
            try:
                cmd = [
                    "osascript",
                    "-e",
                    'tell application "System Events" to get name of window 1 of (first process whose frontmost is true)',
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                if proc.returncode == 0 and proc.stdout.strip():
                    return proc.stdout.strip()
            except Exception as e:
                logger.debug(f"Exception caught: {e}", exc_info=True)

        return ""

    @classmethod
    def get_url_via_clipboard(cls) -> str | None:
        """
        Attempts to read URL directly from browser address bar by triggering Ctrl+L -> Ctrl+C.
        Restores original clipboard content after reading.
        """
        if getattr(cls.config, "dry_run", False):
            return None

        original_clip = get_clipboard_text()
        try:
            import time

            import pyautogui

            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.15)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.15)
            pyautogui.press("escape")

            new_clip = get_clipboard_text()
            if new_clip and new_clip != original_clip:
                if any(
                    k in new_clip.lower()
                    for k in ["bombcrypto", "v13d", "v10l", "http://", "https://"]
                ):
                    logger.info(f"[BROWSER] Retrieved URL from browser address bar: {new_clip}")
                    return new_clip
        except Exception as err:
            logger.debug(f"[BROWSER] Clipboard URL fetch notice: {err}")

        if original_clip and any(
            k in original_clip.lower() for k in ["bombcrypto", "v13d", "v10l"]
        ):
            return original_clip

        return None

    @classmethod
    def get_open_browser_url(cls, try_clipboard: bool = False) -> str | None:
        """
        Detects URL of the currently open browser tab using multiple detection strategies:
        1. Process command line arguments inspection.
        2. Active window title inspection.
        3. Address bar clipboard copy (optional/fallback).
        """
        # 1. Try process arguments
        url = BrowserManager.get_url_from_process_args()
        if url:
            return url

        # 2. Try window title if it contains full URL or game domain
        title = BrowserManager.get_browser_window_title()
        if title and (
            "http://" in title.lower()
            or "https://" in title.lower()
            or "bombcrypto.io" in title.lower()
        ):
            for token in title.split():
                if any(
                    k in token.lower()
                    for k in ["bombcrypto", "v13d", "v10l", "http://", "https://"]
                ):
                    return token.strip("'\"()")

        # 3. Try clipboard address bar fetch if enabled
        if try_clipboard:
            url = BrowserManager.get_url_via_clipboard()
            if url:
                return url

        # 4. Fallback check on current clipboard content
        clip_text = get_clipboard_text()
        if clip_text and any(
            k in clip_text.lower() for k in ["game.bombcrypto.io", "v13d", "v10l"]
        ):
            return clip_text

        return None

    @classmethod
    def detect_game_version(cls, try_clipboard: bool = False) -> str | None:
        """
        Detects game version ('v13d' or 'v10l') by examining the open browser URL and window title.
        Returns 'v13d', 'v10l', or None if undetected.
        """
        url = BrowserManager.get_open_browser_url(try_clipboard=try_clipboard)
        if url:
            url_lower = url.lower()
            if "v10l" in url_lower:
                return "v10l"
            if "v13d" in url_lower:
                return "v13d"

        title = BrowserManager.get_browser_window_title()
        if title:
            title_lower = title.lower()
            if "v10l" in title_lower:
                return "v10l"
            if "v13d" in title_lower:
                return "v13d"

        return None

    @classmethod
    def sync_game_version_from_browser(cls, try_clipboard: bool = False) -> str:
        """
        Auto-detects open browser URL/version and updates cls.config.game_version,
        cls.config.direct_treasure_url, and cls.config.direct_landing_mode accordingly.
        Returns the detected or active game version string.
        """
        detected_url = BrowserManager.get_open_browser_url(try_clipboard=try_clipboard)
        detected_ver = BrowserManager.detect_game_version(try_clipboard=try_clipboard)

        if detected_url:
            logger.info(f"[BROWSER] Detected open browser URL: {detected_url}")
            cls.config.direct_treasure_url = detected_url

        if detected_ver in ("v13d", "v10l"):
            old_ver = getattr(cls.config, "game_version", "v13d")
            cls.config.game_version = detected_ver
            cls.config.direct_landing_mode = detected_ver == "v13d"
            if old_ver != detected_ver:
                logger.info(
                    f"[BROWSER] Auto-detected Game Version: {old_ver} -> {detected_ver.upper()}"
                )
            else:
                logger.info(f"[BROWSER] Auto-detected Game Version: {detected_ver.upper()}")
            return detected_ver
        else:
            cur_ver = (
                getattr(cls.config, "game_version", "v13d")
                if getattr(cls.config, "game_version", "auto") != "auto"
                else "v13d"
            )
            cls.config.game_version = cur_ver
            cls.config.direct_landing_mode = cur_ver == "v13d"
            logger.info(f"[BROWSER] Could not auto-detect version. Using: {cur_ver.upper()}")
            return cur_ver


def get_clipboard_text() -> str:
    """Safely reads system clipboard text across Linux, macOS, and Windows."""
    try:
        import pyperclip

        text = pyperclip.paste()
        if text:
            return text.strip()
    except Exception as e:
        logger.debug(f"Exception caught: {e}", exc_info=True)

    if platform_utils.is_linux():
        if shutil.which("wl-paste"):
            try:
                return subprocess.check_output(
                    ["wl-paste", "--no-newline"], text=True, timeout=1
                ).strip()
            except Exception as e:
                logger.debug(f"Exception caught: {e}", exc_info=True)
        if shutil.which("xclip"):
            try:
                return subprocess.check_output(
                    ["xclip", "-selection", "clipboard", "-o"], text=True, timeout=1
                ).strip()
            except Exception as e:
                logger.debug(f"Exception caught: {e}", exc_info=True)
        if shutil.which("xsel"):
            try:
                return subprocess.check_output(["xsel", "-b", "-o"], text=True, timeout=1).strip()
            except Exception as e:
                logger.debug(f"Exception caught: {e}", exc_info=True)
    elif platform_utils.is_mac():
        try:
            return subprocess.check_output(["pbpaste"], text=True, timeout=1).strip()
        except Exception as e:
            logger.debug(f"Exception caught: {e}", exc_info=True)
    elif platform_utils.is_windows():
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-Clipboard"]
            return subprocess.check_output(cmd, text=True, timeout=2).strip()
        except Exception as e:
            logger.debug(f"Exception caught: {e}", exc_info=True)

    return ""


# Backward compatibility alias
BraveManager = BrowserManager
