#!/usr/bin/env python3
"""Firmware-gated wired Android Auto setup for the tested 2025 Oshan X7."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET

from prepare import find_adb

VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parent
PROFILE_PATH = ROOT / "profiles" / "f202-mca-rhd-20241022.json"
CARAUTO = "com.eryanet.vlink"
RECEIVER = "com.andrerinas.headunitrevived"
SYSTEMUI = "com.android.systemui"
PREFS = ("/data/user_de/0/com.android.systemui/shared_prefs/"
         "com.incall.apps.common.utils.SharePrefrecenceUtil.xml")
MAIN_ACTIVITY = RECEIVER + "/com.andrerinas.openheadunit.main.MainActivity"
PROFILE = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
ENABLE_COMMANDS = {0: "default-state", 1: "enable", 2: "disable",
                   3: "disable-user", 4: "disable-until-used"}


class SetupError(Exception):
    """A refused operation or an operation needing user attention."""


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_json(path, value):
    """Replace a local journal atomically; never expose a half-written backup."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".journal-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def exclusive(state_dir):
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = state_dir / "operation.lock"
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise SetupError(
            f"Another setup/restore may be running. Check before removing {lock}.") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


class ADB:
    def __init__(self, executable="adb", port=5037, serial=None):
        self.executable = executable
        self.port = port
        self.serial = serial

    def run(self, *args, target=True, timeout=30, allow_failure=False):
        command = [self.executable, "-P", str(self.port)]
        if target:
            if not self.serial:
                raise SetupError("No USB device was selected.")
            command += ["-s", self.serial]
        command += list(args)
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=timeout)
        except FileNotFoundError as exc:
            raise SetupError("adb is missing. Run prepare.py to download official Platform Tools, "
                             "or have your agent follow docs/agent-setup.md.") from exc
        except subprocess.TimeoutExpired as exc:
            raise SetupError("ADB timed out. Reconnect the laptop by USB, then run status or restore.") from exc
        if result.returncode and not allow_failure:
            detail = (result.stderr or result.stdout).strip()[:1200]
            raise SetupError(f"ADB command failed: {detail}")
        return result

    def shell(self, *args, root=False, allow_failure=False):
        tokens = (["su", "0"] if root else []) + list(args)
        return self.run("shell", shlex.join(tokens), allow_failure=allow_failure).stdout.strip()

    def select_usb(self):
        output = self.run("devices", "-l", target=False).stdout
        entries = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] != "List" and not line.startswith("*"):
                entries.append((parts[0], parts[1], parts[2:]))
        # A USB descriptor is required, including when --serial is supplied.
        usb = [e for e in entries if any(x.startswith("usb:") for x in e[2])]
        ready = [e for e in usb if e[1] == "device"]
        if self.serial:
            if not any(e[0] == self.serial for e in ready):
                raise SetupError("The requested device is not an authorized, online USB transport. "
                                 "Enable debugging, accept authorization, and check the ADB port.")
        else:
            if len(ready) != 1:
                raise SetupError("Connect exactly one authorized USB device (the car), or use --serial. "
                                 "Disconnect phones/emulators. Accept the car's debugging prompt. "
                                 "If your existing ADB server uses 5038, add --adb-port 5038.")
            self.serial = ready[0][0]
        return self.serial


def parse_properties(text):
    return dict(re.findall(r"^\[([^\]]+)\]: \[(.*)\]$", text, re.MULTILINE))


def parse_package(text):
    match = re.search(r"^\s*User 0:([^\n]*)", text, re.MULTILINE)
    if not match or not re.search(r"\binstalled=true\b", match[1]):
        return {"installed": False}
    enabled = re.search(r"\benabled=(\d+)\b", match[1])
    if not enabled or int(enabled[1]) not in ENABLE_COMMANDS:
        raise SetupError("Cannot determine the exact package enabled state for Android user 0.")
    result = {"installed": True, "enabled": int(enabled[1])}
    for key, pattern in [("version_code", r"\bversionCode=(\d+)"),
                         ("version_name", r"^\s*versionName=([^\n]+)")]:
        found = re.search(pattern, text, re.MULTILINE)
        if found:
            result[key] = int(found[1]) if key == "version_code" else found[1].strip()
    return result


