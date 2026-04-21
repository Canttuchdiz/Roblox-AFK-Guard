from __future__ import annotations

from dataclasses import dataclass

import numpy as np


Region = tuple[int, int, int, int]  # x, y, w, h in window-local coords

# A single-pixel channel-sum delta above this is considered "moved". The sum is
# taken over the 3 RGB channels, so 30 ≈ an average ~10/255 shift per channel —
# well above JPEG / video compression noise but low enough that a new sprite
# dropping in still lights up every pixel it covers.
PIXEL_CHANGE_DELTA = 30


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


def frame_diff(prev: np.ndarray, curr: np.ndarray, mask: np.ndarray) -> float:
    """Return the count of unmasked pixels that changed meaningfully between frames.

    A pixel counts as "moved" when the sum of absolute per-channel deltas
    exceeds PIXEL_CHANGE_DELTA. We return a count (not a mean) so that a
    localized event — e.g. a player spawning in, covering a few thousand
    pixels in a 2M-pixel window — is not diluted to near zero by averaging
    across the whole frame.
    """
    if prev.shape != curr.shape:
        raise ValueError(f"shape mismatch: {prev.shape} vs {curr.shape}")
    if mask.shape != prev.shape[:2]:
        raise ValueError(f"mask shape {mask.shape} != frame HxW {prev.shape[:2]}")
    delta = np.abs(curr.astype(np.int16) - prev.astype(np.int16)).sum(axis=2)
    moved = (delta > PIXEL_CHANGE_DELTA) & (mask > 0)
    return float(moved.sum())


@dataclass
class Detector:
    threshold: float
    mask: np.ndarray
    _prev: np.ndarray | None = None

    def step(self, frame: np.ndarray) -> tuple[float, bool]:
        """Feed a new frame. Returns (diff, tripped). First call always returns (0.0, False)."""
        if self._prev is None or self._prev.shape != frame.shape:
            self._prev = frame
            return 0.0, False
        diff = frame_diff(self._prev, frame, self.mask)
        self._prev = frame
        return diff, diff > self.threshold

    def reset_baseline(self) -> None:
        """Drop the stored previous frame so the next step() re-seeds from scratch.

        Used after intentional motion we caused ourselves (anti-AFK key hold)
        so that the resulting character movement doesn't get diffed and trip.
        """
        self._prev = None
