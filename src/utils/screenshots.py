from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from .config import CONFIG_DIR


SCREENSHOT_DIR = CONFIG_DIR / "screenshots"


def save_trip_frame(frame: np.ndarray) -> Path:
    """Save the frame that tripped the guard to the screenshots folder.

    Filename is `trip-YYYYMMDD-HHMMSS.png`. Returns the written path so the
    caller can log where it went — useful when diagnosing false positives.
    """
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = SCREENSHOT_DIR / f"trip-{stamp}.png"
    Image.fromarray(frame).save(path)
    print(f"[trip] saved screenshot → {path}", file=sys.stderr)
    return path
