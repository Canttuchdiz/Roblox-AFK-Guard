from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import CONFIG_DIR


SCREENSHOT_DIR = CONFIG_DIR / "screenshots"

# How much to tint moved pixels in the debug overlay. 0.5 → 50% red blend.
MOVED_PIXEL_TINT_ALPHA = 0.55

# Padding around the bounding box so the red rectangle isn't flush to the
# cluster; easier to see what actually moved vs. the box outline.
BBOX_PADDING_PX = 6


def _save_raw(frame: np.ndarray, path: Path) -> None:
    Image.fromarray(frame).save(path)


def _save_annotated(
    frame: np.ndarray,
    moved: np.ndarray,
    diff: float,
    threshold: float,
    path: Path,
) -> None:
    """Save a debug overlay: red tint on moved pixels + bounding box + stats."""
    # Red overlay where pixels moved — blend, don't replace, so you can still
    # see what's underneath.
    red = np.zeros_like(frame)
    red[..., 0] = 255
    alpha = (moved.astype(np.float32) * MOVED_PIXEL_TINT_ALPHA)[..., None]
    blended = (frame.astype(np.float32) * (1 - alpha) + red.astype(np.float32) * alpha)
    img = Image.fromarray(blended.astype(np.uint8))

    draw = ImageDraw.Draw(img)
    h, w = frame.shape[:2]
    # Scale the rectangle stroke and text with frame size so it reads on both
    # a 900px window and a 4K capture.
    stroke = max(3, min(w, h) // 300)

    # Bounding box over ALL moved pixels. Not connected-component-aware on
    # purpose — one box over the whole change region is enough to point the
    # eye, and it avoids a scipy dependency.
    ys, xs = np.where(moved)
    if ys.size > 0:
        y0 = max(0, int(ys.min()) - BBOX_PADDING_PX)
        y1 = min(h - 1, int(ys.max()) + BBOX_PADDING_PX)
        x0 = max(0, int(xs.min()) - BBOX_PADDING_PX)
        x1 = min(w - 1, int(xs.max()) + BBOX_PADDING_PX)
        draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=stroke)

    # Stats banner in top-left so you can cross-check whether the threshold
    # was reasonable given what tripped.
    try:
        font = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", size=max(14, h // 50))
    except OSError:
        font = ImageFont.load_default()
    label = f"diff={int(diff)}  threshold={int(threshold)}  moved_px={int(moved.sum())}"
    # Dark pill behind text for legibility over arbitrary game backgrounds.
    tw, th = draw.textbbox((0, 0), label, font=font)[2:]
    draw.rectangle([8, 8, 8 + tw + 16, 8 + th + 12], fill=(0, 0, 0))
    draw.text((16, 14), label, fill=(255, 80, 80), font=font)

    img.save(path)


def save_trip_frame(
    frame: np.ndarray,
    moved: np.ndarray | None = None,
    diff: float = 0.0,
    threshold: float = 0.0,
) -> Path:
    """Save the frame that tripped the guard, plus a debug-annotated copy.

    Writes two files into ~/.robloxafkguard/screenshots/:
      - trip-<stamp>.png         — raw frame as captured
      - trip-<stamp>-debug.png   — same frame with moved pixels tinted red,
                                   bounding box around the change, stats banner

    Returns the raw path (for logging); the debug path is raw + "-debug.png".
    """
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = SCREENSHOT_DIR / f"trip-{stamp}.png"
    _save_raw(frame, raw_path)
    print(f"[trip] saved screenshot → {raw_path}", file=sys.stderr)

    if moved is not None and moved.shape == frame.shape[:2]:
        debug_path = SCREENSHOT_DIR / f"trip-{stamp}-debug.png"
        try:
            _save_annotated(frame, moved, diff, threshold, debug_path)
            print(f"[trip] saved debug overlay → {debug_path}", file=sys.stderr)
        except Exception as exc:
            # Never let a bad overlay prevent the raw save from being useful.
            print(f"[trip] debug overlay failed: {exc}", file=sys.stderr)

    return raw_path
