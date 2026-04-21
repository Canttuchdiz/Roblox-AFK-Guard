from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

import numpy as np
from PIL import Image, ImageTk

Region = tuple[int, int, int, int]  # x, y, w, h in image-local coords


class IgnoreRegionPainter(ttk.Frame):
    """Interactive canvas for painting semi-transparent red ignore rectangles.

    Keys: 'Z' undo last rectangle, 'C' clear all.
    """

    MAX_CANVAS_WIDTH = 1100
    MAX_CANVAS_HEIGHT = 650

    def __init__(
        self,
        master: tk.Misc,
        frame: np.ndarray,
        initial_regions: list[Region],
        on_confirm: Callable[[list[Region]], None],
    ) -> None:
        super().__init__(master, padding=12)
        self._on_confirm = on_confirm
        self._regions: list[Region] = list(initial_regions)

        self._frame_h, self._frame_w = frame.shape[:2]
        self._scale = min(
            1.0,
            self.MAX_CANVAS_WIDTH / self._frame_w,
            self.MAX_CANVAS_HEIGHT / self._frame_h,
        )
        disp_w = int(self._frame_w * self._scale)
        disp_h = int(self._frame_h * self._scale)

        pil_img = Image.fromarray(frame).resize((disp_w, disp_h), Image.BILINEAR)
        self._photo = ImageTk.PhotoImage(pil_img)

        ttk.Label(
            self,
            text=(
                "Cover anything that moves while you are idle — your character, "
                "HUD, ticking numbers. Drag to paint. Press Z to undo, C to clear."
            ),
            wraplength=disp_w,
        ).pack(anchor="w", pady=(0, 6))

        self._canvas = tk.Canvas(
            self,
            width=disp_w,
            height=disp_h,
            highlightthickness=1,
            highlightbackground="#444",
            bg="#000",
            cursor="crosshair",
        )
        self._canvas.pack()
        self._canvas.create_image(0, 0, anchor="nw", image=self._photo)

        self._start: tuple[int, int] | None = None
        self._live_id: int | None = None
        self._rect_ids: list[int] = []

        self._canvas.bind("<ButtonPress-1>", self._on_down)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_up)

        self.bind_all("<KeyPress-z>", lambda _e: self._undo())
        self.bind_all("<KeyPress-Z>", lambda _e: self._undo())
        self.bind_all("<KeyPress-c>", lambda _e: self._clear())
        self.bind_all("<KeyPress-C>", lambda _e: self._clear())

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Undo (Z)", command=self._undo).pack(side="left")
        ttk.Button(btns, text="Clear (C)", command=self._clear).pack(side="left", padx=6)
        ttk.Button(btns, text="Continue →", command=self._confirm).pack(side="right")

        self._redraw_all()

    def _on_down(self, event: tk.Event) -> None:
        self._start = (event.x, event.y)

    def _on_drag(self, event: tk.Event) -> None:
        if self._start is None:
            return
        x0, y0 = self._start
        if self._live_id is not None:
            self._canvas.delete(self._live_id)
        self._live_id = self._canvas.create_rectangle(
            x0, y0, event.x, event.y,
            outline="#ff3030",
            fill="#ff3030",
            stipple="gray50",
            width=2,
        )

    def _on_up(self, event: tk.Event) -> None:
        if self._start is None:
            return
        x0, y0 = self._start
        x1, y1 = event.x, event.y
        if self._live_id is not None:
            self._canvas.delete(self._live_id)
            self._live_id = None
        self._start = None
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        if dx < 4 or dy < 4:
            return
        # Convert displayed coords back to original-frame coords.
        lx = min(x0, x1) / self._scale
        ly = min(y0, y1) / self._scale
        lw = dx / self._scale
        lh = dy / self._scale
        self._regions.append((int(lx), int(ly), int(lw), int(lh)))
        self._redraw_all()

    def _redraw_all(self) -> None:
        for rid in self._rect_ids:
            self._canvas.delete(rid)
        self._rect_ids.clear()
        for x, y, w, h in self._regions:
            dx = x * self._scale
            dy = y * self._scale
            dw = w * self._scale
            dh = h * self._scale
            rid = self._canvas.create_rectangle(
                dx, dy, dx + dw, dy + dh,
                outline="#ff3030",
                fill="#ff3030",
                stipple="gray50",
                width=2,
            )
            self._rect_ids.append(rid)

    def _undo(self) -> None:
        if self._regions:
            self._regions.pop()
            self._redraw_all()

    def _clear(self) -> None:
        self._regions.clear()
        self._redraw_all()

    def _confirm(self) -> None:
        self._on_confirm(list(self._regions))
