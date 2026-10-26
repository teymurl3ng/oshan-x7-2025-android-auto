#!/usr/bin/env python3
"""Find ADB or install Google's Platform Tools privately beside this repository."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / ".oshan-x7" / "tools"
URLS = {
    "Windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
    "Darwin": "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
    "Linux": "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
}


class PreparationError(Exception):
    pass


def adb_name():
    return "adb.exe" if platform.system() == "Windows" else "adb"


def working_adb(candidate):
    try:
        result = subprocess.run([str(candidate), "version"], capture_output=True,
                                text=True, timeout=15)
        if result.returncode == 0 and "Android Debug Bridge version" in result.stdout:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def find_adb():
    candidates = [shutil.which("adb"), TOOLS / "platform-tools" / adb_name()]
    for variable in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        if os.environ.get(variable):
            candidates.append(Path(os.environ[variable]) / "platform-tools" / adb_name())
    if platform.system() == "Windows" and os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "Android" / "Sdk" / "platform-tools" / "adb.exe")
    elif platform.system() == "Darwin":
        candidates.append(Path.home() / "Library" / "Android" / "sdk" / "platform-tools" / "adb")
    elif platform.system() == "Linux":
        candidates.append(Path.home() / "Android" / "Sdk" / "platform-tools" / "adb")
    for candidate in candidates:
        if candidate:
            version = working_adb(candidate)
            if version:
                return Path(candidate).resolve(), version
    return None


def extract_tools(archive, destination):
    """Extract only the expected directory, without following archive links."""
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        if sum(e.file_size for e in entries) > 300 * 1024 * 1024:
            raise PreparationError("Platform Tools archive is unexpectedly large.")
        for entry in entries:
            # ZIP paths use '/', regardless of the laptop's OS.
            parts = entry.filename.split("/")
            raw_name = entry.orig_filename  # Windows' ZIP reader can normalize backslashes.
            mode = entry.external_attr >> 16
            if (parts[0] != "platform-tools" or ".." in parts or
                    "\\" in raw_name or ":" in raw_name or "\x00" in raw_name or stat.S_ISLNK(mode)):
                raise PreparationError("Unexpected path or link in Platform Tools archive.")
        package.extractall(destination)
    executable = destination / "platform-tools" / adb_name()
    if not executable.is_file():
        raise PreparationError("Official archive did not contain the expected adb executable.")
    if platform.system() != "Windows":
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def prepare(download=True):
    if sys.version_info < (3, 10):
        raise PreparationError("Python 3.10+ is required. Follow docs/agent-setup.md to install it.")
    found = find_adb()
    if found:
        return {"status": "ready", "python": sys.executable, "python_version": platform.python_version(),
                "adb": str(found[0]), "adb_version": found[1], "downloaded": False}
    if not download:
        raise PreparationError("No working ADB found. Run prepare.py without --verify-only to download it.")
    system = platform.system()
    if system not in URLS:
        raise PreparationError("Unsupported laptop OS. Install ADB with your trusted package manager.")
    if system == "Linux" and platform.machine().lower() not in ("x86_64", "amd64"):
        raise PreparationError("Google's Linux archive requires x86_64. Have the agent install native "
                               "ADB from your distribution's package manager, then rerun preparation.")
    TOOLS.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = TOOLS / "platform-tools"
    # Keep a broken previous download for diagnosis rather than overwriting files.
    if target.exists():
        raise PreparationError(f"The private ADB at {target} does not run. Have the agent diagnose it "
                               "or move this directory aside before retrying.")
    with tempfile.TemporaryDirectory(prefix="prepare-", dir=TOOLS) as temporary:
        stage = Path(temporary)
        archive = stage / "tools.zip"
        request = urllib.request.Request(URLS[system], headers={"User-Agent": "oshan-x7-setup"})
        with urllib.request.urlopen(request, timeout=45) as response, archive.open("wb") as stream:
            if not response.geturl().startswith("https://"):
                raise PreparationError("Refusing a download redirected away from HTTPS.")
            size = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                if size > 100 * 1024 * 1024:
                    raise PreparationError("Platform Tools download is unexpectedly large.")
                stream.write(block)
        sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
        executable = extract_tools(archive, stage)
        version = working_adb(executable)
        if not version:
            raise PreparationError("Downloaded ADB did not run. Check CPU/OS compatibility and system libraries.")
        os.replace(stage / "platform-tools", target)
    result = {"status": "ready", "python": sys.executable, "python_version": platform.python_version(),
              "adb": str((target / adb_name()).resolve()), "adb_version": version,
              "downloaded": True, "source": URLS[system], "archive_sha256": sha256}
    # The digest is an audit record, not an independently published integrity pin.
    (TOOLS / "download.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verify-only", action="store_true", help="Inspect installed tools without downloading")
    args = parser.parse_args(argv)
    try:
        result = {"ok": True, **prepare(download=not args.verify_only)}
        code = 0
    except (PreparationError, OSError, zipfile.BadZipFile) as error:
        result, code = {"ok": False, "error": str(error)}, 2
    print(json.dumps(result, indent=None if args.json else 2))
    return code


if __name__ == "__main__":
    sys.exit(main())
