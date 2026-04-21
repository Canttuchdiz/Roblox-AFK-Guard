from __future__ import annotations

from dataclasses import dataclass

import mss
import numpy as np


@dataclass(frozen=True)
class BBox:
    left: int
    top: int
    width: int
    height: int

    def as_monitor(self) -> dict:
        return {"left": self.left, "top": self.top, "width": self.width, "height": self.height}


class ScreenCapture:
    def __init__(self) -> None:
        self._sct = mss.mss()

    def grab(self, bbox: BBox) -> np.ndarray:
        raw = self._sct.grab(bbox.as_monitor())
        # mss returns BGRA; convert to RGB for consistency with Pillow downstream.
        arr = np.array(raw, dtype=np.uint8)
        return arr[:, :, [2, 1, 0]]

    def close(self) -> None:
        self._sct.close()
