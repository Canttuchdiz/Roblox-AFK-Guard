#!/usr/bin/env bash
# Build a self-contained .dmg for macOS.
# Requires: Python 3.10+, pip, PyInstaller, hdiutil (ships with macOS).
#
# Signing / notarization (optional — only runs if these env vars are set):
#   NOTARY_APPLE_ID  — Apple ID email used for notarytool.
#   NOTARY_TEAM_ID   — 10-char Team ID (e.g. MKPUVQGYSS).
#   NOTARY_PASSWORD  — app-specific password from appleid.apple.com.
# If any of the three are missing the script produces an unsigned DMG and
# exits normally — that's the shape we want for local dev builds so nothing
# blocks `bash scripts/build_macos.sh` on your laptop.
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

# -----------------------------------------------------------------------------
# Sign + notarize (CI / release builds). Gated so local dev builds skip cleanly.
# -----------------------------------------------------------------------------
# We auto-detect the identity from the keychain rather than hardcoding the
# common-name string. On CI we import a .p12 into a temp keychain before this
# runs; on a dev Mac the Developer ID cert is already in the login keychain.
SIGNING_IDENTITY=""
if security find-identity -v -p codesigning 2>/dev/null \
     | grep -q "Developer ID Application"; then
  SIGNING_IDENTITY=$(security find-identity -v -p codesigning \
    | awk -F '"' '/Developer ID Application/ {print $2; exit}')
fi

DO_SIGN=0
if [[ -n "$SIGNING_IDENTITY" \
   && -n "${NOTARY_APPLE_ID:-}" \
   && -n "${NOTARY_TEAM_ID:-}" \
   && -n "${NOTARY_PASSWORD:-}" ]]; then
  DO_SIGN=1
fi

if [[ "$DO_SIGN" -eq 1 ]]; then
  ENTITLEMENTS="$here/assets/entitlements.plist"
  echo "==> Signing app with identity: $SIGNING_IDENTITY"

  # --deep walks every embedded Mach-O (PyInstaller ships a lot of .dylib / .so).
  # --timestamp is required for notarization — without it Apple rejects.
  # --options runtime enables the Hardened Runtime that the entitlements rely on.
  codesign --force --deep --timestamp \
    --options runtime \
    --entitlements "$ENTITLEMENTS" \
    --sign "$SIGNING_IDENTITY" \
    "$APP_PATH"

  echo "==> Verifying app signature"
  codesign --verify --deep --strict --verbose=2 "$APP_PATH"

  # Notarize the .app directly by first zipping it (notarytool needs a
  # single file). The resulting ticket is stapled onto the .app, so users
  # who extract it from the DMG still get offline Gatekeeper approval.
  NOTARIZE_ZIP="$(mktemp -d)/app.zip"
  echo "==> Zipping app for notarization → $NOTARIZE_ZIP"
  # ditto preserves bundle structure + xattrs correctly (zip -r mangles symlinks).
  ditto -c -k --keepParent "$APP_PATH" "$NOTARIZE_ZIP"

  echo "==> Submitting app to Apple notary service (this usually takes 1-3 min)"
  xcrun notarytool submit "$NOTARIZE_ZIP" \
    --apple-id "$NOTARY_APPLE_ID" \
    --team-id "$NOTARY_TEAM_ID" \
    --password "$NOTARY_PASSWORD" \
    --wait

  echo "==> Stapling notarization ticket to app"
  xcrun stapler staple "$APP_PATH"
  xcrun stapler validate "$APP_PATH"

  rm -rf "$(dirname "$NOTARIZE_ZIP")"
else
  echo "==> Skipping sign/notarize (missing identity or NOTARY_* env vars)"
fi

# -----------------------------------------------------------------------------
# Package the .app into a drag-to-install DMG.
# -----------------------------------------------------------------------------
DMG_PATH="dist/${DMG_NAME}.dmg"
echo "==> Creating ${DMG_PATH}"
rm -f "$DMG_PATH"

# Stage the .app alongside a symlink to /Applications so the DMG shows the
# familiar "drag the app into Applications" layout when the user opens it.
STAGE="$(mktemp -d)/dmg-root"
mkdir -p "$STAGE"
cp -R "$APP_PATH" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

rm -rf "$STAGE"

# Sign + notarize + staple the DMG itself. Belt-and-suspenders: even though
# the .app inside is already stapled, signing the DMG means Gatekeeper greets
# the download with a clean "from Apple-verified developer" prompt instead of
# the quarantine one.
if [[ "$DO_SIGN" -eq 1 ]]; then
  echo "==> Signing DMG"
  codesign --force --timestamp --sign "$SIGNING_IDENTITY" "$DMG_PATH"

  echo "==> Notarizing DMG"
  xcrun notarytool submit "$DMG_PATH" \
    --apple-id "$NOTARY_APPLE_ID" \
    --team-id "$NOTARY_TEAM_ID" \
    --password "$NOTARY_PASSWORD" \
    --wait

  echo "==> Stapling DMG"
  xcrun stapler staple "$DMG_PATH"
  xcrun stapler validate "$DMG_PATH"
fi

echo "==> Done: $DMG_PATH"
