"""Bounded reference screenshots while the shared USB port is used by a phone.

Only diagnostic files under an owned /data/local/tmp directory are written.
No package, launcher, USB role, root, or network settings are changed.
"""
from pathlib import Path
import hashlib
import json
import re
import secrets
import struct


def script(remote):
    if not re.fullmatch(r"/data/local/tmp/oshan-carlink-reference-[0-9a-f]{16}", remote):
        raise ValueError("Unexpected reference capture directory")
    return ("#!/system/bin/sh\nset -eu\n"
            "for frame in 1 2 3 4 5 6; do\n"
            "  sleep 15\n"
            f'  screencap -p "{remote}/frame-$frame.png"\n'
            "done\n"
            f"echo complete > {remote}/complete\n")


def png(path):
    data = Path(path).read_bytes()
    if (not 32 <= len(data) <= 16 * 1024 * 1024 or
            data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR" or
            struct.unpack(">II", data[16:24]) != (1920, 720) or
            data[-12:] != b"\x00\x00\x00\x00IEND\xaeB`\x82"):
        raise ValueError("Reference frame is not a complete 1920 x 720 PNG")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def run(trial, command):
    c, adb = trial.c, trial.adb
    journal = trial.load()
    if journal["restored"] or journal["phase"] != "trial_ready":
        raise c.SetupError("Reference capture requires the original ready CarLink journal.")
    _, state = trial.inspect(journal)
    trial.require_owned(state)
    if command == "carlink-reference-pages":
        folder = trial.path.parent / "reference-pages"
        folder.mkdir(mode=0o700, exist_ok=True)
        remote = "/data/local/tmp/oshan-carlink-reference-" + secrets.token_hex(8)
        frames = []
        adb.shell("mkdir", "-m", "700", remote)
        try:
            trial.launch(c.PROFILE["launcher"]["home"])
            # The qualified 1920x720 factory launcher uses horizontal pages.
            # Start on its large-card page, then move to the app-menu page.
            adb.shell("input", "swipe", "300", "640", "1700", "640", "400")
            for name in ("home", "menu"):
                if name == "menu":
                    adb.shell("input", "swipe", "1700", "640", "300", "640", "400")
                c.time.sleep(1)
                adb.shell("screencap", "-p", remote + "/" + name + ".png")
                target = folder / (name + ".png")
                adb.run("pull", remote + "/" + target.name, str(target))
                frames.append({"file": target.name, **png(target)})
                adb.shell("rm", remote + "/" + target.name)
            c.write_json(folder / "capture.json", {"captured_at": c.now(), "frames": frames})
        finally:
            trial.launch(c.PROFILE["launcher"]["home"])
        adb.shell("rmdir", remote)
        return {"status": "reference_pages_captured", "folder": str(folder),
                "next_action": "inspect_private_images_before_publishing"}
    folder = trial.path.parent / "reference-capture"
    record = folder / "capture.json"
    if command == "carlink-reference-start":
        if record.exists():
            raise c.SetupError("Reference capture already exists; collect it instead of starting another timer.")
        folder.mkdir(mode=0o700)
        remote = "/data/local/tmp/oshan-carlink-reference-" + secrets.token_hex(8)
        payload = script(remote)
        local_script = folder / "capture.sh"
        local_script.write_text(payload, encoding="utf-8")
        operation = {"schema": 1, "serial": adb.serial, "remote": remote,
                     "script_sha256": c.digest(local_script), "started_at": c.now(),
                     "frames": 6, "interval_seconds": 15, "collected": False}
        c.write_json(record, operation)
        adb.shell("mkdir", "-m", "700", remote)
        adb.run("push", str(local_script), remote + "/capture.sh")
        if c.remote_hash(adb, remote + "/capture.sh") != operation["script_sha256"]:
            raise c.SetupError("Reference capture script read-back failed; timer was not started.")
        pid = adb.shell("sh", "-c", "nohup sh " + remote + "/capture.sh </dev/null >" +
                        remote + "/capture.log 2>&1 & echo $!")
        if not re.fullmatch(r"[1-9][0-9]*", pid):
            raise c.SetupError("Reference capture did not return a process ID; preserve its record.")
        operation["pid"] = int(pid)
        c.write_json(record, operation)
        return {"status": "reference_capture_started", "duration_seconds": 90,
                "frames": 6, "next_action": "disconnect_laptop_select_host_show_phone_then_return_device"}
    try:
        operation = json.loads(record.read_text(encoding="utf-8"))
        remote = operation["remote"]
        expected = hashlib.sha256(script(remote).encode()).hexdigest()
        if (operation["schema"] != 1 or operation["serial"] != adb.serial or
                operation["script_sha256"] != expected or operation["frames"] != 6):
            raise ValueError("Capture record identity changed")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise c.SetupError("Cannot verify the original reference capture record.") from exc
    if operation["collected"]:
        return {"status": "reference_already_collected", "folder": str(folder)}
    if adb.shell("cat", remote + "/complete", allow_failure=True) != "complete":
        return {"status": "reference_capture_pending", "next_action": "wait_for_90_second_timer"}
    if c.remote_hash(adb, remote + "/capture.sh") != expected:
        raise c.SetupError("Remote capture script changed; no files are collected or removed.")
    frames = []
    for index in range(1, 7):
        target = folder / ("frame-" + str(index) + ".png")
        adb.run("pull", remote + "/" + target.name, str(target))
        frames.append({"file": target.name, **png(target)})
    operation["collected"], operation["collected_at"], operation["frame_hashes"] = True, c.now(), frames
    c.write_json(record, operation)
    # Delete only the exact files created by this finished, verified capture.
    for name in ["frame-" + str(i) + ".png" for i in range(1, 7)] + ["capture.sh", "capture.log", "complete"]:
        adb.shell("rm", remote + "/" + name)
    adb.shell("rmdir", remote)
    return {"status": "reference_collected", "folder": str(folder), "frames": frames,
            "next_action": "review_private_frames_before_publishing"}