def parse_layout(xml):
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise SetupError("Factory fullscreen preferences could not be parsed; no write is safe.") from exc
    if root.tag != "map":
        raise SetupError("Unexpected factory fullscreen preferences format.")
    entries = [e for e in root if e.attrib.get("name") == RECEIVER]
    if not entries:
        return None
    if len(entries) != 1 or entries[0].tag != "int":
        raise SetupError("Unexpected fullscreen preference type or duplicate key.")
    try:
        value = int(entries[0].attrib["value"])
    except (KeyError, ValueError) as exc:
        raise SetupError("Invalid factory fullscreen preference value.") from exc
    if not -(2**31) <= value < 2**31:
        raise SetupError("Fullscreen value is outside the Android integer range.")
    return value


def package(adb, name):
    return parse_package(adb.shell("dumpsys", "package", name))


def apk_path(adb, name):
    paths = [line[8:] for line in adb.shell("pm", "path", "--user", "0", name).splitlines()
             if line.startswith("package:")]
    if len(paths) != 1 or not re.fullmatch(r"/[A-Za-z0-9_./+=@~-]+\.apk", paths[0]):
        raise SetupError(f"Expected one ordinary APK for {name}; split/unknown installations are unsupported.")
    return paths[0]


def remote_hash(adb, path):
    output = adb.shell("sha256sum", path)
    match = re.match(r"([0-9a-fA-F]{64})\s", output)
    if not match:
        raise SetupError("Could not read a device APK's SHA-256.")
    return match[1].lower()


def inspect(adb):
    """Read only: every listed mismatch prevents setup AND restore writes."""
    adb.select_usb()
    props = parse_properties(adb.shell("getprop"))
    failures = []
    for key, expected in PROFILE["properties"].items():
        if props.get(key) != expected:
            failures.append(f"{key}: expected {expected!r}, got {props.get(key)!r}")
    size_text = adb.shell("wm", "size")
    size = re.search(r"Physical size:\s*(\d+x\d+)", size_text)
    if not size or size[1] != PROFILE["physical_size"]:
        failures.append("Physical display must be 1920x720.")
    if re.search(r"Override size:", size_text):
        failures.append("An overridden display size is unsupported; restore factory size first.")
    # Reject unknown firmware before attempting root or reading private preferences.
    if failures:
        return {"compatible": False, "profile": PROFILE["id"], "mismatches": failures}
    if adb.shell("am", "get-current-user") != "0":
        failures.append("Android user 0 must be the current user.")
    if adb.shell("getprop", "sys.boot_completed") != "1":
        failures.append("Wait for Android to finish booting.")
    for name in PROFILE["required_packages"]:
        state = package(adb, name)
        if not state["installed"]:
            failures.append(f"Required factory package is missing for user 0: {name}")
        elif name != CARAUTO and state["enabled"] not in (0, 1):
            failures.append(f"Required factory package is disabled for user 0: {name}")
    launcher = PROFILE["launcher"]
    path = apk_path(adb, launcher["package"])
    if path != launcher["path"] or remote_hash(adb, path) != launcher["sha256"]:
        failures.append("Factory launcher path/hash does not match the verified original.")
    if failures:
        return {"compatible": False, "profile": PROFILE["id"], "mismatches": failures}
    if not re.search(r"\buid=0\b", adb.shell("id", root=True)):
        raise SetupError("The tested firmware's existing 'su 0' access is unavailable. Do not root or flash it.")
    xml = adb.shell("cat", PREFS, root=True)
    layout = parse_layout(xml)
    receiver = package(adb, RECEIVER)
    if receiver["installed"]:
        path = apk_path(adb, RECEIVER)
        receiver["sha256"] = remote_hash(adb, path)
        pinned = PROFILE["receiver"]
        if (receiver.get("version_code") != pinned["version_code"] or
                receiver.get("version_name") != pinned["version_name"] or
                receiver["sha256"] != pinned["sha256"] or receiver["enabled"] not in (0, 1)):
            failures.append("Existing Open Headunit is not the pinned, enabled 3.5.0 APK. "
                            "This tool will not replace or downgrade it.")
    return {"compatible": not failures, "profile": PROFILE["id"], "mismatches": failures,
            "carauto": package(adb, CARAUTO), "receiver": receiver,
            "fullscreen_value": layout, "usb_mode": props.get("OTG_MODE", "unknown"),
            "firmware": props["ro.build.display.id"], "root": "su 0",
            "_prefs_xml": xml}


