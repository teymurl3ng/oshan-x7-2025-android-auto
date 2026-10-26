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

import health_checks as health
from prepare import find_adb
from launcher_patch import apply as apply_launcher_patch, PatchError

VERSION = "0.3.0"
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

    def __init__(self, message, **details):
        super().__init__(message)
        self.details = details


class NeedsPermissions(SetupError):
    """A visible permission prompt requires a person, not a rollback."""


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

    def shell(self, *args, root=False, allow_failure=False, timeout=30):
        tokens = (["su", "0"] if root else []) + list(args)
        return self.run("shell", shlex.join(tokens), allow_failure=allow_failure, timeout=timeout).stdout.strip()

    def select_usb(self, timeout=30):
        output = self.run("devices", "-l", target=False, timeout=timeout).stdout
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


def launcher_state(adb, check_home=True):
    """Accept only the immutable factory base or the exact tested system update."""
    pin = PROFILE["launcher"]
    if remote_hash(adb, pin["path"]) != pin["sha256"]:
        raise SetupError("Immutable factory launcher hash does not match the verified original.")
    raw = adb.shell("dumpsys", "package", pin["package"])
    match = re.search(r"^  Package \[com\.chinatsp\.launcher\][^\n]*:\n(.*?)(?=^\S|^  Package |\Z)",
                      raw, re.M | re.S)
    if not match:
        raise SetupError("Cannot identify the active factory launcher package record.")
    block = match[1]
    state = parse_package(block)
    uid = re.search(r"^\s*userId=(\d+)$", block, re.M)
    flags = re.search(r"^\s*(?:pkgFlags|flags)=\[([^\]]*)\]", block, re.M)
    if (not state["installed"] or state.get("enabled") not in (0, 1) or
            state.get("version_code") != pin["version_code"] or not uid or
            int(uid[1]) != pin["uid"] or "android.uid.system/1000" not in block or not flags):
        raise SetupError("Launcher UID, shared UID, version or enabled state is unsupported.")
    flags = set(flags[1].split())
    if "SYSTEM" not in flags:
        raise SetupError("Launcher is not registered as the factory system app.")
    path = apk_path(adb, pin["package"])
    sha = remote_hash(adb, path)
    updated = "UPDATED_SYSTEM_APP" in flags
    if path == pin["path"]:
        valid = sha == pin["sha256"] and not updated
        build = "factory"
    else:
        valid = (sha == pin["update"]["sha256"] and updated and
                 re.fullmatch(r"/data/app/com\.chinatsp\.launcher-[A-Za-z0-9_+=@~-]+/base\.apk", path))
        build = "openhu"
    if not valid:
        raise SetupError("Unknown launcher path/hash; refusing to replace or remove it.")
    home = adb.shell("cmd", "package", "resolve-activity", "--components", "-a",
                     "android.intent.action.MAIN", "-c", "android.intent.category.HOME")
    if check_home and home not in (pin["home"], pin["package"] + "/com.chinatsp.launcher.MainAct"):
        raise SetupError("Unexpected default HOME activity; inspect it before setup.")
    return {"build": build, "sha256": sha, "path": path, "uid": pin["uid"],
            "version_code": pin["version_code"], "updated_system_app": updated, "home": home}


def receiver_state(adb):
    state = package(adb, RECEIVER)
    state["verified"] = not state["installed"]
    if state["installed"]:
        state["sha256"] = remote_hash(adb, apk_path(adb, RECEIVER))
        pin = PROFILE["receiver"]
        state["verified"] = (state.get("version_code") == pin["version_code"] and
                             state.get("version_name") == pin["version_name"] and
                             state["sha256"] == pin["sha256"])
    return state


