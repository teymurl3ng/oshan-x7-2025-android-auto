"""Public CarLink workflow; old journals retain their original recovery engine.

The CLI runs one command per process. Configuration is scoped and restored so
the shared guarded setup/recovery engine also remains usable in offline tests.
"""
from contextlib import contextmanager
import json


@contextmanager
def configuration(core):
    names = ("PROFILE", "RECEIVER", "MAIN_ACTIVITY")
    original = {name: getattr(core, name) for name in names}
    profile = json.loads((core.ROOT / "profiles/f202-carlink.json").read_text(encoding="utf-8"))
    core.PROFILE = profile
    core.RECEIVER = profile["receiver"]["package"]
    core.MAIN_ACTIVITY = profile["receiver"]["activity"]
    try:
        yield
    finally:
        for name, value in original.items():
            setattr(core, name, value)


def run(core, adb, state_dir, args):
    # Establish a USB identity before locating its private journal. No car writes.
    adb.select_usb()
    import carlink_trial
    trial_path = carlink_trial.journal_path(core, adb, state_dir)
    if trial_path.exists():
        trial = carlink_trial.Trial(core, adb, state_dir)
        journal = trial.load()
        if not journal["restored"]:
            if args.command == "setup" and journal.get("primary_receiver") == "carlink":
                if journal["phase"] != "trial_ready" or trial.pin != carlink_trial.BASE_PIN:
                    raise core.SetupError("The existing CarLink setup needs recovery before setup can continue.")
                with core.exclusive(state_dir):
                    trial.require_owned(trial.inspect(journal)[1])
                    with configuration(core):
                        import carlink_permissions
                        permission_record = carlink_permissions.path(core, adb, state_dir)
                        if permission_record.exists():
                            previous = carlink_permissions.load(core, adb, state_dir)
                            current = carlink_permissions.snapshot(core, adb)
                            if (previous["phase"] == "configured" and current["ready"] and
                                    (not args.reboot_check or previous.get("android_reboot_verified"))):
                                return {"status": "already_configured", "device_writes": False,
                                        "carlink_permissions": current, "projection_tested": False,
                                        "android_reboot_verified": bool(previous.get("android_reboot_verified")),
                                        "next_action": "phone_handoff"}, 0
                        result = carlink_permissions.apply(core, adb, state_dir)
                        core.healthy_launch(adb, core.PROFILE["launcher"]["home"])
                        core.healthy_launch(adb, core.MAIN_ACTIVITY)
                        if args.reboot_check:
                            permission_journal = carlink_permissions.load(core, adb, state_dir)
                            if not permission_journal.get("android_reboot_verified"):
                                core.operation(carlink_permissions.path(core, adb, state_dir), permission_journal,
                                               "android_reboot", lambda: core.reboot_check(adb))
                                permission_journal["android_reboot_verified"] = True
                                permission_journal["phase"] = "configured"
                                core.write_json(carlink_permissions.path(core, adb, state_dir), permission_journal)
                        rebooted = bool(carlink_permissions.load(core, adb, state_dir).get("android_reboot_verified"))
                return {"status": "configured", "carlink_permissions": result,
                        "android_reboot_verified": rebooted, "projection_tested": False,
                        "next_action": "phone_handoff" if rebooted else "rerun_setup_with_reboot_check"}, 0
            command = {"check": "carlink-check", "status": "carlink-check", "restore": "carlink-restore"}.get(args.command)
            if command is None:
                raise core.SetupError("An existing setup already owns this state directory; use status or restore.")
            result = carlink_trial.run(core, adb, state_dir, command)
            if command == "carlink-check":
                import carlink_permissions
                if carlink_permissions.path(core, adb, state_dir).exists():
                    try:
                        with configuration(core):
                            result["carlink_permissions"] = carlink_permissions.snapshot(core, adb)
                    except core.SetupError as exc:
                        result["carlink_permissions"] = {"ready": False, "error": str(exc)}
            return result, 2 if result.get("trial_eligible") is False else 0
    backup = core.backup_path(adb, state_dir)
    if backup.exists():
        try:
            prior = json.loads(backup.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise core.SetupError("Cannot read the original setup journal; preserve it.") from exc
        if not isinstance(prior, dict):
            raise core.SetupError("Invalid original setup journal; preserve it.")
        legacy_id = json.loads(core.PROFILE_PATH.read_text(encoding="utf-8"))["id"]
        if prior.get("profile") == legacy_id:
            # Recovery compatibility is not a public path that installs an old receiver.
            if args.command == "setup":
                raise core.SetupError("This journal belongs to an earlier setup. Keep it; use status or restore.")
            return core.run_commands(adb, state_dir, args)
    with configuration(core):
        return core.run_commands(adb, state_dir, args)
