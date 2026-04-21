from __future__ import annotations

import sys

if sys.platform == "darwin":
    from . import _macos as impl  # noqa: F401
elif sys.platform == "win32":
    from . import _windows as impl  # noqa: F401
else:
    raise RuntimeError(
        f"Roblox AFK Guard supports macOS and Windows only (detected: {sys.platform})."
    )

list_roblox_windows = impl.list_roblox_windows
focus_window = impl.focus_window
capture_window = impl.capture_window
leave_game = impl.leave_game
prevent_afk = impl.prevent_afk
