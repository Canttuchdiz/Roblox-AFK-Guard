from __future__ import annotations

import sys
from dataclasses import dataclass, field

import numpy as np

from .detector import frame_diff


CALIBRATION_FRAMES = 20
CALIBRATION_DURATION_S = 5.0
THRESHOLD_MULTIPLIER = 2.0

# Floor: prevents cursor-jitter-tight thresholds on unnaturally quiet idle periods.
# Empirically, a spawning player / swung weapon is tens of thousands of motion
# pixels, so 1200 is well below real events but well above ambient noise.
MIN_THRESHOLD = 1200.0

# Ceiling: a change covering this fraction of the frame must always trip,
# regardless of how noisy calibration turned out to be. A spawning player at
# 1080p covers 15k-80k px (~1-4% of the frame); capping at 1.5% (~31k at 1080p)
# means a whole character's worth of new pixels trips while tolerating some
# ambient animation. TUNE THIS if you get false trips or miss real events —
# higher = more tolerant, lower = more sensitive.
MAX_TRIGGER_FRACTION = 0.015

# Percentile of idle samples used as the noise baseline. We use 0.75 (not max)
# so that a single spike during calibration — camera sway, a distant NPC
# stepping, a particle effect — can't balloon the threshold.
NOISE_PERCENTILE = 0.75


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, min(len(s) - 1, int(p * len(s))))
    return s[idx]


def threshold_from_samples(
    diffs: list[float],
    frame_pixel_count: int | None = None,
) -> float:
    """Compute a robust trip threshold from idle-period diff samples.

    baseline = P75(diffs) * 2.0
    floor    = MIN_THRESHOLD                   (never lower than this)
    ceiling  = frame_pixel_count * 0.005       (never higher than this, if given)
    """
    baseline = _percentile(diffs, NOISE_PERCENTILE) * THRESHOLD_MULTIPLIER
    result = max(baseline, MIN_THRESHOLD)
    if frame_pixel_count is not None:
        result = min(result, frame_pixel_count * MAX_TRIGGER_FRACTION)
    return result


@dataclass
class Calibrator:
    mask: np.ndarray
    diffs: list[float] = field(default_factory=list)
    _prev: np.ndarray | None = None

    @property
    def frames_needed(self) -> int:
        return CALIBRATION_FRAMES

    @property
    def done(self) -> bool:
        return len(self.diffs) >= CALIBRATION_FRAMES

    @property
    def _frame_pixels(self) -> int:
        return int(self.mask.shape[0] * self.mask.shape[1])

    def feed(self, frame: np.ndarray) -> None:
        if self._prev is not None and self._prev.shape == frame.shape:
            self.diffs.append(frame_diff(self._prev, frame, self.mask))
        self._prev = frame

    def threshold(self) -> float:
        t = threshold_from_samples(self.diffs, frame_pixel_count=self._frame_pixels)
        # Log a one-line calibration summary so the user can diagnose if a
        # real event (like a distant spawn) is still sub-threshold.
        if self.diffs:
            print(
                f"[calibration] samples={len(self.diffs)} "
                f"min={min(self.diffs):.0f} "
                f"p75={_percentile(self.diffs, NOISE_PERCENTILE):.0f} "
                f"max={max(self.diffs):.0f}  "
                f"frame={self._frame_pixels} px  "
                f"→ threshold={t:.0f} px",
                file=sys.stderr,
            )
        return t
