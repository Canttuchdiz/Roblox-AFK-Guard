# Roblox AFK Guard

A cross-platform (macOS + Windows) GUI utility that watches a selected Roblox
window for on-screen motion and **force-quits Roblox the instant something
moves** — so your idle character bails out before another player or entity
can land a hit on you.

Pixel-diff detection, tuned per-game via a calibration pass, with an
interactive painter for excluding the parts of the screen that *are* supposed
to move while you're idle (your character's idle animation, HUD tickers,
ambient scenery).

## How it works

1. **Pick the Roblox window** you want guarded. The list shows every running
   Roblox process with its title, resolution, and PID.
2. **Paint ignore regions** over your character and any HUD elements that
   animate on their own.
3. **Calibrate** — the guard captures 20 frames over 5 seconds while nothing
   is happening, and sets the trip threshold at 2× the worst observed idle
   diff.
4. **Guard** — a small always-on-top window shows current diff vs. threshold.
   If anything crosses the threshold outside your ignore regions, the
   selected Roblox PID is killed immediately and a "ROBLOX KILLED" banner
   displays for 3 seconds.

Ignore regions and window dimensions are persisted per-resolution to
`~/.robloxafkguard/config.json`, so you only calibrate once per setup.

## Installation

### Pre-built binaries

Download the latest `.dmg` (macOS) or `.exe` (Windows) from the
[Releases](../../releases) page — they are self-contained and do not require
a Python environment.

### Running from source

```bash
git clone <repo>
cd "Anomaly Detection"
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src
```

Python 3.10+ is required.

## Platform notes

### macOS

- On first run, macOS prompts for **Screen Recording** and **Automation**
  permissions. Grant both in *System Settings → Privacy & Security*.
- The Automation permission lets the app activate the Roblox window via
  AppleScript; without it, the countdown will run but the Roblox window
  won't come forward.

### Windows

- No special permissions are required. The app uses `SetForegroundWindow`
  and `TerminateProcess`, both of which work for the current user's own
  processes.

## Building releases locally

```bash
# macOS
bash scripts/build_macos.sh
# → dist/RobloxAFKGuard.dmg

# Windows
scripts\build_windows.bat
# → dist\RobloxAFKGuard.exe
```

Both scripts invoke PyInstaller with the shared `pyinstaller.spec` and then
package the result. CI (`.github/workflows/release.yml`) runs the same
scripts on GitHub-hosted `macos-latest` and `windows-latest` runners for
every `v*` tag and attaches the artifacts to the GitHub Release.

## Project layout

```
src/
├── app.py            # State machine: Picker → Countdown → Painter → Calibrate → Guard
├── gui/              # tkinter screens
├── logic/            # Pixel diff, calibration, guard tick loop
├── utils/            # Capture, process-kill, window enum, config IO
└── platform/         # macOS + Windows shims (window enum + focus)
tests/                # Unit tests for diff math, threshold, config round-trip
scripts/              # build_macos.sh, build_windows.bat
.github/workflows/    # release.yml
```

## Contributing

1. Fork and create a feature branch.
2. `pip install -r requirements.txt` and run `pytest tests/`.
3. Keep GUI changes confined to `src/gui/`; keep pixel-math changes in
   `src/logic/` with tests.
4. Open a PR. CI runs tests on macOS + Windows.

## License

MIT — see [LICENSE](LICENSE).