def inspect(adb, recovery=False):
    """Read only. Recovery keeps identity gates but reports component failures separately."""
    adb.select_usb()
    props = parse_properties(adb.shell("getprop"))
    failures, issues = [], []
    for key, expected in PROFILE["properties"].items():
        if props.get(key) != expected:
            failures.append(f"{key}: expected {expected!r}, got {props.get(key)!r}")
    size_text = adb.shell("wm", "size")
    size = re.search(r"Physical size:\s*(\d+x\d+)", size_text)
    if not size or size[1] != PROFILE["physical_size"]:
        failures.append("Physical display must be 1920x720.")
    if "Override size:" in size_text:
        failures.append("An overridden display size is unsupported; restore factory size first.")
    if props.get("OTG_MODE") != "1":
        failures.append("Select USB Device mode for the laptop before setup or restore.")
    # Reject unknown firmware before root/private preference reads.
    if failures:
        return {"compatible": False, "setup_compatible": False, "recovery_eligible": False,
                "profile": PROFILE["id"], "mismatches": failures}
    if adb.shell("am", "get-current-user") != "0":
        failures.append("Android user 0 must be the current user.")
    booted = adb.shell("getprop", "sys.boot_completed") == "1"
    if not booted:
        issues.append("Android has not completed booting.")
    states = {}
    for name in PROFILE["required_packages"]:
        states[name] = package(adb, name)
        if not states[name]["installed"]:
            issues.append(f"Required factory package is missing for user 0: {name}")
        elif name != CARAUTO and states[name]["enabled"] not in (0, 1):
            issues.append(f"Required factory package is disabled for user 0: {name}")
    try:
        launcher = launcher_state(adb, check_home=not recovery)
        if recovery and launcher["home"] not in (PROFILE["launcher"]["home"],
                PROFILE["launcher"]["package"] + "/com.chinatsp.launcher.MainAct"):
            issues.append("Unexpected default HOME activity; setup is not compatible.")
    except SetupError as exc:
        failures.append(str(exc))
    if failures:
        return {"compatible": False, "setup_compatible": False, "recovery_eligible": False,
                "profile": PROFILE["id"], "mismatches": failures}
    root_available, prefs_readable, xml, layout = False, False, None, None
    try:
        root_available = bool(re.search(r"\buid=0\b", adb.shell("id", root=True)))
        if not root_available:
            raise SetupError("Existing 'su 0' access is unavailable. Do not root or flash the car.")
        xml = adb.shell("cat", PREFS, root=True)
        layout = parse_layout(xml)
        prefs_readable = True
    except SetupError as exc:
        issues.append(str(exc))
    try:
        receiver = receiver_state(adb)
        if not receiver["verified"] or (receiver["installed"] and receiver["enabled"] not in (0, 1)):
            issues.append("Existing Open Headunit is not the pinned, enabled 3.5.0 APK. "
                          "It will not be replaced or downgraded.")
    except SetupError as exc:
        receiver = {"installed": None, "verified": False}
        issues.append(str(exc))
    return {"compatible": not failures and (recovery or not issues),
            "setup_compatible": not failures and not issues,
            "recovery_eligible": not failures, "profile": PROFILE["id"],
            "mismatches": failures + ([] if recovery else issues), "component_issues": issues,
            "carauto": states[CARAUTO], "receiver": receiver,
            "fullscreen_value": layout, "prefs_readable": prefs_readable,
            "usb_mode": props.get("OTG_MODE", "unknown"), "boot_completed": booted,
            "firmware": props["ro.build.display.id"], "root_available": root_available,
            "root": "su 0" if root_available else None, "launcher": launcher, "_prefs_xml": xml}


def require_compatible(report):
    if not report["compatible"]:
        raise SetupError("Configuration refused. " + "; ".join(report["mismatches"]))


def healthy_launch(adb, component, baseline=None):
    try:
        return health.launch(adb, component, baseline,
                             exact_activity=component == PROFILE["launcher"]["home"])
    except health.PermissionsPending as exc:
        raise NeedsPermissions(str(exc)) from exc
    except health.HealthError as exc:
        raise SetupError(str(exc)) from exc


def healthy_systemui(adb, baseline):
    try:
        return health.observe(adb, SYSTEMUI, baseline)
    except health.HealthError as exc:
        raise SetupError(str(exc)) from exc


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


