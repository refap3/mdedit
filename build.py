#!/usr/bin/env python3
"""
MDEdit build script
Usage:  python3 build.py

Produces:
  dist/MDEdit.app   — standalone Mac application bundle
  dist/MDEdit.dmg   — drag-to-install disk image
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP_NAME    = "MDEdit"
APP_VERSION = "1.0.0"
ROOT        = Path(__file__).resolve().parent
DIST        = ROOT / "dist"
BUILD       = ROOT / "build"


def run(*cmd, **kwargs):
    flat = [str(c) for c in cmd]
    print("  $", " ".join(flat))
    subprocess.run(flat, check=True, **kwargs)


def step(msg):
    print(f"\n\033[1m==> {msg}\033[0m")


# ---------------------------------------------------------------------------

def install_deps():
    step("Installing / updating build dependencies")
    run(sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller", "-q")
    run(sys.executable, "-m", "pip", "install", "-r", ROOT / "requirements.txt", "-q")


def clean():
    step("Cleaning previous build artefacts")
    for d in (DIST, BUILD):
        if d.exists():
            shutil.rmtree(d)
            print(f"  removed {d}")


def build_app():
    step("Running PyInstaller")
    run(sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        ROOT / "mdedit.spec",
        cwd=ROOT)

    app = DIST / f"{APP_NAME}.app"
    if not app.exists():
        sys.exit(f"\nERROR: expected {app} — PyInstaller may have failed.")
    print(f"  built  {app}")
    return app


def create_dmg(app: Path) -> Path:
    step("Creating .dmg disk image")
    dmg = DIST / f"{APP_NAME}-{APP_VERSION}.dmg"
    staging = Path(tempfile.mkdtemp(prefix="mdedit_dmg_"))

    try:
        # Copy .app and add /Applications symlink for drag-install UX
        shutil.copytree(app, staging / app.name, symlinks=True)
        (staging / "Applications").symlink_to("/Applications")

        run("hdiutil", "create",
            "-volname",  APP_NAME,
            "-srcfolder", staging,
            "-ov",
            "-format",  "UDZO",       # compressed read-only
            dmg)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    print(f"  built  {dmg}")
    return dmg


def verify(dmg: Path):
    step("Verifying disk image")
    run("hdiutil", "verify", dmg)


def summarise(app: Path, dmg: Path):
    step("Done")
    app_mb = sum(f.stat().st_size for f in app.rglob("*") if f.is_file()) / 1e6
    dmg_mb = dmg.stat().st_size / 1e6
    print(f"  App bundle : {app}  ({app_mb:.0f} MB)")
    print(f"  Disk image : {dmg}  ({dmg_mb:.0f} MB)")
    print()
    print("To install: open the .dmg and drag MDEdit to Applications.")


# ---------------------------------------------------------------------------

def main():
    if sys.platform != "darwin":
        sys.exit("This build script currently targets macOS only.")

    install_deps()
    clean()
    app = build_app()
    dmg = create_dmg(app)
    verify(dmg)
    summarise(app, dmg)


if __name__ == "__main__":
    main()
