import numpy as np

from src.logic.calibrator import (
    CALIBRATION_FRAMES,
    MAX_TRIGGER_FRACTION,
    MIN_THRESHOLD,
    THRESHOLD_MULTIPLIER,
    Calibrator,
    threshold_from_samples,
)


def test_threshold_from_empty_is_floor():
    assert threshold_from_samples([]) == MIN_THRESHOLD


def test_threshold_all_zero_uses_floor():
    # A perfectly static calibration period should still produce a sane trip
    # threshold — not a near-zero one that mouse jitter could trip.
    assert threshold_from_samples([0.0, 0.0, 0.0]) == MIN_THRESHOLD


def test_threshold_uses_p75_not_max():
    # If idle is uniformly 1000 but there's a single 50000 spike, a robust
    # threshold must reflect the 1000 baseline, not the one-off spike.
    diffs = [1000.0] * 19 + [50000.0]
    t = threshold_from_samples(diffs)
    # P75 of [1000,1000,...,1000,50000] sits in the 1000s, not the spike.
    # 1000 * 2 = 2000, comfortably above the MIN_THRESHOLD floor.
    assert t == 1000.0 * THRESHOLD_MULTIPLIER


def test_threshold_scales_with_noisy_but_consistent_calibration():
    # If the WHOLE idle period is genuinely noisy, the threshold should track it.
    diffs = [1500.0] * 20
    t = threshold_from_samples(diffs)
    assert t == 1500.0 * THRESHOLD_MULTIPLIER


def test_threshold_never_exceeds_frame_fraction_cap():
    # Even a catastrophically noisy calibration (every sample is 200k px)
    # must not produce a threshold that blinds us to a 0.5%-of-frame event.
    frame_pixels = 1_920 * 1_080
    diffs = [200_000.0] * 20
    t = threshold_from_samples(diffs, frame_pixel_count=frame_pixels)
    assert t == frame_pixels * MAX_TRIGGER_FRACTION


def test_calibrator_collects_expected_diff_count():
    mask = np.ones((20, 20), dtype=np.uint8)
    c = Calibrator(mask=mask)

    frame_a = np.zeros((20, 20, 3), dtype=np.uint8)
    frame_b = np.full((20, 20, 3), 100, dtype=np.uint8)

    for i in range(CALIBRATION_FRAMES + 1):
        c.feed(frame_a if i % 2 == 0 else frame_b)

    assert len(c.diffs) == CALIBRATION_FRAMES
    assert c.done is True
    assert c.threshold() > 0.0
