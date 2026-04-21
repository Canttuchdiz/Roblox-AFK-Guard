from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import ctypes
    import pygetwindow as gw
    import psutil
    import win32api
    import win32con
    import win32gui
    import win32process
    import win32ui
    from PIL import Image
except ImportError:  # pragma: no cover - only hit when pywin32 not installed
    ctypes = None
    gw = None
    psutil = None
    win32api = None
    win32con = None
    win32gui = None
    win32process = None
    win32ui = None
    Image = None


ROBLOX_PROCESS_PREFIXES = ("Roblox", "RobloxPlayer")


@dataclass(frozen=True)
class WindowInfo:
    pid: int
    title: str
    width: int
    height: int
    bbox: tuple[int, int, int, int]
    hwnd: int = 0


def _proc_name(pid: int) -> str:
    if psutil is None:
        return ""
    try:
        return psutil.Process(pid).name()
    except psutil.Error:
        return ""


def list_roblox_windows() -> list[WindowInfo]:
    if gw is None:
        return []
    result: list[WindowInfo] = []
    for w in gw.getAllWindows():
        hwnd = getattr(w, "_hWnd", None)
        if not hwnd or not w.visible or w.width < 200 or w.height < 200:
            continue
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        name = _proc_name(pid)
        if not any(name.startswith(p) for p in ROBLOX_PROCESS_PREFIXES):
            continue
        result.append(
            WindowInfo(
                pid=pid,
                title=w.title or name,
                width=w.width,
                height=w.height,
                bbox=(w.left, w.top, w.width, w.height),
                hwnd=hwnd,
            )
        )
    return result


def focus_window(window: WindowInfo) -> None:
    if win32gui is None or not window.hwnd:
        return
    try:
        if win32gui.IsIconic(window.hwnd):
            win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(window.hwnd)
    except Exception:
        # SetForegroundWindow can fail silently if the calling thread doesn't own
        # the foreground; nothing actionable to do from here.
        pass


# PW_RENDERFULLCONTENT — captures DWM-composited / GPU-rendered window contents
# even when the window is obscured. Requires Windows 8.1+.
_PW_RENDERFULLCONTENT = 0x00000002


def capture_window(window: WindowInfo) -> np.ndarray:
    """Capture the given window's contents as an RGB numpy array, even if
    obscured by other windows. Uses PrintWindow(PW_RENDERFULLCONTENT)."""
    if win32gui is None or Image is None or not window.hwnd:
        raise RuntimeError("win32 + Pillow required for per-window capture.")

    hwnd = window.hwnd
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    w = right - left
    h = bottom - top
    if w <= 0 or h <= 0:
        raise RuntimeError("Window has no client area to capture.")

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    save_bitmap = win32ui.CreateBitmap()
    save_bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
    save_dc.SelectObject(save_bitmap)

    try:
        ok = ctypes.windll.user32.PrintWindow(
            hwnd, save_dc.GetSafeHdc(), _PW_RENDERFULLCONTENT
        )
        if not ok:
            raise RuntimeError("PrintWindow failed.")
        bmp_info = save_bitmap.GetInfo()
        bmp_bits = save_bitmap.GetBitmapBits(True)
        img = Image.frombuffer(
            "RGB",
            (bmp_info["bmWidth"], bmp_info["bmHeight"]),
            bmp_bits,
            "raw",
            "BGRX",
            0,
            1,
        )
        return np.array(img)
    finally:
        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)


import time

_VK_ESCAPE = 0x1B
_VK_RETURN = 0x0D
_VK_L = 0x4C
_VK_S = 0x53
_KEYEVENTF_KEYUP = 0x0002


def prevent_afk(window: WindowInfo, hold_seconds: float = 1.0) -> None:
    """Focus Roblox and hold S for `hold_seconds` so the game registers input.

    Blocks the caller for ~hold_seconds (plus focus polling). The caller is
    expected to have paused the guard loop so this freeze of the tk mainloop
    is harmless; it happens at most every 15 min.
    """
    if win32api is None or win32gui is None or not window.hwnd:
        return
    try:
        if win32gui.IsIconic(window.hwnd):
            win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(window.hwnd)
    except Exception:
        pass
    for _ in range(20):
        try:
            if win32gui.GetForegroundWindow() == window.hwnd:
                break
        except Exception:
            break
        time.sleep(0.05)
    time.sleep(0.1)
    win32api.keybd_event(_VK_S, 0, 0, 0)
    time.sleep(hold_seconds)
    win32api.keybd_event(_VK_S, 0, _KEYEVENTF_KEYUP, 0)


def leave_game(window: WindowInfo) -> None:
    """Run Roblox's leave-game sequence: focus → Escape → Enter, atomically."""
    if win32api is None or win32gui is None or not window.hwnd:
        return
    try:
        if win32gui.IsIconic(window.hwnd):
            win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(window.hwnd)
    except Exception:
        pass
    # Wait up to 1 s for Roblox to actually be foreground before synthesizing keys,
    # otherwise the keystrokes land on whatever window happened to be focused.
    for _ in range(20):
        try:
            if win32gui.GetForegroundWindow() == window.hwnd:
                break
        except Exception:
            break
        time.sleep(0.05)
    time.sleep(0.15)
    # Roblox's leave-game chord: Esc (open menu) → L (arm Leave) → Enter (confirm).
    win32api.keybd_event(_VK_ESCAPE, 0, 0, 0)
    win32api.keybd_event(_VK_ESCAPE, 0, _KEYEVENTF_KEYUP, 0)
    time.sleep(0.25)
    win32api.keybd_event(_VK_L, 0, 0, 0)
    win32api.keybd_event(_VK_L, 0, _KEYEVENTF_KEYUP, 0)
    time.sleep(0.25)
    win32api.keybd_event(_VK_RETURN, 0, 0, 0)
    win32api.keybd_event(_VK_RETURN, 0, _KEYEVENTF_KEYUP, 0)
