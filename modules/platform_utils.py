from __future__ import annotations

import os
import sys


def is_windows() -> bool:
    return sys.platform == "win32"


def is_mac() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_wayland() -> bool:
    return is_linux() and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
