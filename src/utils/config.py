from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".robloxafkguard"
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class ResolutionProfile:
    width: int
    height: int
    ignore_regions: list[tuple[int, int, int, int]] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.width}x{self.height}"


def _key(width: int, height: int) -> str:
    return f"{width}x{height}"


def load() -> dict:
    if not CONFIG_PATH.exists():
        return {"profiles": {}}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"profiles": {}}


def save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_profile(width: int, height: int) -> ResolutionProfile | None:
    data = load()
    raw = data.get("profiles", {}).get(_key(width, height))
    if raw is None:
        return None
    regions = [tuple(r) for r in raw.get("ignore_regions", [])]
    return ResolutionProfile(width=width, height=height, ignore_regions=regions)


def put_profile(profile: ResolutionProfile) -> None:
    data = load()
    data.setdefault("profiles", {})[profile.key] = {
        "width": profile.width,
        "height": profile.height,
        "ignore_regions": [list(r) for r in profile.ignore_regions],
    }
    save(data)
