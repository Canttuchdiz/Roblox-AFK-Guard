from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

import numpy as np

from src.logic.calibrator import CALIBRATION_DURATION_S, CALIBRATION_FRAMES, Calibrator


class CalibrationDialog(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        mask: np.ndarray,
        capture_fn: Callable[[], np.ndarray],
        on_done: Callable[[float], None],
    ) -> None:
        super().__init__(master, padding=20)
        self._capture = capture_fn
        self._on_done = on_done
        self._calibrator = Calibrator(mask=mask)
        self._tick_ms = int(CALIBRATION_DURATION_S * 1000 / (CALIBRATION_FRAMES + 1))

        ttk.Label(
            self,
            text="Calibrating — stand still for 5 seconds.",
            font=("TkDefaultFont", 12, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            self,
            text="Sampling idle pixel-diff so we can set a sensible trip threshold.",
        ).pack(anchor="w", pady=(0, 10))

        self._bar = ttk.Progressbar(
            self, mode="determinate", maximum=CALIBRATION_FRAMES, length=340
        )
        self._bar.pack(fill="x")

        self._status = ttk.Label(self, text="0 / {} frames".format(CALIBRATION_FRAMES))
        self._status.pack(anchor="w", pady=(6, 0))

        self.after(self._tick_ms, self._tick)

    def _tick(self) -> None:
        try:
            frame = self._capture()
        except Exception as exc:  # pragma: no cover
            self._status.config(text=f"capture error: {exc}")
            self.after(self._tick_ms, self._tick)
            return

        self._calibrator.feed(frame)
        done = len(self._calibrator.diffs)
        self._bar["value"] = done
        self._status.config(text=f"{done} / {CALIBRATION_FRAMES} frames")

        if self._calibrator.done:
            self._on_done(self._calibrator.threshold())
            return
        self.after(self._tick_ms, self._tick)
