import numpy as np

from src.logic.detector import Detector, build_ignore_mask, frame_diff


def _frame(h=40, w=60, fill=0):
    return np.full((h, w, 3), fill, dtype=np.uint8)


def test_build_ignore_mask_zeros_inside_regions():
    mask = build_ignore_mask(20, 30, [(5, 5, 10, 10)])
    assert mask.shape == (20, 30)
    assert mask[6, 6] == 0
    assert mask[4, 4] == 1
    assert mask[15, 15] == 1


def test_build_ignore_mask_clips_out_of_bounds():
    mask = build_ignore_mask(20, 30, [(-5, -5, 100, 100)])
    assert mask.sum() == 0


def test_frame_diff_identical_is_zero():
    f = _frame(fill=128)
    mask = np.ones(f.shape[:2], dtype=np.uint8)
    assert frame_diff(f, f, mask) == 0.0


def test_frame_diff_ignores_masked_regions():
    prev = _frame(fill=0)
    curr = prev.copy()
    curr[0:10, 0:10, :] = 255  # huge change, but fully masked
    mask = build_ignore_mask(curr.shape[0], curr.shape[1], [(0, 0, 10, 10)])
    assert frame_diff(prev, curr, mask) == 0.0


def test_frame_diff_counts_moved_pixel_count():
    # A 10x10 block of 100 pixels changing by a full 255 per channel should
    # count as exactly 100 moved pixels.
    prev = _frame(fill=0)
    curr = prev.copy()
    curr[20:30, 30:40, :] = 255
    mask_all = np.ones(curr.shape[:2], dtype=np.uint8)
    assert frame_diff(prev, curr, mask_all) == 100.0


def test_frame_diff_ignores_sub_noise_changes():
    # Per-pixel channel-sum delta below PIXEL_CHANGE_DELTA must not register —
    # this is what protects us from JPEG / video compression noise.
    prev = _frame(fill=0)
    curr = prev.copy()
    curr[:, :, 0] = 5  # 5 + 0 + 0 = 5 per-pixel, well below threshold (30)
    mask = np.ones(prev.shape[:2], dtype=np.uint8)
    assert frame_diff(prev, curr, mask) == 0.0


def test_detector_trips_only_when_above_threshold():
    prev = _frame(fill=0)
    changed = prev.copy()
    changed[:, :, :] = 255  # every pixel moved
    mask = np.ones(prev.shape[:2], dtype=np.uint8)
    total_pixels = prev.shape[0] * prev.shape[1]
    det = Detector(threshold=total_pixels / 10.0, mask=mask)

    # First frame: no previous frame, never trips.
    diff, tripped = det.step(prev)
    assert diff == 0.0 and tripped is False

    # Identical next frame: trivially below threshold.
    diff, tripped = det.step(prev)
    assert diff == 0.0 and tripped is False

    # Big change → trips.
    diff, tripped = det.step(changed)
    assert tripped is True
    assert diff == float(total_pixels)


def test_detector_no_trip_below_threshold():
    prev = _frame(fill=0)
    tiny = prev.copy()
    tiny[0, 0, :] = 255  # exactly 1 pixel moved
    mask = np.ones(prev.shape[:2], dtype=np.uint8)
    det = Detector(threshold=100.0, mask=mask)

    det.step(prev)
    diff, tripped = det.step(tiny)
    assert diff == 1.0
    assert tripped is False
