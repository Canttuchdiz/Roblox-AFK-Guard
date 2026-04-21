from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np

from .detector import Detector


@dataclass(frozen=True)
class TripInfo:
    """Everything the trip handler needs to explain what happened.

    Bundled into a dataclass so we can add fields (timestamp, region label,
    etc.) without another round of callback-signature churn.
    """
    frame: np.ndarray          # the post-motion RGB frame that tripped
    moved: np.ndarray          # bool HxW mask: True where pixels counted as moved
    diff: float                # count of moved pixels
    threshold: float           # the threshold the diff exceeded


TICK_MS = 250


class TkAfterScheduler(Protocol):
    def after(self, ms: int, callback: Callable[[], None]) -> str: ...
    def after_cancel(self, id: str) -> None: ...


@dataclass
class GuardLoop:
    """tk-after-driven guard tick. No threads."""

    root: TkAfterScheduler
    detector: Detector
    capture_fn: Callable[[], "object"]  # returns np.ndarray frame
    on_tick: Callable[[float, float], None]  # (diff, threshold)
    on_trip: Callable[[TripInfo], None]

    _job: str | None = None
    _running: bool = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._schedule()

    def stop(self) -> None:
        self._running = False
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _schedule(self) -> None:
        if not self._running:
            return
        self._job = self.root.after(TICK_MS, self._tick)

    def _tick(self) -> None:
        if not self._running:
            return
        frame = self.capture_fn()
        diff, tripped = self.detector.step(frame)
        self.on_tick(diff, self.detector.threshold)
        if tripped:
            self._running = False
            # last_moved is guaranteed non-None after a successful diff tick;
            # fall back to an all-False mask just so the callback never NPEs.
            moved = self.detector.last_moved
            if moved is None:
                moved = np.zeros(frame.shape[:2], dtype=bool)
            self.on_trip(TripInfo(
                frame=frame,
                moved=moved,
                diff=diff,
                threshold=self.detector.threshold,
            ))
            return
        self._schedule()
