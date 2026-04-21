#!/usr/bin/env bash
# Build a self-contained .dmg for macOS.
# Requires: Python 3.10+, pip, PyInstaller, hdiutil (ships with macOS).
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
cd "$here"

APP_NAME="Roblox AFK Guard"
DMG_NAME="RobloxAFKGuard"

echo "==> Installing build dependencies"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install "pyinstaller>=6.0"

echo "==> Cleaning previous build output"
rm -rf build dist

echo "==> Running PyInstaller"
python3 -m PyInstaller --noconfirm pyinstaller.spec

APP_PATH="dist/${APP_NAME}.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "!! Expected $APP_PATH to exist; PyInstaller output unexpected." >&2
  ls -la dist >&2 || true
  exit 1
fi

DMG_PATH="dist/${DMG_NAME}.dmg"
echo "==> Creating ${DMG_PATH}"
rm -f "$DMG_PATH"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$APP_PATH" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo "==> Done: $DMG_PATH"
