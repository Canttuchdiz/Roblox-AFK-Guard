from __future__ import annotations

import tkinter as tk
from typing import Callable


class KilledBanner(tk.Toplevel):
    DURATION_MS = 3000

    def __init__(self, master: tk.Misc, on_done: Callable[[], None]) -> None:
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.92)
        except tk.TclError:
            pass
        self.configure(bg="#8b0000")

        tk.Label(
            self,
            text="LEAVING GAME",
            fg="#ffffff",
            bg="#8b0000",
            font=("TkDefaultFont", 48, "bold"),
            padx=48,
            pady=24,
        ).pack()

        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self.after(self.DURATION_MS, lambda: (self.destroy(), on_done()))
