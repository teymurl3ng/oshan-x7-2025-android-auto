"""Journaled Android 9 grants and CarLink's own USB-dialog automation.

Called automatically by setup before CarLink's first launch. Never enables
network ADB or changes the system USB role, and preserves other services.
"""
import json
import re
import time

PACKAGE = "com.carlink.app"
SERVICE = PACKAGE + "/com.shilapi.xcertplay.UsbAutoConfirmService"
RUNTIME = tuple("android.permission." + name for name in (
    "RECORD_AUDIO", "ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION",
    "READ_PHONE_STATE", "READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE"))
APPOPS = ("SYSTEM_ALERT_WINDOW", "WRITE_SETTINGS", "GET_USAGE_STATS", "ACTIVATE_VPN")
MODES = {"allow", "ignore", "deny", "default", "foreground"}
CHANGES = {"grant:" + p for p in RUNTIME} | {"appop:" + op for op in APPOPS} | {"battery", "usb_auto_confirm"}
OPERATIONS = CHANGES | {"restore:" + name for name in CHANGES} | {"android_reboot"}


def path(core, adb, state_dir):
    return core.backup_path(adb, state_dir).with_name("carlink-permissions.json")


def services(core, value):
    if not isinstance(value, str):
        raise core.SetupError("Invalid accessibility-service baseline; preserve its journal.")
    if value in ("null", ""):
        return []
    result = value.split(":")
    if any(not re.fullmatch(r"[A-Za-z0-9_.$]+/[A-Za-z0-9_.$]+", x) for x in result):
        raise core.SetupError("Cannot safely preserve the current accessibility-service list.")
    return result


def setting(adb, key):
    return adb.shell("settings", "--user", "0", "get", "secure", key, root=True)


def put_setting(adb, key, value):
    if value == "null":
        adb.shell("settings", "--user", "0", "delete", "secure", key, root=True)
    else:
        adb.shell("settings", "--user", "0", "put", "secure", key, value, root=True)


def service_bound(adb):
    # This firmware's accessibility dump prints labels/capabilities, no IDs.
    # ActivityManager identifies the exact live service and its system binding.
    raw = adb.shell("dumpsys", "activity", "services", PACKAGE)
    for block in re.split(r"(?m)^\s*\* ServiceRecord", raw)[1:]:
        if not re.match(r"\{[^\n]*\bu0 " + re.escape(SERVICE) + r"\}\n", block):
            continue
        return bool("permission=android.permission.BIND_ACCESSIBILITY_SERVICE" in block and
                    re.search(r"app=ProcessRecord\{[^\n]*\b\d+:com\.carlink\.app/u0a\d+\}", block) and
                    "hasBound=true" in block and
                    re.search(r"Client AppBindRecord\{[^\n]*\bsystem/1000\}", block))
    return False


def snapshot(core, adb):
    if core.RECEIVER != PACKAGE or not core.receiver_state(adb).get("verified"):
        raise core.SetupError("Automatic permissions require the exact official CarLink APK.")
    raw = adb.shell("dumpsys", "package", PACKAGE)
    requested = raw.split("requested permissions:", 1)
    if len(requested) != 2 or any(p not in requested[1].split("install permissions:", 1)[0] for p in RUNTIME):
        raise core.SetupError("CarLink's declared Android 9 permissions differ from the tested release.")
    grants = dict(re.findall(r"(android\.permission\.[A-Z_]+): granted=(true|false)", raw))
    ops = {}
    for op in APPOPS:
        output = adb.shell("appops", "get", "--user", "0", PACKAGE, op, root=True)
        explicit = re.search(r"(?:^|\n)" + op + r":\s*(\w+)", output)
        default = re.search(r"Default mode:\s*(\w+)", output)
        mode = explicit[1] if explicit else default[1] if default else None
        if mode not in MODES:
            raise core.SetupError("Cannot read CarLink app-op " + op + ".")
        ops[op] = mode
    enabled_services = setting(adb, "enabled_accessibility_services")
    listed = services(core, enabled_services)
    enabled = setting(adb, "accessibility_enabled")
    if enabled not in ("0", "1", "null"):
        raise core.SetupError("Cannot establish the accessibility enabled state.")
    battery = adb.shell("dumpsys", "deviceidle", "whitelist", "=" + PACKAGE, root=True)
    if battery not in ("true", "false"):
        raise core.SetupError("Cannot read CarLink's battery exemption.")
    bound = SERVICE in listed and enabled == "1" and service_bound(adb)
    result = {"runtime": {p: grants.get(p) == "true" for p in RUNTIME}, "appops": ops,
              "accessibility_services": enabled_services, "accessibility_enabled": enabled,
              "battery_whitelisted": battery == "true", "usb_service_bound": bound}
    result["ready"] = (all(result["runtime"].values()) and all(m == "allow" for m in ops.values()) and
                       SERVICE in listed and enabled == "1" and bound and result["battery_whitelisted"])
    return result


