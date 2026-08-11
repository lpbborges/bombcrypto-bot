import os
import shutil
import subprocess
import sys
import webbrowser

import config
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
    @staticmethod
    def get_target_browser_name() -> str:
        """Returns normalized target browser type string from config."""
        browser_type = getattr(config, "TARGET_BROWSER", "brave").lower()
        if browser_type in ("auto", "default", ""):
            return "brave"
        return browser_type

    @staticmethod
    def get_attached_browser_info():
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
            if sys.platform == "win32":
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

    @staticmethod
    def is_browser_running() -> bool:
        """Checks if a supported browser process is currently active on the system."""
        info = BrowserManager.get_attached_browser_info()
        return info.get("status") == "ATTACHED & RUNNING"

    @staticmethod
    def is_brave_running() -> bool:
        """Backward compatible check for Brave browser."""
        info = BrowserManager.get_attached_browser_info()
        return info.get("status") == "ATTACHED & RUNNING"

    @staticmethod
    def find_browser_executable(browser_type: str = None) -> str:
        """
        Locates the absolute path of the specified browser binary on the system.
        Supports custom override via BROWSER_EXECUTABLE_PATH or environment variable.
        """
        # 1. Custom path override check
        custom_path = getattr(config, "BROWSER_EXECUTABLE_PATH", "").strip()
        if custom_path and os.path.exists(custom_path) and os.access(custom_path, os.X_OK):
            return custom_path

        if not browser_type:
            browser_type = BrowserManager.get_target_browser_name()

        browser_type = browser_type.lower()
        if browser_type not in KNOWN_BROWSER_PATHS:
            browser_type = "brave"

        platform_key = (
            "win32"
            if sys.platform == "win32"
            else ("darwin" if sys.platform == "darwin" else "linux")
        )
        paths_to_check = KNOWN_BROWSER_PATHS[browser_type].get(platform_key, [])

        for path in paths_to_check:
            if os.path.exists(path) and (sys.platform == "win32" or os.access(path, os.X_OK)):
                return path

        for cmd in KNOWN_BROWSER_PATHS[browser_type].get("commands", []):
            found = shutil.which(cmd)
            if found:
                return found

        return None

    @staticmethod
    def find_brave_executable() -> str:
        """Backward compatible helper to find Brave executable."""
        return BrowserManager.find_browser_executable("brave")

    @staticmethod
    def launch_browser(url: str = config.DIRECT_TREASURE_URL, browser_type: str = None) -> bool:
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

    @staticmethod
    def launch_brave(url: str = config.DIRECT_TREASURE_URL) -> bool:
        """Backward compatible helper to launch Brave."""
        return BrowserManager.launch_browser(url, "brave")

    @staticmethod
    def verify_and_ensure_browser() -> bool:
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

    @staticmethod
    def verify_and_ensure_brave() -> bool:
        """Backward compatible helper to verify and launch browser."""
        return BrowserManager.verify_and_ensure_browser()


# Backward compatibility alias
BraveManager = BrowserManager
