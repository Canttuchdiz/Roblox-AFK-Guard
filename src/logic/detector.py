from __future__ import annotations

import sys
from dataclasses import dataclass

import numpy as np
from PIL import Image


Region = tuple[int, int, int, int]  # x, y, w, h in window-local coords

# A single-pixel channel-sum delta above this is considered "moved". The sum is
# taken over the 3 RGB channels, so 30 ≈ an average ~10/255 shift per channel —
# well above JPEG / video compression noise but low enough that a new sprite
# dropping in still lights up every pixel it covers.
PIXEL_CHANGE_DELTA = 30


def resize_mask(mask: np.ndarray, target_hw: tuple[int, int]) -> np.ndarray:
    """Rescale a uint8 ignore mask to a new (height, width) with nearest-neighbor.

    Used when the captured window resolution changes mid-session (HiDPI flip,
    user resized Roblox, switched monitors). Preserves the binary 0/1 values.
    """
    h, w = target_hw
    if mask.shape == (h, w):
        return mask
    pil = Image.fromarray((mask * 255).astype(np.uint8)).resize((w, h), Image.NEAREST)
    return (np.array(pil) > 0).astype(np.uint8)


def build_ignore_mask(height: int, width: int, regions: list[Region]) -> np.ndarray:
    """Return a uint8 mask (h, w) where pixels inside any ignore region are 0, else 1."""
    mask = np.ones((height, width), dtype=np.uint8)
    for x, y, w, h in regions:
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(width, int(x + w))
        y1 = min(height, int(y + h))
        if x1 > x0 and y1 > y0:
            mask[y0:y1, x0:x1] = 0
    return mask


def frame_diff_mask(prev: np.ndarray, curr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Return a bool mask the same shape as the frame's HxW marking which
    unmasked pixels changed meaningfully between `prev` and `curr`.

    A pixel counts as "moved" when the sum of absolute per-channel deltas
    exceeds PIXEL_CHANGE_DELTA. Kept separate from `frame_diff` so the trip
    screenshot can be annotated with the exact region that triggered.
    """
    if prev.shape != curr.shape:
        raise ValueError(f"shape mismatch: {prev.shape} vs {curr.shape}")
    if mask.shape != prev.shape[:2]:
        raise ValueError(f"mask shape {mask.shape} != frame HxW {prev.shape[:2]}")
    delta = np.abs(curr.astype(np.int16) - prev.astype(np.int16)).sum(axis=2)
    return (delta > PIXEL_CHANGE_DELTA) & (mask > 0)


def frame_diff(prev: np.ndarray, curr: np.ndarray, mask: np.ndarray) -> float:
    """Count of unmasked pixels that changed meaningfully between frames.

    A localized event (e.g. a player spawning) is not diluted to near zero by
    averaging across the whole frame — we return a pixel count, not a mean.
    """
    return float(frame_diff_mask(prev, curr, mask).sum())


@dataclass
class Detector:
    threshold: float
    mask: np.ndarray
    _prev: np.ndarray | None = None
    _last_moved: np.ndarray | None = None  # bool HxW mask from the most recent step

    @property
    def last_moved(self) -> np.ndarray | None:
        """The moved-pixel mask from the most recent step(), for debug overlays."""
        return self._last_moved

    def step(self, frame: np.ndarray) -> tuple[float, bool]:
        """Feed a new frame. Returns (diff, tripped). First call always returns (0.0, False)."""
        # Window can change resolution under us (HiDPI scaling flip, resize,
        # move to a different display). Rescale the mask to match rather
        # than crash — painted regions roughly follow the window size.
        if self.mask.shape != frame.shape[:2]:
            print(
                f"[detector] frame resized {self.mask.shape} -> {frame.shape[:2]}; "
                "rescaling ignore mask",
                file=sys.stderr,
            )
            self.mask = resize_mask(self.mask, frame.shape[:2])
            # Prev is also stale at the old resolution — start over.
            self._prev = frame
            self._last_moved = None
            return 0.0, False
        if self._prev is None or self._prev.shape != frame.shape:
            self._prev = frame
            self._last_moved = None
            return 0.0, False
        moved = frame_diff_mask(self._prev, frame, self.mask)
        self._last_moved = moved
        self._prev = frame
        diff = float(moved.sum())
        return diff, diff > self.threshold

    def reset_baseline(self) -> None:
        """Drop the stored previous frame so the next step() re-seeds from scratch.

        Used after intentional motion we caused ourselves (anti-AFK key hold)
        so that the resulting character movement doesn't get diffed and trip.
        """
        self._prev = None
