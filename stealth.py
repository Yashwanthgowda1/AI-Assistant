"""
stealth.py — Makes the window invisible to screen-share / screen-capture tools.
Uses SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE) on Windows 10 2004+.
Falls back gracefully on older Windows or non-Windows platforms.
"""
import sys
import ctypes
import ctypes.wintypes
import logging

logger = logging.getLogger(__name__)

WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011   # Windows 10 build 2004+


def apply_stealth(hwnd: int) -> bool:
    """
    Hide *hwnd* from screen-capture APIs (Teams, Zoom, OBS, etc.).
    Returns True if the affinity was set successfully.
    """
    if sys.platform != "win32":
        logger.warning("Stealth mode is Windows-only.")
        return False
    try:
        user32 = ctypes.windll.user32
        ok = user32.SetWindowDisplayAffinity(
            ctypes.wintypes.HWND(hwnd),
            ctypes.c_uint32(WDA_EXCLUDEFROMCAPTURE)
        )
        if ok:
            logger.info("Stealth mode ACTIVE — window hidden from screen capture.")
        else:
            err = ctypes.get_last_error()
            logger.warning("SetWindowDisplayAffinity failed (err=%d). "
                           "Requires Windows 10 build 2004+.", err)
        return bool(ok)
    except Exception as exc:
        logger.exception("Stealth error: %s", exc)
        return False


def remove_stealth(hwnd: int) -> bool:
    """Restore normal capture visibility."""
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.windll.user32
        return bool(user32.SetWindowDisplayAffinity(
            ctypes.wintypes.HWND(hwnd),
            ctypes.c_uint32(WDA_NONE)
        ))
    except Exception:
        return False