def require_compatible(report):
    if not report["compatible"]:
        raise SetupError("Unsupported configuration; no changes made. " + "; ".join(report["mismatches"]))


def verify_apk(path):
    path = Path(path).resolve()
    pinned = PROFILE["receiver"]
    if not path.is_file() or path.stat().st_size != pinned["bytes"] or digest(path) != pinned["sha256"]:
        raise SetupError("APK size/SHA-256 does not match the pinned Open Headunit 3.5.0 release.")
    return path


def obtain_apk(state_dir, supplied=None):
    if supplied:
        return verify_apk(supplied)
    state_dir = Path(state_dir).expanduser().resolve()
    cache = state_dir / "cache"
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = cache / "open-headunit-3.5.0.apk"
    if target.exists():
        return verify_apk(target)
    fd, temporary = tempfile.mkstemp(prefix="download-", dir=cache)
    try:
        request = urllib.request.Request(PROFILE["receiver"]["url"],
                                         headers={"User-Agent": "oshan-x7-setup/" + VERSION})
        with os.fdopen(fd, "wb") as stream:
            with urllib.request.urlopen(request, timeout=45) as response:
                if not response.geturl().startswith("https://"):
                    raise SetupError("Refusing a download redirected away from HTTPS.")
                remaining = PROFILE["receiver"]["bytes"]
                while True:
                    block = response.read(min(1024 * 1024, remaining + 1))
                    if not block:
                        break
                    remaining -= len(block)
                    if remaining < 0:
                        raise SetupError("Downloaded APK exceeds the pinned size.")
                    stream.write(block)
        verify_apk(temporary)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


def backup_path(adb, state_dir):
    # USB identity is deliberately local; never put it in public profiles.
    identity = hashlib.sha256(adb.serial.encode("utf-8")).hexdigest()[:24]
    return state_dir / "devices" / identity / "backup.json"


def load_backup(path, adb):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SetupError(f"Cannot read the original backup: {path}") from exc
    if not isinstance(value, dict):
        raise SetupError("Backup must contain an object.")
    if (value.get("schema") != 1 or value.get("profile") != PROFILE["id"] or
            value.get("serial") != adb.serial):
        raise SetupError("Backup identity/profile differs from the connected device; refusing restore.")
    original = value.get("original", {})
    if not isinstance(original, dict):
        raise SetupError("Backup contains invalid original settings.")
    carauto = original.get("carauto", {})
    receiver = original.get("receiver", {})
    if (not isinstance(carauto, dict) or not isinstance(receiver, dict) or
            carauto.get("installed") is not True or type(carauto.get("enabled")) is not int or
            carauto.get("enabled") not in ENABLE_COMMANDS or
            type(receiver.get("installed")) is not bool):
        raise SetupError("Backup contains invalid original package states.")
    if (type(value.get("restored")) is not bool or not isinstance(value.get("phase"), str) or
            not isinstance(value.get("operations"), list) or
            any(not isinstance(e, dict) or not isinstance(e.get("name"), str) or
                type(e.get("complete")) is not bool for e in value["operations"])):
        raise SetupError("Backup contains an invalid operation journal.")
    layout = original.get("fullscreen_value")
    if layout is not None and (type(layout) is not int or not -(2**31) <= layout < 2**31):
        raise SetupError("Backup contains an invalid fullscreen value.")
    return value


