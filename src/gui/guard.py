from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class GuardWindow(ttk.Frame):
    """Always-on-top status readout with a live sensitivity slider."""

    def __init__(
        self,
        master: tk.Misc,
        window_title: str,
        pid: int,
        threshold: float,
        slider_max: float,
        on_threshold_change: Callable[[float], None],
    ) -> None:
        super().__init__(master, padding=14)
        self._on_threshold_change = on_threshold_change
        self._slider_max = max(slider_max, threshold * 4.0, 1.0)

        ttk.Label(
            self,
            text="GUARDING",
            foreground="#1c8f2a",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(anchor="w")

        ttk.Label(self, text=f"Window: {window_title}").pack(anchor="w")
        ttk.Label(self, text=f"PID: {pid}").pack(anchor="w", pady=(0, 8))

        self._diff_var = tk.StringVar(value="moved: 0 px")
        ttk.Label(self, textvariable=self._diff_var, font=("TkFixedFont", 12)).pack(anchor="w")

        self._bar = ttk.Progressbar(
            self,
            mode="determinate",
            maximum=self._slider_max,
            length=280,
        )
        self._bar.pack(fill="x", pady=(4, 10))

        ttk.Separator(self).pack(fill="x", pady=(0, 6))
        ttk.Label(
            self,
            text="Trip threshold — drag to tune while watching the diff above.",
            wraplength=280,
        ).pack(anchor="w")

        self._threshold_var = tk.DoubleVar(value=threshold)
        self._threshold_label_var = tk.StringVar(value=f"trip at: {int(threshold)} px")
        ttk.Label(
            self, textvariable=self._threshold_label_var, font=("TkFixedFont", 11)
        ).pack(anchor="w", pady=(2, 0))

        self._scale = ttk.Scale(
            self,
            from_=0.0,
            to=self._slider_max,
            orient="horizontal",
            variable=self._threshold_var,
            command=self._on_slider,
            length=280,
        )
        self._scale.pack(fill="x")

    def _on_slider(self, _raw: str) -> None:
        value = float(self._threshold_var.get())
        self._threshold_label_var.set(f"trip at: {int(value)} px")
        self._on_threshold_change(value)

    def update_diff(self, diff: float, threshold: float) -> None:
        self._diff_var.set(f"moved: {int(diff)} px  /  trip: {int(threshold)} px")
        self._bar["value"] = min(diff, self._bar["maximum"])
