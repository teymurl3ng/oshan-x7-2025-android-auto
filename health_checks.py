"""Bounded, read-only Android 9 health observations used between setup steps.

These checks establish process/UI health, not working audio or projection.
No log buffers are cleared and no permissions are granted by this module.
"""
from collections import Counter
import re
from time import monotonic, sleep

SYSTEMUI = "com.android.systemui"


class HealthError(Exception):
    pass


class PermissionsPending(HealthError):
    pass


def read(adb, *args, deadline=None, **kwargs):
    remaining = 5 if deadline is None else min(5, deadline - monotonic())
    if remaining <= 0:
        raise HealthError("Android health observation timed out.")
    return adb.shell(*args, timeout=remaining, **kwargs)


def logs(adb, deadline=None):
    return read(adb, "logcat", "-d", "-b", "crash", "-b", "events", "-t", "200", "-v", "threadtime",
                deadline=deadline)


def new_lines(before, after):
    """Ignore pre-existing events; tolerate a rolling log buffer without clearing it."""
    def lines(value):
        return [line for line in value.splitlines() if not line.startswith("--------- beginning")]
    old, current = lines(before), lines(after)
    for overlap in range(min(len(old), len(current)), 0, -1):
        if old[-overlap:] == current[:overlap]:
            return current[overlap:]
    # Android can group buffers or rotate them independently. Without an overlap,
    # remove only the exact historical occurrences (timestamps included), rather
    # than attributing an old crash from another buffer to this operation.
    historical = Counter(old)
    fresh = []
    for line in current:
        if historical[line]:
            historical[line] -= 1
        else:
            fresh.append(line)
    return fresh


def resumed_activity(adb, deadline=None):
    raw = read(adb, "dumpsys", "activity", "activities", deadline=deadline)
    match = re.search(r"(?:mResumedActivity|topResumedActivity|ResumedActivity):?\s*"
                      r"ActivityRecord\{[^\n]*?\bu0\s+([\w.$]+/[\w.$]+)", raw)
    return match[1] if match else None


def pids(adb, name, deadline=None):
    raw = read(adb, "pidof", name, allow_failure=True, deadline=deadline)
    return tuple(sorted(raw.split())) if re.fullmatch(r"\d+(?:\s+\d+)*", raw) else ()


def observe(adb, name, baseline=None, foreground=False, timeout=12, samples=3, expected_activity=None):
    baseline = logs(adb) if baseline is None else baseline
    deadline = monotonic() + timeout
    previous, consecutive = None, 0
    targets = {name, SYSTEMUI}
    while monotonic() < deadline:
        fresh = "\n".join(new_lines(baseline, logs(adb, deadline)))
        for target in targets:
            escaped = re.escape(target)
            if (re.search(r"\bProcess:\s*" + escaped + r"(?=[:,\s]|$)", fresh) or
                    re.search(r"\bANR in\s+" + escaped + r"(?=[:,\s]|$)", fresh) or
                    re.search(r">>>\s*" + escaped + r"\s*<<<", fresh) or
                    any(re.search(r"am_(?:anr|crash)", line) and re.search(r"[,\s]" + escaped + r"[,\s\]]", line)
                        for line in fresh.splitlines())):
                raise HealthError(f"Fresh crash/ANR recorded for {target}. Keep USB connected.")
        current = (pids(adb, name, deadline), pids(adb, SYSTEMUI, deadline))
        activity = resumed_activity(adb, deadline) if foreground else None
        if foreground and activity and re.fullmatch(
                r"(?:com\.android\.packageinstaller|com\.google\.android\.packageinstaller|"
                r"com\.android\.permissioncontroller|com\.google\.android\.permissioncontroller)"
                r"/.*GrantPermissionsActivity", activity):
            raise PermissionsPending("Accept the visible Open Headunit permission prompt on the car, "
                                     "then rerun the same setup command with the laptop connected.")
        foreground_ok = not foreground or (activity and activity.split("/")[0] == name)
        if expected_activity:
            def expanded(component):
                package, activity_name = component.split("/", 1)
                return package + "/" + (package + activity_name if activity_name.startswith(".") else activity_name)
            foreground_ok = bool(activity and expanded(activity) == expanded(expected_activity))
        if all(current) and foreground_ok:
            if previous is not None and current != previous:
                raise HealthError(f"{name} or SystemUI restarted during the health check.")
            previous = current
            consecutive += 1
            if consecutive >= samples:
                return {"package": name, "stable_samples": samples,
                        "foreground": activity, "fresh_crash_or_anr": False}
        else:
            if previous is not None:
                raise HealthError(f"{name} or SystemUI disappeared or lost the foreground.")
            consecutive = 0
        sleep(1)
    raise HealthError(f"{name} did not become healthy within {timeout} seconds.")


def launch(adb, component, baseline=None, exact_activity=False):
    baseline = logs(adb) if baseline is None else baseline
    result = adb.shell("am", "start", "-W", "--user", "0", "-n", component, timeout=20)
    if re.search(r"(?:^|\n)\s*(?:Error|Exception|SecurityException)|Status:\s*(?:timeout|failed)",
                 result, re.I):
        raise HealthError("Android could not open " + component + ": " + result[:500])
    return observe(adb, component.split("/")[0], baseline, foreground=True,
                   expected_activity=component if exact_activity else None)