def load(core, adb, state_dir):
    record = path(core, adb, state_dir)
    value = json.loads(record.read_text(encoding="utf-8"))
    baseline = value.get("original", {}) if isinstance(value, dict) else {}
    if not isinstance(baseline, dict):
        raise core.SetupError("Invalid CarLink permission baseline; preserve its journal.")
    if (not isinstance(value, dict) or value.get("schema") != 1 or value.get("serial") != adb.serial or
            value.get("profile") != core.PROFILE["id"] or
            value.get("apk_sha256") != core.PROFILE["receiver"]["sha256"] or
            type(value.get("restored")) is not bool or not isinstance(value.get("operations"), list) or
            not isinstance(value.get("phase"), str) or
            value["phase"] not in OPERATIONS | {"backed_up", "configured", "restored"} or
            type(value.get("android_reboot_verified", False)) is not bool or
            any(not isinstance(x, dict) or not isinstance(x.get("name"), str) or x["name"] not in OPERATIONS or
                type(x.get("complete")) is not bool for x in value["operations"]) or
            not isinstance(baseline.get("runtime"), dict) or set(baseline["runtime"]) != set(RUNTIME) or
            any(type(x) is not bool for x in baseline["runtime"].values()) or
            not isinstance(baseline.get("appops"), dict) or set(baseline["appops"]) != set(APPOPS) or
            any(x not in MODES for x in baseline["appops"].values()) or
            baseline.get("accessibility_enabled") not in ("0", "1", "null") or
            type(baseline.get("battery_whitelisted")) is not bool):
        raise core.SetupError("CarLink permission journal identity or baseline is invalid; preserve it.")
    services(core, baseline.get("accessibility_services"))
    return value


def preflight(core, adb):
    report = core.inspect(adb, recovery=True)
    if not report["recovery_eligible"]:
        raise core.SetupError("Permission setup refused: " + "; ".join(report["mismatches"]))
    if not report["root_available"] or not report["boot_completed"]:
        raise core.SetupError("Permission setup needs the firmware's existing root and completed boot.")
    if not report["receiver"].get("installed") or not report["receiver"].get("verified"):
        raise core.SetupError("Unknown or absent CarLink APK; its permissions will not be changed.")


