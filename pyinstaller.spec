# -*- mode: python ; coding: utf-8 -*-
# Shared PyInstaller spec for Roblox AFK Guard.
# Invoked by scripts/build_macos.sh and scripts/build_windows.bat.

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve()
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

APP_NAME = "Roblox AFK Guard"
EXE_NAME = "RobloxAFKGuard"

icon_path = None
if IS_MAC and (ROOT / "assets" / "icon.icns").exists():
    icon_path = str(ROOT / "assets" / "icon.icns")
elif IS_WIN and (ROOT / "assets" / "icon.ico").exists():
    icon_path = str(ROOT / "assets" / "icon.ico")

datas = []
assets_dir = ROOT / "assets"
if assets_dir.exists():
    datas.append((str(assets_dir), "assets"))

hidden_imports = []
if IS_MAC:
    # pyobjc's Quartz is a namespace of C extensions; PyInstaller 6 sometimes
    # misses the sub-bindings for CGWindowList* unless we name them explicitly.
    hidden_imports += [
        "Quartz",
        "Quartz.CoreGraphics",
        "objc",
    ]
if IS_WIN:
    hidden_imports += [
        "pygetwindow",
        "win32gui",
        "win32con",
        "win32process",
        "win32api",
        "win32ui",
    ]

# NOTE: PyInstaller 6.0 removed the `cipher` kwarg (bytecode obfuscation was
# retired) and the `win_no_prefer_redirects` / `win_private_assemblies` flags.
# Keep this spec compatible with PyInstaller >= 6.0 only.
a = Analysis(
    [str(ROOT / "src" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

# PyInstaller 6 pattern:
#   - onedir (macOS): EXE(..., exclude_binaries=True) → COLLECT(...) → BUNDLE(.app)
#   - onefile (Windows): EXE(pyz, scripts, binaries, zipfiles, datas, ...) — no COLLECT.
# Older specs that mixed both into one EXE() call and used `onefile=` kwarg stopped
# working in PyInstaller 6.
if IS_MAC:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=EXE_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=EXE_NAME,
    )
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=icon_path,
        bundle_identifier="com.hgoldrich.robloxafkguard",
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "NSHighResolutionCapable": True,
            "NSAppleEventsUsageDescription": (
                "Roblox AFK Guard uses Apple Events to bring the selected "
                "Roblox window to the front so it can be monitored."
            ),
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=EXE_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )
