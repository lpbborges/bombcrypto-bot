from __future__ import annotations

import sys
import types


def ensure_mouseinfo_mocked() -> None:
    """Preemptively mock mouseinfo to prevent mouseinfo's missing-tkinter sys.exit() call."""
    if "mouseinfo" not in sys.modules:
        dummy_mouseinfo = types.ModuleType("mouseinfo")
        dummy_mouseinfo.MouseInfoWindow = lambda *a, **k: None
        sys.modules["mouseinfo"] = dummy_mouseinfo
