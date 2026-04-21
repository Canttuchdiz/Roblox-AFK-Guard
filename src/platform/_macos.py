from __future__ import annotations

import subprocess
from dataclasses import dataclass

import numpy as np

try:
    from Quartz import (
        CGDataProviderCopyData,
        CGImageGetBytesPerRow,
        CGImageGetDataProvider,
        CGImageGetHeight,
        CGImageGetWidth,
        CGRectNull,
        CGWindowListCopyWindowInfo,
        CGWindowListCreateImage,
        kCGNullWindowID,
        kCGWindowImageBoundsIgnoreFraming,
        kCGWindowListExcludeDesktopElements,
        kCGWindowListOptionIncludingWindow,
        kCGWindowListOptionOnScreenOnly,
    )
except ImportError:  # pragma: no cover - only hit when pyobjc not installed
    CGWindowListCopyWindowInfo = None


ROBLOX_OWNER_PREFIXES = ("Roblox",)


@dataclass(frozen=True)
class WindowInfo:
    pid: int
    title: str
    width: int
    height: int
    bbox: tuple[int, int, int, int]  # left, top, width, height in global screen coords
    window_number: int = 0           # kCGWindowNumber, used for per-window capture


def _is_roblox_owner(owner: str) -> bool:
    return any(owner.startswith(p) for p in ROBLOX_OWNER_PREFIXES)


def list_roblox_windows() -> list[WindowInfo]:
    if CGWindowListCopyWindowInfo is None:
        return []
    options = kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements
    infos = CGWindowListCopyWindowInfo(options, kCGNullWindowID) or []
    result: list[WindowInfo] = []
    for info in infos:
        owner = str(info.get("kCGWindowOwnerName", ""))
        if not _is_roblox_owner(owner):
            continue
        bounds = info.get("kCGWindowBounds") or {}
        width = int(bounds.get("Width", 0))
        height = int(bounds.get("Height", 0))
        if width < 200 or height < 200:
            continue
        left = int(bounds.get("X", 0))
        top = int(bounds.get("Y", 0))
        pid = int(info.get("kCGWindowOwnerPID", 0))
        title = str(info.get("kCGWindowName") or owner)
        win_num = int(info.get("kCGWindowNumber", 0))
        result.append(
            WindowInfo(
                pid=pid,
                title=title,
                width=width,
                height=height,
                bbox=(left, top, width, height),
                window_number=win_num,
            )
        )
    return result


def focus_window(window: WindowInfo) -> None:
    script = (
        'tell application "System Events" to set frontmost of '
        f"(first process whose unix id is {window.pid}) to true"
    )
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=False,
            timeout=2,
            capture_output=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def leave_game(window: WindowInfo) -> None:
    """Run Roblox's leave-game sequence: focus → Escape → Enter, atomically.

    Previously this was 3 separate Python calls scheduled via tk.after(), which
    raced: focus_window returned before Roblox was actually frontmost, so the
    keystrokes often landed on whatever window happened to be focused at that
    instant. AppleScript handles the wait-for-frontmost serialization for us.
    """
    pid = window.pid
    # key code 53 = escape, key code 37 = L, key code 36 = return
    # Roblox's leave-game chord is Esc → L → Enter: open menu, arm Leave, confirm.
    script = f'''
    tell application "System Events"
        set targetProc to first process whose unix id is {pid}
        set frontmost of targetProc to true
        repeat 20 times
            if frontmost of targetProc is true then exit repeat
            delay 0.05
        end repeat
        delay 0.15
        key code 53
        delay 0.25
        key code 37
        delay 0.25
        key code 36
    end tell
    '''
    try:
        # Popen (not run) so we don't block tkinter's main loop while the
        # script's ~600 ms of delays elapse. Fire-and-forget is fine — the
        # banner is already up and the app is exiting anyway.
        subprocess.Popen(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


def prevent_afk(window: WindowInfo, hold_seconds: float = 1.0) -> None:
    """Focus Roblox and hold S for `hold_seconds` so the game registers input.

    Fire-and-forget: returns immediately. The caller is expected to have paused
    the guard loop and to wait ~hold_seconds + ~1 s before resuming, so that
    the character's movement from the S hold settles before we diff again.
    """
    pid = window.pid
    # key code 1 = S. `key down` / `key up` hold the key between them.
    script = f'''
    tell application "System Events"
        set targetProc to first process whose unix id is {pid}
        set frontmost of targetProc to true
        repeat 20 times
            if frontmost of targetProc is true then exit repeat
            delay 0.05
        end repeat
        delay 0.1
        key down "s"
        delay {hold_seconds}
        key up "s"
    end tell
    '''
    try:
        subprocess.Popen(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


def capture_window(window: WindowInfo) -> np.ndarray:
    """Capture the given Roblox window as an RGB numpy array.

    Unlike a screen-bbox grab, this uses Quartz's per-window capture so it
    returns the Roblox contents even when our own tkinter windows are on top
    of it. That's what makes the guard loop immune to false trips from its
    own slider/progress bar animating.
    """
    if CGWindowListCreateImage is None:
        raise RuntimeError("Quartz is not available — install pyobjc-framework-Quartz.")
    if not window.window_number:
        raise RuntimeError("WindowInfo has no window_number; cannot capture.")

    image_ref = CGWindowListCreateImage(
        CGRectNull,
        kCGWindowListOptionIncludingWindow,
        window.window_number,
        kCGWindowImageBoundsIgnoreFraming,
    )
    if image_ref is None:
        raise RuntimeError("CGWindowListCreateImage returned None (window closed?)")

    w = CGImageGetWidth(image_ref)
    h = CGImageGetHeight(image_ref)
    bpr = CGImageGetBytesPerRow(image_ref)
    provider = CGImageGetDataProvider(image_ref)
    cfdata = CGDataProviderCopyData(provider)

    raw = bytes(cfdata)
    # macOS returns BGRA on little-endian; bytes_per_row may be padded beyond 4*w.
    arr = np.frombuffer(raw, dtype=np.uint8).reshape(h, bpr // 4, 4)
    return arr[:, :w, [2, 1, 0]].copy()