def verify_launcher_file(path, factory=False):
    pin = PROFILE["launcher"] if factory else PROFILE["launcher"]["update"]
    path = Path(path)
    if not path.is_file() or path.stat().st_size != pin["bytes"] or digest(path) != pin["sha256"]:
        raise SetupError("Launcher APK size/SHA-256 does not match the pinned " +
                         ("factory backup." if factory else "tested update."))
    return path


def prepare_launcher(adb, folder):
    """Read the matching factory APK and reconstruct the tested update locally."""
    pin = PROFILE["launcher"]
    update = pin["update"]
    patch = ROOT / update["patch"]
    if (not patch.is_file() or patch.stat().st_size != update["patch_bytes"] or
            digest(patch) != update["patch_sha256"]):
        raise SetupError("Bundled launcher patch is missing or changed; download a complete repo copy.")
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    factory = folder / "factory-launcher.apk"
    target = folder / "openhu-launcher.apk"
    if factory.exists():
        verify_launcher_file(factory, factory=True)
    else:
        fd, temporary = tempfile.mkstemp(prefix=".factory-", dir=folder)
        os.close(fd)
        try:
            adb.run("pull", pin["path"], temporary, timeout=90)
            verify_launcher_file(temporary, factory=True)
            os.chmod(temporary, 0o600)
            with open(temporary, "r+b") as stream:
                os.fsync(stream.fileno())
            os.replace(temporary, factory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    if target.exists():
        return verify_launcher_file(target)
    try:
        payload = apply_launcher_patch(factory.read_bytes(), patch.read_bytes(), update["bytes"])
    except PatchError as exc:
        raise SetupError("Could not reconstruct the pinned launcher: " + str(exc)) from exc
    fd, temporary = tempfile.mkstemp(prefix=".launcher-", dir=folder)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        verify_launcher_file(temporary)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


def load_backup(path, adb):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SetupError(f"Cannot read the original backup: {path}") from exc
    if not isinstance(value, dict):
        raise SetupError("Backup must contain an object.")
    if (type(value.get("schema")) is not int or value.get("schema") not in (1, 2) or
            value.get("profile") != PROFILE["id"] or
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
    if value["schema"] == 2:
        launcher = original.get("launcher")
        pin = PROFILE["launcher"]
        if (not isinstance(launcher, dict) or launcher.get("build") not in {"factory", "openhu"} or
                launcher.get("uid") != pin["uid"] or launcher.get("version_code") != pin["version_code"] or
                launcher.get("sha256") != (pin["sha256"] if launcher["build"] == "factory" else pin["update"]["sha256"])):
            raise SetupError("Backup contains an invalid original launcher identity.")
    elif any(e["name"] == "install_launcher" for e in value["operations"]):
        raise SetupError("Legacy backup cannot own a launcher installation.")
    return value


def create_backup(path, adb, report):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Atomic journal is durable before the first device mutation.
    value = {"schema": 2, "tool_version": VERSION, "profile": PROFILE["id"],
             "serial": adb.serial, "created_at": now(), "phase": "backed_up",
             "original": {key: report[key] for key in ("carauto", "receiver", "fullscreen_value", "launcher")},
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
    try:
        verification = action()
    except (Exception, KeyboardInterrupt) as exc:
        entry["error"] = str(exc) or type(exc).__name__
        entry["failed_at"] = now()
        write_json(path, journal)
        raise
    entry["complete"] = True
    entry["verified_at"] = now()
    if verification is not None:
        entry["verification"] = verification
    write_json(path, journal)
    return verification


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


def install_launcher(adb, path):
    verify_launcher_file(path)
    before = inspect(adb)
    require_compatible(before)
    if (before["launcher"]["build"] != "factory" or before["usb_mode"] != "1" or
            before["carauto"]["enabled"] != 3 or before["fullscreen_value"] != 0 or
            not before["receiver"]["installed"]):
        raise SetupError("Launcher installation requires the verified factory and wired-AA baseline.")
    result = adb.run("install", "--no-streaming", "-r", str(path), timeout=180)
    if not re.search(r"^Success\s*$", result.stdout, re.M):
        raise SetupError("Launcher installation did not confirm success; reconnect and run restore.")
    if launcher_state(adb)["build"] != "openhu":
        raise SetupError("Installed launcher did not pass APK/UID/HOME read-back.")


def restore_launcher(adb):
    before = launcher_state(adb, check_home=False)
    if before["build"] == "factory":
        launcher_state(adb)  # Verify HOME, including after an uncertain earlier rollback.
        return
    # This is an updated SYSTEM app. No --user: that would remove/disable HOME
    # for user 0 instead of restoring the immutable base. Equal versionCode and
    # -k retain its data, following the tested Android 9 rollback procedure.
    result = adb.shell("pm", "uninstall", "-k", PROFILE["launcher"]["package"])
    if result != "Success" or launcher_state(adb)["build"] != "factory":
        raise SetupError("Factory launcher rollback did not verify. Keep USB connected and the journal.")


def touched(journal, name):
    return any(e["name"] == name for e in journal["operations"])


def recovery_report(adb):
    report = inspect(adb, recovery=True)
    require_compatible(report)
    if report["usb_mode"] != "1":
        raise SetupError("Select USB Device mode for the laptop before setup or restore.")
    return report


def _restore_locked(adb, path, journal):
    """One engine for explicit restore and automatic recovery; caller holds the lock."""
    report = recovery_report(adb)
    if journal["restored"]:
        return {"status": "already_restored", "device_writes": False, "backup": str(path)}
    original = journal["original"]
    owns_launcher = (journal["schema"] == 2 and original["launcher"]["build"] == "factory" and
                     touched(journal, "install_launcher"))
    homes = (PROFILE["launcher"]["home"], PROFILE["launcher"]["package"] + "/com.chinatsp.launcher.MainAct")
    if report["launcher"]["home"] not in homes and not owns_launcher:
        raise SetupError("Unexpected HOME and no owned launcher update to recover; refusing writes.")
    results, errors = {}, {}

    def step(name, action):
        try:
            # Identity and transport are checked again before each independent recovery step.
            recovery_report(adb)
            results[name] = operation(path, journal, name, action)
            return True
        except (SetupError, OSError, ValueError) as exc:
            errors[name] = str(exc)
            journal["recovery_errors"] = errors.copy()
            write_json(path, journal)
            return False

    home_ok = True
    if owns_launcher:
        home_ok = step("restore_launcher", lambda: restore_launcher(adb))
    if home_ok:
        home_ok = step("verify_restored_home", lambda: healthy_launch(adb, PROFILE["launcher"]["home"]))

    if touched(journal, "fullscreen"):
        def restore_layout():
            current = recovery_report(adb)
            if not current["root_available"] or not current["prefs_readable"]:
                raise SetupError("Fullscreen recovery needs existing root and readable factory preferences.")
            wanted = original["fullscreen_value"]
            if current["fullscreen_value"] == wanted or (wanted is None and current["fullscreen_value"] == -1):
                return {"unchanged": True}
            baseline = health.logs(adb)
            broadcast_layout(adb, -1 if wanted is None else wanted)
            refresh(adb)
            return healthy_systemui(adb, baseline)
        step("restore_fullscreen", restore_layout)

    carauto_ok = True
    if touched(journal, "disable_carauto"):
        def restore_carauto():
            current = recovery_report(adb)
            if not current["carauto"]["installed"]:
                raise SetupError("CarAuto is missing; this restore cannot recreate factory packages.")
            wanted = original["carauto"]["enabled"]
            if current["carauto"]["enabled"] == wanted:
                return {"unchanged": True}
            if not current["root_available"]:
                raise SetupError("CarAuto recovery needs the firmware's existing root access.")
            baseline = health.logs(adb)
            set_enabled(adb, wanted)
            return healthy_systemui(adb, baseline)
        carauto_ok = step("restore_carauto", restore_carauto)

    if not original["receiver"]["installed"] and touched(journal, "install_receiver"):
        def remove_receiver():
            if not home_ok or not carauto_ok:
                raise SetupError("Receiver retained until Home and CarAuto recovery verify successfully.")
            current = receiver_state(adb)
            if not current["installed"]:
                return {"unchanged": True}
            if not current["verified"]:
                raise SetupError("Receiver identity changed; refusing to remove an unknown APK.")
            if not recovery_report(adb)["root_available"]:
                raise SetupError("Receiver removal needs the firmware's existing root access.")
            output = adb.shell("pm", "uninstall", "--user", "0", RECEIVER, root=True)
            if output != "Success" or package(adb, RECEIVER)["installed"]:
                raise SetupError("Could not remove the receiver installed by this setup.")
            return {"installed": False}
        step("remove_receiver", remove_receiver)
    journal["recovery_errors"] = errors
    journal["phase"] = "recovery_required" if errors else "restored"
    journal["restored"] = not errors
    if not errors:
        journal["restored_at"] = now()
    write_json(path, journal)
    result = {"status": journal["phase"], "backup": str(path), "steps": results, "errors": errors,
              "component_issues": report.get("component_issues", []),
              "next_action": "reconnect_usb_and_restore" if errors else "restore_complete",
              "note": "Only journal-owned changes are reversed. An absent fullscreen key uses -1 "
                      "if it was changed. Preexisting apps and their settings are retained."}
    if errors:
        raise SetupError("Recovery is incomplete; preserve the journal and rerun restore after resolving "
                         "the reported problems.", recovery=result)
    return result


def reboot_check(adb):
    """Reboot Android once, keep USB supervision, then verify the configured state/UI."""
    previous = adb.shell("cat", "/proc/sys/kernel/random/boot_id")
    boot_pattern = r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}"
    if not re.fullmatch(boot_pattern, previous):
        raise SetupError("Cannot establish Android boot identity; reboot verification refused.")
    adb.run("reboot")
    deadline = time.monotonic() + 120
    def probe_timeout():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SetupError("Reboot observation deadline reached.")
        return min(3, remaining)

    while time.monotonic() < deadline:
        time.sleep(min(2, deadline - time.monotonic()))
        try:
            adb.select_usb(timeout=probe_timeout())
            current_boot = adb.shell("cat", "/proc/sys/kernel/random/boot_id", timeout=probe_timeout())
            changed = bool(re.fullmatch(boot_pattern, current_boot)) and current_boot != previous
            if changed and adb.shell("getprop", "sys.boot_completed", timeout=probe_timeout()) == "1":
                break
        except SetupError:
            continue
    else:
        raise SetupError("Android did not return over USB within 120 seconds. Reconnect in Device mode "
                         "and run restore. USB recovery requires responsive Android/ADB.")
    after = inspect(adb)
    require_compatible(after)
    if not configured(after) or after["usb_mode"] != "1":
        raise SetupError("Configured state did not persist after the Android reboot.")
    home = healthy_launch(adb, PROFILE["launcher"]["home"])
    receiver = healthy_launch(adb, MAIN_ACTIVITY)
    return {"android_reboot_verified": True, "home": home, "receiver": receiver,
            "ignition_cycle_tested": False}


def configured(report):
    return (report["compatible"] and report["carauto"]["enabled"] == 3 and
            report["fullscreen_value"] == 0 and report["receiver"]["installed"] and
            report["launcher"]["build"] == "openhu")


def setup(adb, state_dir, report, supplied_apk=None, verify_reboot=False):
    require_compatible(report)
    if report["usb_mode"] != "1":
        raise SetupError("Select USB Device mode for the laptop before setup.")
    path = backup_path(adb, state_dir)
    with exclusive(state_dir):
        journal = load_backup(path, adb) if path.exists() else None
        if journal and journal["restored"]:
            raise SetupError("This backup has already been restored. Keep it, and choose a new "
                             "--state-dir for a new setup cycle.")
        if journal and journal["phase"] not in ("backed_up", "configured", "waiting_for_permissions"):
            raise SetupError("An earlier operation was interrupted. Run restore before starting again.")
        already = bool(journal and journal["phase"] == "configured")
        if already:
            if configured(report):
                if journal["schema"] == 1:
                    journal["schema"] = 2
                    journal["original"]["launcher"] = report["launcher"]
                    journal["launcher_adopted_as_preexisting_at"] = now()
                    write_json(path, journal)
                if not verify_reboot or journal.get("android_reboot_verified"):
                    return setup_result(path, journal, report, already=True)
            elif journal["schema"] != 1 or report["launcher"]["build"] != "factory" or not (
                    report["carauto"]["enabled"] == 3 and report["fullscreen_value"] == 0 and
                    report["receiver"]["installed"]):
                raise SetupError("Device settings changed after setup. Run restore before reapplying.")
            else:
                already = False  # Extend a completed v0.1 AA-only cycle.
        # Verify all artifacts before any device writes. A permission pause reuses this same baseline.
        apk = None if report["receiver"]["installed"] else obtain_apk(state_dir, supplied_apk)
        launcher_apk = (prepare_launcher(adb, path.parent)
                        if report["launcher"]["build"] == "factory" else None)
        if journal is None:
            journal = create_backup(path, adb, report)
        elif journal["schema"] == 1:
            journal["schema"] = 2
            journal["original"]["launcher"] = report["launcher"]
            journal["launcher_upgrade_at"] = now()
            write_json(path, journal)
        def stage(name, action):
            # Downloads/owner prompts can take time. Never rely on an old setup report.
            current = inspect(adb)
            require_compatible(current)
            if current["usb_mode"] != "1":
                raise SetupError("Keep USB in Device mode until setup and its reboot check finish.")
            return operation(path, journal, name, action)

        try:
            if not already:
                stage("verify_home_before",
                          lambda: healthy_launch(adb, PROFILE["launcher"]["home"]))
                if apk is not None:
                    stage("install_receiver", lambda: install(adb, apk))
                stage("verify_receiver", lambda: healthy_launch(adb, MAIN_ACTIVITY))
                if report["carauto"]["enabled"] != 3:
                    def disable_carauto():
                        baseline = health.logs(adb)
                        set_enabled(adb, 3)
                        return healthy_systemui(adb, baseline)
                    stage("disable_carauto", disable_carauto)
                if report["fullscreen_value"] != 0:
                    def fullscreen():
                        baseline = health.logs(adb)
                        broadcast_layout(adb, 0)
                        refresh(adb)
                        return healthy_systemui(adb, baseline)
                    stage("fullscreen", fullscreen)
                if launcher_apk is not None:
                    def update_launcher():
                        baseline = health.logs(adb)
                        install_launcher(adb, launcher_apk)
                        return healthy_launch(adb, PROFILE["launcher"]["home"], baseline)
                    stage("install_launcher", update_launcher)
                stage("open_receiver", lambda: healthy_launch(adb, MAIN_ACTIVITY))
            after = inspect(adb)
            require_compatible(after)
            if not configured(after):
                raise SetupError("Final configured state did not pass read-back.")
            if verify_reboot and not journal.get("android_reboot_verified"):
                stage("verify_android_reboot", lambda: reboot_check(adb))
                journal["android_reboot_verified"] = True
            journal["phase"] = "configured"
            journal["configured_at"] = now()
            journal["launcher_after"] = after["launcher"]
            write_json(path, journal)
        except NeedsPermissions as exc:
            journal["phase"] = "waiting_for_permissions"
            journal["next_action"] = "accept_car_permission_then_rerun_setup"
            write_json(path, journal)
            return {"status": "waiting_for_permissions", "backup": str(path), "projection_tested": False,
                    "next_action": journal["next_action"], "message": str(exc)}
        except (Exception, KeyboardInterrupt) as exc:
            journal["setup_error"] = str(exc) or type(exc).__name__
            journal["failed_stage"] = journal["phase"]
            journal["phase"] = "recovery_required"
            write_json(path, journal)
            try:
                recovery = _restore_locked(adb, path, journal)
            except (SetupError, OSError, ValueError) as recovery_error:
                recovery = getattr(recovery_error, "details", {}).get("recovery", {
                    "status": "recovery_required", "error": str(recovery_error),
                    "next_action": "reconnect_usb_device_mode_then_restore", "backup": str(path)})
                journal["automatic_recovery"] = recovery
                write_json(path, journal)
            raise SetupError("Setup failed: " + (str(exc) or type(exc).__name__),
                             failed_stage=journal.get("failed_stage"), recovery=recovery) from exc
    return setup_result(path, journal, after)


def setup_result(path, journal, report, already=False):
    rebooted = bool(journal.get("android_reboot_verified"))
    return {"status": "already_configured" if already else "configured", "backup": str(path),
            "device_writes": not already, "projection_tested": False,
            "android_reboot_verified": rebooted, "launcher": report["launcher"],
            "next_action": "phone_handoff" if rebooted else "rerun_setup_with_reboot_check",
            "next": (["Complete onboarding/visible permissions on the car; choose USB and right-hand drive.",
                      "Disconnect the laptop, select Host模式, and connect the phone to the recording USB port.",
                      "Accept phone/USB prompts; check real Maps, sound, touch, large AA card, Home and native controls."]
                     if rebooted else ["Keep the laptop connected in Device mode. Run setup --reboot-check."]),
            "note": "Microphone recognition remains unresolved; wireless and cold ignition cycles are untested."}


def restore(adb, state_dir, report=None):
    # A fresh, component-aware recovery inspection is independent of a failed setup check.
    adb.select_usb()
    path = backup_path(adb, state_dir)
    with exclusive(state_dir):
        journal = load_backup(path, adb)
        return _restore_locked(adb, path, journal)


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
    result.add_argument("--reboot-check", action="store_true",
                        help="With setup, verify a normal Android reboot while USB stays connected")
    result.add_argument("--json", action="store_true", help="Emit one JSON object for agent/tool use")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    details = {}
    try:
        if not 1 <= args.adb_port <= 65535:
            raise SetupError("ADB port must be between 1 and 65535.")
        if args.apk and args.command != "setup":
            raise SetupError("--apk is only used by setup.")
        if args.reboot_check and args.command != "setup":
            raise SetupError("--reboot-check is only used by setup.")
        adb = ADB(args.adb, args.adb_port, args.serial)
        state_dir = args.state_dir.expanduser().resolve()
        report = inspect(adb, recovery=args.command in ("restore", "status"))
        if args.command in ("check", "status"):
            result = public_report(report)
            result["device_writes"] = False
            result["projection_tested"] = False
            if adb.serial:
                path = backup_path(adb, state_dir)
                result["backup_exists"] = path.exists()
                if path.exists():
                    journal = load_backup(path, adb)
                    result["backup_phase"] = journal["phase"]
                    result["failed_stage"] = journal.get("failed_stage")
                    result["recovery_errors"] = journal.get("recovery_errors", {})
                    result["android_reboot_verified"] = bool(journal.get("android_reboot_verified"))
                    result["next_action"] = ("restore" if journal["phase"] not in
                        {"configured", "restored", "waiting_for_permissions"} else
                        {"configured": "phone_handoff" if journal.get("android_reboot_verified") else
                         "rerun_setup_with_reboot_check", "restored": "restore_complete",
                         "waiting_for_permissions": "accept_car_permission_then_rerun_setup"}[journal["phase"]])
                if not report["compatible"]:
                    result["next_action"] = "diagnose_identity_mismatch_no_writes"
                elif args.command == "status" and report.get("component_issues"):
                    result["next_action"] = "inspect_component_issues_and_restore_if_needed"
            code = 0 if report["compatible"] else 2
        elif args.command == "setup":
            result = setup(adb, state_dir, report, args.apk, args.reboot_check)
            code = 3 if result["status"] == "waiting_for_permissions" else 0
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
        details = getattr(exc, "details", {})
    if args.json:
        print(json.dumps({"ok": False, "error": message, **details}))
    else:
        print("Error: " + message, file=sys.stderr)
        if details:
            print(json.dumps(details, indent=2), file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