def apply(core, adb, state_dir):
    """Caller holds the shared setup lock; original snapshot precedes every write."""
    preflight(core, adb)
    record = path(core, adb, state_dir)
    if record.exists():
        journal = load(core, adb, state_dir)
        if journal["restored"]:
            raise core.SetupError("This permission cycle was restored; retain it and use a new setup cycle.")
    else:
        journal = {"schema": 1, "profile": core.PROFILE["id"], "serial": adb.serial,
                   "apk_sha256": core.PROFILE["receiver"]["sha256"], "created_at": core.now(),
                   "original": snapshot(core, adb), "operations": [], "restored": False, "phase": "backed_up"}
        core.write_json(record, journal)
    current = snapshot(core, adb)
    def step(name, action):
        preflight(core, adb)
        return core.operation(record, journal, name, action)
    for permission in RUNTIME:
        if not current["runtime"][permission]:
            step("grant:" + permission,
                 lambda p=permission: adb.shell("pm", "grant", "--user", "0", PACKAGE, p, root=True))
    for op in APPOPS:
        if current["appops"][op] != "allow":
            step("appop:" + op,
                 lambda name=op: adb.shell("appops", "set", "--user", "0", PACKAGE, name, "allow", root=True))
    if not current["battery_whitelisted"]:
        step("battery", lambda: adb.shell("dumpsys", "deviceidle", "whitelist", "+" + PACKAGE, root=True))
    def enable_usb():
        # Merge immediately before writing, preserving every unrelated service.
        raw = setting(adb, "enabled_accessibility_services")
        listed = services(core, raw)
        if SERVICE not in listed:
            listed.append(SERVICE)
            put_setting(adb, "enabled_accessibility_services", ":".join(listed))
        put_setting(adb, "accessibility_enabled", "1")
    if SERVICE not in services(core, current["accessibility_services"]) or current["accessibility_enabled"] != "1":
        step("usb_auto_confirm", enable_usb)
    deadline = time.monotonic() + 12
    while True:
        current = snapshot(core, adb)
        if current["ready"] or time.monotonic() >= deadline:
            break
        time.sleep(.5)
    if not current["ready"]:
        raise core.SetupError("Automatic CarLink grants did not verify, including its USB auto-confirm service.")
    journal["phase"] = "configured"
    journal["verified_at"] = core.now()
    core.write_json(record, journal)
    return {"ready": True, "runtime_permissions": list(RUNTIME), "appops": list(APPOPS),
            "usb_auto_confirm_bound": True, "usb_phone_tested": False}


def restore(core, adb, state_dir):
    record = path(core, adb, state_dir)
    if not record.exists():
        return {"unchanged": True}
    journal = load(core, adb, state_dir)
    if journal["restored"]:
        return {"unchanged": True}
    preflight(core, adb)
    original = journal["original"]
    owned = {x["name"] for x in journal["operations"]}
    def step(name, action):
        preflight(core, adb)
        return core.operation(record, journal, "restore:" + name, action)
    if "usb_auto_confirm" in owned:
        def undo_usb():
            current = services(core, setting(adb, "enabled_accessibility_services"))
            before = services(core, original["accessibility_services"])
            if SERVICE not in before:
                current = [x for x in current if x != SERVICE]
                value = original["accessibility_services"] if current == before else ":".join(current)
                put_setting(adb, "enabled_accessibility_services", value)
            if not current or current == before:
                put_setting(adb, "accessibility_enabled", original["accessibility_enabled"])
        step("usb_auto_confirm", undo_usb)
    current = snapshot(core, adb)
    for op in APPOPS:
        if "appop:" + op in owned and current["appops"][op] != original["appops"][op]:
            step("appop:" + op, lambda name=op: adb.shell("appops", "set", "--user", "0", PACKAGE,
                                                        name, original["appops"][name], root=True))
    if "battery" in owned and not original["battery_whitelisted"] and current["battery_whitelisted"]:
        step("battery", lambda: adb.shell("dumpsys", "deviceidle", "whitelist", "-" + PACKAGE, root=True))
    for permission in RUNTIME:
        if "grant:" + permission in owned and not original["runtime"][permission] and current["runtime"][permission]:
            step("grant:" + permission, lambda p=permission: adb.shell("pm", "revoke", "--user", "0", PACKAGE, p, root=True))
    after = snapshot(core, adb)
    if any(after["runtime"][p] != original["runtime"][p] for p in RUNTIME if "grant:" + p in owned):
        raise core.SetupError("Runtime permission restore did not verify.")
    if any(after["appops"][op] != original["appops"][op] for op in APPOPS if "appop:" + op in owned):
        raise core.SetupError("Special-access restore did not verify.")
    if "battery" in owned and after["battery_whitelisted"] != original["battery_whitelisted"]:
        raise core.SetupError("Battery exemption restore did not verify.")
    if ("usb_auto_confirm" in owned and SERVICE not in services(core, original["accessibility_services"]) and
            SERVICE in services(core, after["accessibility_services"])):
        raise core.SetupError("USB auto-confirm removal did not verify.")
    journal["phase"], journal["restored"] = "restored", True
    core.write_json(record, journal)
    return {"restored": True}
