from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .detector import Detector


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
    on_trip: Callable[[Any], None]  # receives the frame (np.ndarray) that tripped

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
            self.on_trip(frame)
            return
        self._schedule()
