from __future__ import annotations

import tkinter as tk
from typing import Callable


class CountdownOverlay(tk.Toplevel):
    def __init__(self, master: tk.Misc, seconds: int, on_done: Callable[[], None]) -> None:
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.85)
        except tk.TclError:
            pass
        self.configure(bg="#000000")

        self._remaining = seconds
        self._on_done = on_done

        self._label = tk.Label(
            self,
            text=str(self._remaining),
            fg="#ffffff",
            bg="#000000",
            font=("TkDefaultFont", 96, "bold"),
            width=3,
        )
        self._label.pack(padx=40, pady=20)

        self.update_idletasks()
        self._center()
        self.after(1000, self._tick)

    def _center(self) -> None:
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            self.destroy()
            self._on_done()
            return
        self._label.config(text=str(self._remaining))
        self.after(1000, self._tick)
