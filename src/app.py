from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import numpy as np

from src.gui.calibrator import CalibrationDialog
from src.gui.countdown import CountdownOverlay
from src.gui.guard import GuardWindow
from src.gui.killed import KilledBanner
from src.gui.painter import IgnoreRegionPainter, Region
from src.gui.picker import WindowPickerFrame
from src.logic.detector import Detector, build_ignore_mask
from src.logic.guard_loop import GuardLoop
from src.utils import config
from src.utils.screenshots import save_trip_frame
from src.utils.windows import capture_window, focus_window, leave_game, prevent_afk


APP_TITLE = "Roblox AFK Guard"
COUNTDOWN_SECONDS = 3

# How often to prod Roblox with an input so it doesn't kick us for idling.
ANTI_AFK_INTERVAL_MS = 15 * 60 * 1000
# How long to hold S. Long enough for Roblox to count it as deliberate movement.
ANTI_AFK_HOLD_S = 1.0
# After the S hold finishes, how long to wait for character animation / camera
# motion to settle before we re-enable detection. Must exceed ANTI_AFK_HOLD_S
# plus focus-polling overhead in prevent_afk().
ANTI_AFK_SETTLE_MS = 2500


class AppController:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("640x420")
        self._current: tk.Widget | None = None

        self._window = None
        self._reference_frame: np.ndarray | None = None
        self._regions: list[Region] = []
        self._loop: GuardLoop | None = None
        self._detector: Detector | None = None

        self._show_picker()

    def run(self) -> None:
        self.root.mainloop()

    # --- screen transitions ---

    def _swap(self, widget: tk.Widget) -> None:
        if self._current is not None:
            self._current.destroy()
        self._current = widget
        widget.pack(fill="both", expand=True)

    def _show_picker(self) -> None:
        self._swap(WindowPickerFrame(self.root, on_start=self._on_window_picked))

    def _on_window_picked(self, window) -> None:
        self._window = window
        profile = config.get_profile(window.width, window.height)
        self._regions = list(profile.ignore_regions) if profile else []

        # Countdown → focus Roblox → capture reference frame → show painter.
        CountdownOverlay(self.root, COUNTDOWN_SECONDS, on_done=self._after_countdown)

    def _after_countdown(self) -> None:
        assert self._window is not None
        focus_window(self._window)
        # Give the WM a tick to repaint before we grab.
        self.root.after(120, self._grab_and_paint)

    def _grab_and_paint(self) -> None:
        assert self._window is not None
        self._reference_frame = capture_window(self._window)
        painter = IgnoreRegionPainter(
            self.root,
            frame=self._reference_frame,
            initial_regions=self._regions,
            on_confirm=self._on_regions_confirmed,
        )
        self._swap(painter)

    def _on_regions_confirmed(self, regions: list[Region]) -> None:
        assert self._window is not None
        self._regions = regions
        config.put_profile(
            config.ResolutionProfile(
                width=self._window.width,
                height=self._window.height,
                ignore_regions=regions,
            )
        )
        assert self._reference_frame is not None
        h, w = self._reference_frame.shape[:2]
        mask = build_ignore_mask(h, w, regions)

        dialog = CalibrationDialog(
            self.root,
            mask=mask,
            capture_fn=self._capture_current,
            on_done=lambda threshold: self._start_guard(mask, threshold),
        )
        self._swap(dialog)

    def _capture_current(self) -> np.ndarray:
        assert self._window is not None
        return capture_window(self._window)

    def _start_guard(self, mask: np.ndarray, threshold: float) -> None:
        assert self._window is not None
        detector = Detector(threshold=threshold, mask=mask)

        self.root.attributes("-topmost", True)
        self.root.geometry("360x320")

        # Slider range: 0 → 5% of the frame. Well past any realistic trip
        # threshold so the user can detune aggressively if needed.
        frame_pixels = int(mask.shape[0] * mask.shape[1])
        slider_max = max(frame_pixels * 0.05, threshold * 4.0)

        def _set_threshold(new_value: float) -> None:
            detector.threshold = new_value

        guard_ui = GuardWindow(
            self.root,
            window_title=self._window.title,
            pid=self._window.pid,
            threshold=threshold,
            slider_max=slider_max,
            on_threshold_change=_set_threshold,
        )
        self._swap(guard_ui)

        loop = GuardLoop(
            root=self.root,
            detector=detector,
            capture_fn=self._capture_current,
            on_tick=guard_ui.update_diff,
            on_trip=self._on_trip,
        )
        loop.start()
        self._loop = loop
        self._detector = detector
        self._schedule_anti_afk()

    def _schedule_anti_afk(self) -> None:
        self.root.after(ANTI_AFK_INTERVAL_MS, self._anti_afk_tick)

    def _anti_afk_tick(self) -> None:
        """Every 15 min, pause the guard, hold S so Roblox sees input, resume."""
        if self._window is None or self._loop is None:
            return
        self._loop.stop()
        prevent_afk(self._window, ANTI_AFK_HOLD_S)
        # Wait for the key hold + character settle before re-arming the guard;
        # otherwise the movement we just caused would diff huge and trip.
        self.root.after(ANTI_AFK_SETTLE_MS, self._after_anti_afk)

    def _after_anti_afk(self) -> None:
        if self._loop is None or self._detector is None:
            return
        self._detector.reset_baseline()
        self._loop.start()
        self._schedule_anti_afk()

    def _on_trip(self, frame: np.ndarray) -> None:
        """Save the offending frame, then run Roblox's leave-game flow."""
        assert self._window is not None
        try:
            save_trip_frame(frame)
        except Exception as exc:
            # Screenshotting must never block leave_game — that's the whole point.
            print(f"[trip] failed to save screenshot: {exc}")
        if self._current is not None:
            self._current.pack_forget()
        KilledBanner(self.root, on_done=self.root.destroy)
        leave_game(self._window)