def create_backup(path, adb, report):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Atomic journal is durable before the first device mutation.
    value = {"schema": 1, "tool_version": VERSION, "profile": PROFILE["id"],
             "serial": adb.serial, "created_at": now(), "phase": "backed_up",
             "original": {key: report[key] for key in ("carauto", "receiver", "fullscreen_value")},
             "operations": [], "restored": False}
    fd = os.open(path.parent / "systemui-prefs-before.xml", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(report["_prefs_xml"] + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    write_json(path, value)
    return value


def operation(path, journal, name, action):
    entry = {"name": name, "started_at": now(), "complete": False}
    journal["operations"].append(entry)
    journal["phase"] = name
    write_json(path, journal)
    action()
    entry["complete"] = True
    write_json(path, journal)


def set_enabled(adb, value):
    adb.shell("pm", ENABLE_COMMANDS[value], "--user", "0", CARAUTO, root=True)
    actual = package(adb, CARAUTO)
    if actual.get("enabled") != value:
        raise SetupError("CarAuto enabled state did not match the requested value.")


def broadcast_layout(adb, value):
    adb.shell("am", "broadcast", "--user", "0", "-p", SYSTEMUI,
              "-a", "com.chinatsp.systemui.ACTION_APP_INFO", "--es", "packageName", RECEIVER,
              "--ei", "appCentered", str(value), root=True)
    # Broadcast completion alone is insufficient: SharedPreferences persists asynchronously.
    for attempt in range(10):
        if parse_layout(adb.shell("cat", PREFS, root=True)) == value:
            return
        if attempt < 9:
            time.sleep(0.2)
    raise SetupError("Factory fullscreen preference did not persist. Reconnect and run restore.")


def refresh(adb):
    adb.shell("am", "broadcast", "--user", "0", "-p", SYSTEMUI,
              "-a", "com.chinatsp.activity.onpostresume", "--es", "packageName", RECEIVER, root=True)


def install(adb, path):
    result = adb.run("install", "--user", "0", str(path), timeout=180)
    if not re.search(r"\bSuccess\b", result.stdout):
        raise SetupError("ADB did not confirm successful installation.")
    state = package(adb, RECEIVER)
    if (not state["installed"] or state.get("version_code") != PROFILE["receiver"]["version_code"] or
            remote_hash(adb, apk_path(adb, RECEIVER)) != PROFILE["receiver"]["sha256"]):
        raise SetupError("Installed receiver did not pass verification.")


def setup(adb, state_dir, report, supplied_apk=None):
    require_compatible(report)
    path = backup_path(adb, state_dir)
    with exclusive(state_dir):
        journal = load_backup(path, adb) if path.exists() else None
        if journal and journal["restored"]:
            raise SetupError("This backup has already been restored. Keep it, and choose a new "
                             "--state-dir for a new setup cycle.")
        if journal and journal["phase"] not in ("backed_up", "configured"):
            raise SetupError("An earlier operation was interrupted. Run restore before starting again.")
        if journal and journal["phase"] == "configured":
            if (report["carauto"]["enabled"] == 3 and report["fullscreen_value"] == 0 and
                    report["receiver"]["installed"]):
                return {"status": "already_configured", "backup": str(path), "device_writes": False,
                        "next": "Disconnect the laptop, select USB Host mode, and connect the phone."}
            raise SetupError("Device settings changed after setup. Run restore before reapplying.")
        # Obtain/verify the artifact before making a backup or writing to the car.
        apk = None if report["receiver"]["installed"] else obtain_apk(state_dir, supplied_apk)
        if journal is None:
            journal = create_backup(path, adb, report)
        try:
            if apk is not None:
                operation(path, journal, "install_receiver", lambda: install(adb, apk))
            if report["carauto"]["enabled"] != 3:
                operation(path, journal, "disable_carauto", lambda: set_enabled(adb, 3))
            if report["fullscreen_value"] != 0:
                operation(path, journal, "fullscreen", lambda: broadcast_layout(adb, 0))
            # Launch once; all first-run grants and connection choices stay visible to the owner.
            operation(path, journal, "open_receiver",
                      lambda: adb.shell("am", "start", "--user", "0", "-n", MAIN_ACTIVITY))
            operation(path, journal, "refresh_layout", lambda: refresh(adb))
            verified = (package(adb, CARAUTO).get("enabled") == 3 and
                        parse_layout(adb.shell("cat", PREFS, root=True)) == 0 and
                        package(adb, RECEIVER).get("installed"))
            if not verified:
                raise SetupError("Final read-back failed. Run restore with the saved backup.")
            journal["phase"] = "configured"
            journal["configured_at"] = now()
            write_json(path, journal)
        except (Exception, KeyboardInterrupt):
            # A dropped cable cannot be rolled back over a nonexistent connection. Preserve the
            # write-ahead journal so restore can finish after USB access returns.
            print(f"Setup interrupted. Backup retained: {path}. Reconnect and run restore.", file=sys.stderr)
            raise
    return {"status": "configured", "backup": str(path), "projection_tested": False,
            "next": ["Complete Open Headunit onboarding and choose USB; allow its requested permissions.",
                     "Disconnect the laptop, select USB Host mode in factory settings, and connect the phone.",
                     "Accept phone/USB prompts; verify picture, audio, touch, microphone, and factory controls."],
            "note": "Small factory Home/Back overlays remain. Wireless is untested."}


def restore(adb, state_dir, report):
    require_compatible(report)
    path = backup_path(adb, state_dir)
    with exclusive(state_dir):
        journal = load_backup(path, adb)
        if journal["restored"]:
            return {"status": "already_restored", "device_writes": False, "backup": str(path)}
        original = journal["original"]
        wanted = original["fullscreen_value"]
        # The verified factory API has no delete-key command. -1 has the same layout behavior
        # as an originally absent key, without rewriting all of SystemUI's preferences.
        wanted = -1 if wanted is None else wanted
        operation(path, journal, "restore_fullscreen", lambda: broadcast_layout(adb, wanted))
        operation(path, journal, "refresh_layout_restore", lambda: refresh(adb))
        operation(path, journal, "restore_carauto",
                  lambda: set_enabled(adb, original["carauto"]["enabled"]))
        # Only remove the user app if THIS setup cycle could have installed it. Never uninstall
        # a factory package or a receiver that was already present before setup.
        installed_by_tool = any(e["name"] == "install_receiver" for e in journal["operations"])
        if not original["receiver"]["installed"] and report["receiver"]["installed"] and installed_by_tool:
            def remove_receiver():
                adb.shell("pm", "uninstall", "--user", "0", RECEIVER, root=True)
                if package(adb, RECEIVER)["installed"]:
                    raise SetupError("Could not remove the receiver installed by this setup.")
            operation(path, journal, "remove_receiver", remove_receiver)
        journal["phase"] = "restored"
        journal["restored"] = True
        journal["restored_at"] = now()
        write_json(path, journal)
    return {"status": "restored", "backup": str(path),
            "note": "Originally absent fullscreen key is restored as -1 (factory default behavior). "
                    "Existing Open Headunit installs and their settings are retained."}


def public_report(report):
    return {key: value for key, value in report.items() if not key.startswith("_")}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("command", choices=("check", "setup", "status", "restore"))
    result.add_argument("--version", action="version", version=VERSION)
    found = find_adb()
    default_adb = str(found[0]) if found else "adb"
    result.add_argument("--adb", default=default_adb, help="Path to adb executable (system or prepared private copy)")
    result.add_argument("--adb-port", type=int, default=5037, help="Local ADB server port (default: 5037)")
    result.add_argument("--serial", help="Explicit USB serial when more than one USB device is connected")
    result.add_argument("--state-dir", type=Path, default=ROOT / ".oshan-x7",
                        help="Local private backup/cache directory; keep it for restore")
    result.add_argument("--apk", type=Path, help="Use an already downloaded pinned APK instead of downloading")
    result.add_argument("--json", action="store_true", help="Emit one JSON object for agent/tool use")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if not 1 <= args.adb_port <= 65535:
            raise SetupError("ADB port must be between 1 and 65535.")
        if args.apk and args.command != "setup":
            raise SetupError("--apk is only used by setup.")
        adb = ADB(args.adb, args.adb_port, args.serial)
        state_dir = args.state_dir.expanduser().resolve()
        report = inspect(adb)
        if args.command in ("check", "status"):
            result = public_report(report)
            result["device_writes"] = False
            result["projection_tested"] = False
            if report["compatible"]:
                path = backup_path(adb, state_dir)
                result["backup_exists"] = path.exists()
                if path.exists():
                    journal = load_backup(path, adb)
                    result["backup_phase"] = journal["phase"]
            code = 0 if report["compatible"] else 2
        elif args.command == "setup":
            result, code = setup(adb, state_dir, report, args.apk), 0
        else:
            result, code = restore(adb, state_dir, report), 0
        if args.json:
            print(json.dumps({"ok": code == 0, **result}))
        else:
            print(json.dumps(result, indent=2))
        return code
    except KeyboardInterrupt:
        message, code = "Interrupted. Reconnect by USB and run status/restore if setup had started.", 130
    except (SetupError, OSError, ValueError) as exc:
        message, code = str(exc), 2
    if args.json:
        print(json.dumps({"ok": False, "error": message}))
    else:
        print("Error: " + message, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
