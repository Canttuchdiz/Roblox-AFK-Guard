from pathlib import Path

import pytest

from src.utils import config


@pytest.fixture(autouse=True)
def _redirect_config(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")


def test_load_with_no_file_returns_empty_profiles():
    assert config.load() == {"profiles": {}}


def test_round_trip_profile():
    profile = config.ResolutionProfile(
        width=1920,
        height=1080,
        ignore_regions=[(10, 20, 30, 40), (100, 200, 300, 400)],
    )
    config.put_profile(profile)

    loaded = config.get_profile(1920, 1080)
    assert loaded is not None
    assert loaded.width == 1920
    assert loaded.height == 1080
    assert loaded.ignore_regions == [(10, 20, 30, 40), (100, 200, 300, 400)]


def test_unknown_resolution_returns_none():
    config.put_profile(
        config.ResolutionProfile(width=1280, height=720, ignore_regions=[(1, 2, 3, 4)])
    )
    assert config.get_profile(1920, 1080) is None


def test_malformed_config_file_is_tolerated(tmp_path: Path):
    (config.CONFIG_PATH).write_text("{not valid json", encoding="utf-8")
    assert config.load() == {"profiles": {}}
