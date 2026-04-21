from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from src.utils.windows import list_roblox_windows


class WindowPickerFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_start: Callable[[object], None]) -> None:
        super().__init__(master, padding=12)
        self._on_start = on_start
        self._windows: list = []

        header = ttk.Label(
            self,
            text="Select a Roblox window to guard",
            font=("TkDefaultFont", 14, "bold"),
        )
        header.pack(anchor="w")

        ttk.Label(
            self,
            text="The guard will kill this process the moment something moves "
            "outside your ignore regions.",
            wraplength=520,
        ).pack(anchor="w", pady=(2, 8))

        cols = ("pid", "title", "size")
        self._tree = ttk.Treeview(self, columns=cols, show="headings", height=8)
        self._tree.heading("pid", text="PID")
        self._tree.heading("title", text="Title")
        self._tree.heading("size", text="Resolution")
        self._tree.column("pid", width=80, anchor="w")
        self._tree.column("title", width=340, anchor="w")
        self._tree.column("size", width=120, anchor="w")
        self._tree.pack(fill="both", expand=True, pady=4)

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Refresh", command=self.refresh).pack(side="left")
        ttk.Button(btns, text="Start", command=self._start).pack(side="right")

        self.refresh()

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        try:
            self._windows = list_roblox_windows()
        except Exception as exc:  # pragma: no cover - platform-dependent
            self._windows = []
            self._tree.insert("", "end", values=("-", f"error: {exc}", "-"))
            return

        if not self._windows:
            self._tree.insert("", "end", values=("-", "No Roblox windows detected", "-"))
            return

        for i, w in enumerate(self._windows):
            self._tree.insert(
                "",
                "end",
                iid=str(i),
                values=(w.pid, w.title, f"{w.width}x{w.height}"),
            )

    def _start(self) -> None:
        sel = self._tree.selection()
        if not sel or not self._windows:
            return
        try:
            idx = int(sel[0])
        except ValueError:
            return
        if 0 <= idx < len(self._windows):
            self._on_start(self._windows[idx])
