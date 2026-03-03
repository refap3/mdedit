# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []

for pkg in ("PyQt6", "markdown", "pygments"):
    d, b, h = collect_all(pkg)
    datas     += d
    binaries  += b
    hiddenimports += h

a = Analysis(
    ["mdedit.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MDEdit",
    debug=False,
    strip=False,
    upx=False,          # UPX can break Qt binaries on macOS — keep off
    console=False,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MDEdit",
)

app = BUNDLE(
    coll,
    name="MDEdit.app",
    icon=None,           # replace with "mdedit.icns" once you have an icon
    bundle_identifier="com.mdedit.app",
    version="1.0.0",
    info_plist={
        "NSPrincipalClass": "NSApplication",
        "NSAppleScriptEnabled": False,
        "NSHighResolutionCapable": True,
        "CFBundleDisplayName": "MDEdit",
        "CFBundleName": "MDEdit",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSMinimumSystemVersion": "10.13",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Markdown Document",
                "CFBundleTypeExtensions": ["md", "markdown"],
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Owner",
            },
            {
                "CFBundleTypeName": "Plain Text",
                "CFBundleTypeExtensions": ["txt"],
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Alternate",
            },
        ],
    },
)
