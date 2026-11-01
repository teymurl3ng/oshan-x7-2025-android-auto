"""Compatibility and recovery for existing CarLink journals.

New public installations use carlink_setup and the shared setup engine. Keep
these original journal identities and recovery ownership for earlier cycles.
"""
from pathlib import Path
import json
import os
import re
import tempfile
import time
import urllib.request

BASE_PIN = {
    "package": "com.carlink.app", "version_name": "1.0.7", "version_code": 10007,
    "variant": "official-1.0.7",
    "bytes": 16747592,
    "sha256": "16e8b98436a5c5f355aa4b49086e28d41bee9f9f874174658cafb682fd503e77",
    "certificate_sha256": "037468ca5beb70ea5f68543329b03368247dfb393d3f626a6b472d10e5657d21",
    "url": "https://github.com/F-e-n-y-x/CarLink/releases/download/v1.0.7/CarLink-1.0.7.apk",
    "activity": "com.carlink.app/com.carlink.app.ui.HomeActivity",
}
PIN = {
    **BASE_PIN,
    "variant": "oshan-permission-coexist-1",
    "bytes": 16565044,
    "sha256": "a06e8ffcdcee0a1c555e39af9ea5f478addbb902b532f5b63a0c2c68d5f6a19e",
    "certificate_sha256": "dbacadae126d332ea436912ff63fd396d46833dae763ea6562dc694c7fe6d28c",
}
DEFAULT_PIN = BASE_PIN
# PIN records the already installed historical variant for journal recovery only.
LAUNCHER_PIN = json.loads((Path(__file__).resolve().parent / "profiles/f202-carlink-launcher.json").read_text())
COMPETITORS = ("com.shihab.diplay", "com.shihab.diplay.hudtest", "com.shilapi.xcertplay")
PHASES = {"backed_up", "waiting_for_permissions", "trial_ready", "restoring",
          "recovery_required", "restored", "install_carlink", "pause_openhu",
          "launch_carlink", "android_reboot", "stop_carlink", "restore_openhu",
          "verify_original", "remove_carlink", "baseline_health", "backup_openhu",
          "remove_openhu", "reinstall_openhu", "carlink_fullscreen", "restore_carlink_fullscreen",
          "backup_carlink_launcher", "install_carlink_launcher", "restore_carlink_launcher"}


def journal_path(core, adb, state_dir):
    return core.backup_path(adb, state_dir).with_name("carlink-trial.json")


def refuse_active(core, adb, state_dir):
    """Prevent the AA installer/restore from crossing an active trial's baseline."""
    path = journal_path(core, adb, state_dir)
    if path.exists():
        journal = Trial(core, adb, state_dir).load()
        if not journal["restored"]:
            raise core.SetupError("An app-only CarLink trial is active. Use carlink-restore "
                                  "with this state directory before AA setup/restore.")


def verify_apk(core, path, pin=None):
    pin = BASE_PIN if pin is None else pin
    path = Path(path).resolve()
    if (not path.is_file() or path.stat().st_size != pin["bytes"] or
            core.digest(path) != pin["sha256"]):
        raise core.SetupError("CarLink APK differs from the exact pinned " + pin["variant"] + " release.")
    return path


def obtain_apk(core, state_dir, supplied=None):
    """New installations always use the unmodified official release."""
    if supplied:
        return verify_apk(core, supplied)
    folder = Path(state_dir) / "cache"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = folder / "CarLink-1.0.7-official.apk"
    if not target.exists():
        _download_base(core, folder, target)
    return verify_apk(core, target)


def _download_base(core, folder, target):
    fd, temporary = tempfile.mkstemp(prefix=".carlink-base-", dir=folder)
    try:
        request = urllib.request.Request(BASE_PIN["url"], headers={"User-Agent": "oshan-x7-carlink-trial"})
        with os.fdopen(fd, "wb") as stream, urllib.request.urlopen(request, timeout=45) as response:
            if not response.geturl().startswith("https://"):
                raise core.SetupError("Refusing a CarLink download redirected away from HTTPS.")
            remaining = BASE_PIN["bytes"]
            while True:
                block = response.read(min(1024 * 1024, remaining + 1))
                if not block:
                    break
                remaining -= len(block)
                if remaining < 0:
                    raise core.SetupError("CarLink download exceeds its pinned size.")
                stream.write(block)
        if Path(temporary).stat().st_size != BASE_PIN["bytes"] or core.digest(temporary) != BASE_PIN["sha256"]:
            raise core.SetupError("Downloaded official CarLink base differs from the pinned release.")
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Trial:
    def __init__(self, core, adb, state_dir):
        self.c, self.adb, self.state_dir = core, adb, Path(state_dir)
        self.path = journal_path(core, adb, self.state_dir)
        self.pin = DEFAULT_PIN

    def load(self):
        c = self.c
        try:
            j = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise c.SetupError("Cannot read the original CarLink trial journal; preserve it.") from exc
        if isinstance(j, dict):
            self.pin = BASE_PIN if j.get("apk_sha256") == BASE_PIN["sha256"] else PIN
        original = j.get("original", {}) if isinstance(j, dict) else {}
        receiver = original.get("receiver", {}) if isinstance(original, dict) else {}
        launcher = original.get("launcher", {}) if isinstance(original, dict) else {}
        carauto = original.get("carauto", {}) if isinstance(original, dict) else {}
        if (not isinstance(j, dict) or j.get("schema") != 1 or
                j.get("kind") != "carlink_trial" or j.get("serial") != self.adb.serial or
                j.get("profile") != c.PROFILE["id"] or
                not (j.get("apk_sha256") == PIN["sha256"] or
                     (j.get("apk_sha256") == BASE_PIN["sha256"] and
                      (j.get("restored") is True or j.get("remove_openhu") is True))) or
                type(j.get("restored")) is not bool or j.get("phase") not in PHASES or
                type(j.get("android_reboot_verified")) is not bool or
                type(j.get("remove_openhu", False)) is not bool or
                not isinstance(receiver, dict) or receiver.get("installed") is not True or
                type(receiver.get("enabled")) is not int or receiver.get("enabled") not in (0, 1) or
                receiver.get("sha256") != c.PROFILE["receiver"]["sha256"] or
                receiver.get("version_code") != c.PROFILE["receiver"]["version_code"] or
                receiver.get("version_name") != c.PROFILE["receiver"]["version_name"] or
                not isinstance(carauto, dict) or carauto.get("installed") is not True or
                carauto.get("enabled") != 3 or not isinstance(launcher, dict) or
                launcher.get("sha256") not in (c.PROFILE["launcher"]["sha256"],
                                               c.PROFILE["launcher"]["update"]["sha256"]) or
                original.get("carlink_present") is not False or
                not isinstance(j.get("operations"), list) or
                any(not isinstance(e, dict) or e.get("name") not in PHASES or
                    type(e.get("complete")) is not bool for e in j["operations"])):
            raise c.SetupError("CarLink trial journal identity, baseline or operation record is invalid.")
        layout = original.get("fullscreen_value")
        if layout is not None and (type(layout) is not int or not -(2**31) <= layout < 2**31):
            raise c.SetupError("CarLink trial journal has an invalid original fullscreen value.")
        layout = j.get("carlink_fullscreen_original")
        if ((layout is not None and (type(layout) is not int or not -(2**31) <= layout < 2**31)) or
                (self.touched(j, "carlink_fullscreen") and "carlink_fullscreen_original" not in j)):
            raise c.SetupError("CarLink fullscreen baseline is missing or invalid; preserve the journal.")
        if self.touched(j, "install_carlink_launcher") and (
                j.get("launcher_migration_sha256") != LAUNCHER_PIN["sha256"] or
                original["launcher"]["sha256"] != c.PROFILE["launcher"]["update"]["sha256"]):
            raise c.SetupError("CarLink launcher migration identity is invalid; preserve the journal.")
        return j

    def touched(self, journal, name):
        return any(e["name"] == name for e in journal["operations"])

    def receiver_backup(self):
        return self.path.with_name("openhu-original.apk")

    def backup_receiver(self):
        """Copy the exact installed APK before any trial writes; data stays on car."""
        c = self.c
        target = self.receiver_backup()
        if target.exists():
            c.verify_apk(target)
        else:
            fd, temporary = tempfile.mkstemp(prefix=".openhu-", dir=self.path.parent)
            os.close(fd)
            try:
                self.adb.run("pull", c.apk_path(self.adb, c.RECEIVER), temporary, timeout=60)
                c.verify_apk(temporary)
                with open(temporary, "rb") as stream:
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return {"apk": str(target), "sha256": c.digest(target),
                "app_data": "retained_on_device_with_uninstall_k"}

    def owns_absence(self, journal):
        if not (journal and journal.get("remove_openhu") and self.touched(journal, "remove_openhu")):
            return False
        self.c.verify_apk(self.receiver_backup())
        return True

    def isolated(self, report, journal):
        receiver = report["receiver"]
        return (not receiver.get("installed") if journal.get("remove_openhu")
                else receiver.get("enabled") == 3)

    def remove_receiver(self):
        c = self.c
        c.verify_apk(self.receiver_backup())
        receiver = c.receiver_state(self.adb)
        if not receiver.get("installed") or not receiver.get("verified"):
            raise c.SetupError("Only the exact backed-up OpenHU can be removed.")
        output = self.adb.shell("pm", "uninstall", "-k", "--user", "0",
                                "--versionCode", str(c.PROFILE["receiver"]["version_code"]), c.RECEIVER)
        # Package broadcasts and per-user registration can settle after pm exits.
        # Do not issue another uninstall while waiting for the original read-back.
        deadline = time.monotonic() + 5
        while True:
            raw = self.adb.shell("dumpsys", "package", c.RECEIVER)
            diagnostic = self.path.with_name("openhu-removal-package.txt")
            diagnostic.write_text(raw, encoding="utf-8")
            os.chmod(diagnostic, 0o600)
            state = c.receiver_state(self.adb)
            if state.get("installed") is False or time.monotonic() >= deadline:
                break
            time.sleep(.5)
        if "Success" not in output or state.get("installed") is not False:
            raise c.SetupError("OpenHU removal did not verify: pm output=" + repr(output[:800]) +
                               "; read-back=" + repr(state) + ". Preserve the journal and APK backup.")
        return {"removed_for_user_0": True, "keep_data_requested": True, "pm_output": output[:800]}

    def remove_carlink(self):
        self.require_owned(self.package())
        output = self.adb.shell("pm", "uninstall", "--user", "0", PIN["package"])
        if "Success" not in output or self.package()["installed"]:
            raise self.c.SetupError("CarLink removal did not verify; keep the journal.")
        return {"removed": True}

    def reinstall_receiver(self):
        c = self.c
        apk = c.verify_apk(self.receiver_backup())
        output = self.adb.run("install", "--user", "0", "-r", str(apk), timeout=120).stdout
        state = c.receiver_state(self.adb)
        if "Success" not in output or not state.get("installed") or not state.get("verified"):
            raise c.SetupError("Reinstallation of the original OpenHU APK did not verify.")
        return state

    def package(self, pin=None):
        c, adb = self.c, self.adb
        pin = self.pin if pin is None else pin
        raw = adb.shell("dumpsys", "package", PIN["package"])
        present = bool(re.search(r"^\s*Package \[com\.carlink\.app\]", raw, re.M))
        state = c.parse_package(raw)
        state["present"] = present or state["installed"]
        if not state["installed"]:
            return state
        state["path"] = c.apk_path(adb, PIN["package"])
        state["sha256"] = c.remote_hash(adb, state["path"])
        uid = re.search(r"^\s*userId=(\d+)\s*$", raw, re.M)
        flags = re.search(r"^\s*(?:pkgFlags|flags)=\[([^\]]*)\]", raw, re.M)
        state["verified"] = bool(
            state.get("version_code") == pin["version_code"] and
            state.get("version_name") == pin["version_name"] and
            state["sha256"] == pin["sha256"] and uid and int(uid[1]) >= 10000 and flags and
            not {"SYSTEM", "UPDATED_SYSTEM_APP"}.intersection(flags[1].split()) and
            not re.search(r"^\s*sharedUser=", raw, re.M) and
            re.fullmatch(r"/data/app/com\.carlink\.app-[A-Za-z0-9_+=@~-]+/base\.apk", state["path"]))
        return state

    def inspect(self, journal=None, recovery=False):
        c = self.c
        launcher_pin = LAUNCHER_PIN if journal and self.touched(journal, "install_carlink_launcher") else None
        r = c.inspect(self.adb, recovery=True, launcher_update=launcher_pin)
        if not r["recovery_eligible"]:
            raise c.SetupError("CarLink refused: " + "; ".join(r["mismatches"]))
        if not r["boot_completed"]:
            raise c.SetupError("Wait for Android to finish booting before the CarLink trial or recovery.")
        if r["launcher"]["home"] not in (c.PROFILE["launcher"]["home"],
                c.PROFILE["launcher"]["package"] + "/com.chinatsp.launcher.MainAct"):
            raise c.SetupError("Default HOME changed; inspect it before any CarLink operation.")
        if not recovery:
            issues = list(r["component_issues"])
            if (journal and self.touched(journal, "pause_openhu") and
                    r["receiver"].get("verified") and r["receiver"].get("enabled") == 3):
                issues = [i for i in issues if not i.startswith("Existing Open Headunit is not the pinned, enabled ")]
            if issues:
                raise c.SetupError("CarLink trial preflight failed: " + "; ".join(issues))
            absent_owned = not r["receiver"].get("installed") and self.owns_absence(journal)
            if (not r["receiver"].get("installed") or not r["receiver"].get("verified")) and not absent_owned:
                raise c.SetupError("The existing pinned OpenHU installation is required for this trial.")
            expected = {0, 1}
            if journal and self.touched(journal, "pause_openhu"):
                expected.add(3)
            if not absent_owned and r["receiver"].get("enabled") not in expected:
                raise c.SetupError("OpenHU enabled state is not owned by this trial.")
            if r["carauto"].get("enabled") != 3:
                raise c.SetupError("This trial requires the existing AA setup with CarAuto already disabled. "
                                   "It does not change CarAuto.")
            for name in COMPETITORS:
                other = c.package(self.adb, name)
                if other["installed"] and other["enabled"] in (0, 1):
                    raise c.SetupError("Another enabled projection receiver needs inspection first: " + name)
            if journal:
                self.unchanged(r, journal)
        return r, self.package()

    def unchanged(self, report, journal):
        for key in ("carauto", "fullscreen_value", "launcher"):
            if key == "launcher" and self.touched(journal, "install_carlink_launcher"):
                original = journal["original"][key]
                current = report[key]
                if (current["sha256"] not in (original["sha256"], LAUNCHER_PIN["sha256"]) or
                        any(current[k] != original[k] for k in ("home", "uid", "version_code", "updated_system_app"))):
                    raise self.c.SetupError("Launcher differs from this migration's exact original or CarLink build.")
                continue
            if report[key] != journal["original"][key]:
                raise self.c.SetupError("The preexisting AA baseline changed outside this trial: " + key)

    def step(self, journal, name, action):
        return self.c.operation(self.path, journal, name, action)

    def enabled(self, package, value):
        c = self.c
        self.adb.shell("pm", c.ENABLE_COMMANDS[value], "--user", "0", package)
        state = c.package(self.adb, package)
        if not state["installed"] or state["enabled"] != value:
            raise c.SetupError("Package enabled-state read-back failed for " + package)
        return {"package": package, "enabled": value}

    def launch(self, component, baseline=None):
        try:
            return self.c.healthy_launch(self.adb, component, baseline)
        except self.c.NeedsPermissions as exc:
            raise self.c.NeedsPermissions("Inspect the unexpected CarLink permission screen and diagnose "
                                         "the missing access. Keep Device mode and the original backup; "
                                         "use status or restore before attempting setup again.") from exc

    def require_owned(self, state):
        if not state.get("installed") or not state.get("verified"):
            raise self.c.SetupError("CarLink differs from the exact owned APK; it will not be changed or removed.")

    def launcher_backup(self):
        return self.path.with_name("launcher-before-carlink.apk")

    def verify_carlink_launcher(self, path):
        path = Path(path)
        if (not path.is_file() or path.stat().st_size != LAUNCHER_PIN["bytes"] or
                self.c.digest(path) != LAUNCHER_PIN["sha256"]):
            raise self.c.SetupError("CarLink launcher differs from the audited, pinned candidate.")
        return path

    def prepare_carlink_launcher(self, report):
        c = self.c
        folder = self.path.parent
        backup = self.launcher_backup()
        factory = folder / "launcher-factory.apk"
        for remote, target, factory_flag in (
                (report["launcher"]["path"], backup, False),
                (c.PROFILE["launcher"]["path"], factory, True)):
            if not target.exists():
                fd, temporary = tempfile.mkstemp(prefix=".launcher-backup-", dir=folder)
                os.close(fd)
                try:
                    self.adb.run("pull", remote, temporary, timeout=60)
                    c.verify_launcher_file(temporary, factory=factory_flag)
                    with open(temporary, "rb") as stream:
                        os.fsync(stream.fileno())
                    os.replace(temporary, target)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            c.verify_launcher_file(target, factory=factory_flag)
        patch = c.ROOT / LAUNCHER_PIN["patch"]
        if (patch.stat().st_size != LAUNCHER_PIN["patch_bytes"] or
                c.digest(patch) != LAUNCHER_PIN["patch_sha256"]):
            raise c.SetupError("CarLink launcher patch differs from its audited pin.")
        output = folder / "launcher-carlink.apk"
        if not output.exists():
            payload = c.apply_launcher_patch(factory.read_bytes(), patch.read_bytes(), LAUNCHER_PIN["bytes"])
            fd, temporary = tempfile.mkstemp(prefix=".launcher-carlink-", dir=folder)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                self.verify_carlink_launcher(temporary)
                os.replace(temporary, output)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        self.verify_carlink_launcher(output)
        return {"original_backup": str(backup), "factory_backup": str(factory), "prepared_apk": str(output)}

    def restore_carlink_launcher(self, journal):
        c = self.c
        report, _ = self.inspect(journal, recovery=True)
        current = report["launcher"]
        original = journal["original"]["launcher"]["sha256"]
        if current["sha256"] == original:
            return {"unchanged": True}
        if current["sha256"] != LAUNCHER_PIN["sha256"]:
            raise c.SetupError("Unknown launcher will not be overwritten during CarLink recovery.")
        backup = c.verify_launcher_file(self.launcher_backup())
        output = self.adb.run("install", "--no-streaming", "-r", str(backup), timeout=180).stdout
        if not re.search(r"^Success\s*$", output, re.M) or c.launcher_state(self.adb)["sha256"] != original:
            raise c.SetupError("Original launcher reinstall did not verify; retain USB and backups.")
        return self.launch(c.PROFILE["launcher"]["home"])

    def promote(self, journal, verify_reboot=False):
        c = self.c
        if journal["restored"] or journal["phase"] != "trial_ready":
            raise c.SetupError("Promotion requires the existing ready CarLink trial and its original state directory.")
        report, state = self.inspect(journal)
        self.require_owned(state)
        if (not journal.get("remove_openhu") or report["receiver"].get("installed") or
                state["enabled"] not in (0, 1) or self.layout() != 0):
            raise c.SetupError("Promotion requires the working fullscreen CarLink trial with OpenHU absent.")
        if journal["original"]["launcher"]["sha256"] != c.PROFILE["launcher"]["update"]["sha256"]:
            raise c.SetupError("Only the exact previous OpenHU launcher can be migrated by this command.")
        try:
            if report["launcher"]["sha256"] != LAUNCHER_PIN["sha256"]:
                self.step(journal, "backup_carlink_launcher", lambda: self.prepare_carlink_launcher(report))
                journal["launcher_migration_sha256"] = LAUNCHER_PIN["sha256"]
                journal["carlink_launcher_reboot_verified"] = False
                journal.pop("observed_reboot_boot_id", None)
                c.write_json(self.path, journal)
                def install_launcher():
                    self.inspect(journal)
                    apk = self.verify_carlink_launcher(self.path.with_name("launcher-carlink.apk"))
                    baseline = c.health.logs(self.adb)
                    output = self.adb.run("install", "--no-streaming", "-r", str(apk), timeout=180).stdout
                    if not re.search(r"^Success\s*$", output, re.M):
                        raise c.SetupError("CarLink launcher installation did not confirm success.")
                    after, _ = self.inspect(journal)
                    if after["launcher"]["sha256"] != LAUNCHER_PIN["sha256"]:
                        raise c.SetupError("Installed CarLink launcher identity did not verify.")
                    return self.launch(c.PROFILE["launcher"]["home"], baseline)
                self.step(journal, "install_carlink_launcher", install_launcher)
            self.launch(PIN["activity"])
            self.launch(c.PROFILE["launcher"]["home"])
            if verify_reboot and not journal.get("carlink_launcher_reboot_verified"):
                self.step(journal, "android_reboot", lambda: self.reboot(journal))
                if self.layout() != 0:
                    raise c.SetupError("CarLink fullscreen did not persist through reboot.")
                self.launch(c.PROFILE["launcher"]["home"])
                journal["carlink_launcher_reboot_verified"] = True
            journal["primary_receiver"] = "carlink"
            journal["phase"] = "trial_ready"
            c.write_json(self.path, journal)
            return {**self.result(journal, "carlink_configured"),
                    "launcher": self.inspect(journal)[0]["launcher"],
                    "carlink_launcher_reboot_verified": bool(journal.get("carlink_launcher_reboot_verified"))}
        except (Exception, KeyboardInterrupt) as exc:
            journal["launcher_migration_error"] = str(exc)
            c.write_json(self.path, journal)
            try:
                if self.touched(journal, "install_carlink_launcher"):
                    self.step(journal, "restore_carlink_launcher", lambda: self.restore_carlink_launcher(journal))
                journal["phase"] = "trial_ready"
                journal["primary_receiver"] = None
                c.write_json(self.path, journal)
            except (Exception, KeyboardInterrupt) as recovery_exc:
                journal["phase"] = "recovery_required"
                journal["recovery_error"] = str(recovery_exc)
                c.write_json(self.path, journal)
            raise c.SetupError("CarLink launcher migration failed: " + str(exc),
                               recovery=self.result(journal, journal["phase"])) from exc

    def layout(self):
        return self.c.parse_layout(self.adb.shell("cat", self.c.PREFS, root=True), PIN["package"])

    def set_layout(self, value):
        c = self.c
        baseline = c.health.logs(self.adb)
        c.broadcast_layout(self.adb, value, package_name=PIN["package"])
        c.refresh(self.adb, package_name=PIN["package"])
        return {"value": value, "systemui": c.healthy_systemui(self.adb, baseline)}

    def restore_layout(self, journal):
        original = journal["carlink_fullscreen_original"]
        current = self.layout()
        wanted = -1 if original is None else original
        if current == original or current == wanted:
            return {"unchanged": True, "value": current}
        if current != 0:
            raise self.c.SetupError("CarLink fullscreen changed outside this trial; refusing to overwrite it.")
        return self.set_layout(wanted)

    def fullscreen(self, journal):
        c = self.c
        if journal["restored"] or journal["phase"] != "trial_ready":
            raise c.SetupError("CarLink fullscreen requires the existing ready trial and its original state directory.")
        report, state = self.inspect(journal)
        self.require_owned(state)
        if not self.isolated(report, journal) or state["enabled"] not in (0, 1):
            raise c.SetupError("Receiver isolation is required before applying CarLink fullscreen.")
        if "carlink_fullscreen_original" not in journal:
            xml = self.adb.shell("cat", c.PREFS, root=True)
            journal["carlink_fullscreen_original"] = c.parse_layout(xml, PIN["package"])
            snapshot = self.path.with_name("systemui-prefs-before-carlink-fullscreen.xml")
            snapshot.write_text(xml, encoding="utf-8")
            os.chmod(snapshot, 0o600)
            c.write_json(self.path, journal)
        try:
            def apply():
                result = self.set_layout(0) if self.layout() != 0 else {"value": 0, "unchanged": True}
                self.launch(c.PROFILE["launcher"]["home"])
                result["carlink"] = self.launch(PIN["activity"])
                self.inspect(journal)
                return result
            self.step(journal, "carlink_fullscreen", apply)
            journal["phase"] = "trial_ready"
            c.write_json(self.path, journal)
            return {**self.result(journal, "fullscreen_ready"), "carlink_fullscreen_value": self.layout(),
                    "fullscreen_phone_tested": False, "fullscreen_reboot_tested": False}
        except (Exception, KeyboardInterrupt) as exc:
            try:
                self.inspect(journal, recovery=True)
                self.step(journal, "restore_carlink_fullscreen", lambda: self.restore_layout(journal))
                journal["phase"] = "trial_ready"
                c.write_json(self.path, journal)
            except (Exception, KeyboardInterrupt) as recovery_exc:
                journal["phase"] = "recovery_required"
                journal["recovery_error"] = str(recovery_exc)
                c.write_json(self.path, journal)
                raise c.SetupError("CarLink fullscreen failed and layout recovery is incomplete. Run carlink-restore.",
                                   recovery=self.result(journal, "recovery_required")) from exc
            raise c.SetupError("CarLink fullscreen failed; its original layout was restored: " + str(exc)) from exc

    def reboot(self, journal):
        c = self.c
        old = self.adb.shell("cat", "/proc/sys/kernel/random/boot_id")
        pattern = r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}"
        if not re.fullmatch(pattern, old):
            raise c.SetupError("Cannot establish the Android boot identity.")
        # A permission pause after observing the reboot must not request it again.
        observed = journal.get("observed_reboot_boot_id")
        if observed != old:
            self.adb.run("reboot")
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            time.sleep(min(2, deadline - time.monotonic()))
            try:
                self.adb.select_usb(timeout=min(3, max(.1, deadline - time.monotonic())))
                boot = self.adb.shell("cat", "/proc/sys/kernel/random/boot_id", timeout=3)
                if (re.fullmatch(pattern, boot) and (boot != old or boot == observed) and
                        self.adb.shell("getprop", "sys.boot_completed", timeout=3) == "1"):
                    break
            except c.SetupError:
                continue
        else:
            raise c.SetupError("Android did not return over USB within 120 seconds. "
                               "Keep the journal, regain Device mode and run carlink-restore.")
        journal["observed_reboot_boot_id"] = boot
        c.write_json(self.path, journal)
        r, state = self.inspect(journal)
        self.require_owned(state)
        if not self.isolated(r, journal) or state["enabled"] not in (0, 1):
            raise c.SetupError("Receiver isolation did not persist through the Android reboot.")
        return {"home": self.launch(c.PROFILE["launcher"]["home"]),
                "carlink": self.launch(PIN["activity"]), "ignition_cycle_tested": False}

    def restore(self, journal):
        c = self.c
        if journal["restored"]:
            return self.result(journal, "already_restored")
        journal["phase"] = "restoring"
        c.write_json(self.path, journal)
        try:
            r, state = self.inspect(journal, recovery=True)
            if self.touched(journal, "install_carlink_launcher"):
                self.step(journal, "restore_carlink_launcher", lambda: self.restore_carlink_launcher(journal))
                r, state = self.inspect(journal, recovery=True)
            # Root-dependent grants must not prevent an independently owned Home
            # update rollback. Their original app is retained until grants recover.
            import carlink_permissions
            if carlink_permissions.path(c, self.adb, self.state_dir).exists():
                from carlink_setup import configuration
                prior_update = c.PROFILE["launcher"]["update"]
                with configuration(c):
                    if r["launcher"]["sha256"] == prior_update["sha256"]:
                        c.PROFILE["launcher"]["update"] = prior_update
                    carlink_permissions.restore(c, self.adb, self.state_dir)
            if state["installed"]:
                if not self.touched(journal, "install_carlink"):
                    raise c.SetupError("CarLink was not installed by this journal; refusing removal.")
                self.require_owned(state)
                if state["enabled"] in (0, 1):
                    self.step(journal, "stop_carlink", lambda: self.enabled(PIN["package"], 3))
                elif state["enabled"] != 3:
                    raise c.SetupError("Unexpected CarLink enabled state; inspect it before recovery.")
            if self.touched(journal, "carlink_fullscreen"):
                self.step(journal, "restore_carlink_fullscreen", lambda: self.restore_layout(journal))
            receiver = r["receiver"]
            if self.pin == BASE_PIN and state["installed"]:
                self.launch(c.PROFILE["launcher"]["home"])
                c.verify_apk(self.receiver_backup())
                self.step(journal, "remove_carlink", self.remove_carlink)
                state = self.package()
            if not receiver.get("installed") and self.owns_absence(journal):
                self.step(journal, "reinstall_openhu", self.reinstall_receiver)
                receiver = c.receiver_state(self.adb)
            if not receiver.get("installed") or not receiver.get("verified"):
                raise c.SetupError("Original OpenHU identity cannot be verified; CarLink is retained.")
            original = journal["original"]["receiver"]["enabled"]
            if receiver["enabled"] != original:
                owned_state = (self.touched(journal, "pause_openhu") and receiver["enabled"] == 3)
                owned_state |= (self.touched(journal, "remove_openhu") and receiver["enabled"] in (0, 1, 3))
                if not owned_state:
                    raise c.SetupError("Unexpected OpenHU enabled state; refusing to overwrite it.")
                self.step(journal, "restore_openhu", lambda: self.enabled(c.RECEIVER, original))
            def original_health():
                self.launch(c.PROFILE["launcher"]["home"])
                self.launch(c.MAIN_ACTIVITY)
                return self.launch(c.PROFILE["launcher"]["home"])
            self.step(journal, "verify_original", original_health)
            # Recheck the physical target and both identities immediately before removal.
            r, state = self.inspect(journal, recovery=True)
            if (not r["receiver"].get("verified") or r["receiver"].get("enabled") != original):
                raise c.SetupError("Original OpenHU changed during recovery; retaining CarLink.")
            if state["installed"]:
                self.require_owned(state)
                self.step(journal, "remove_carlink", self.remove_carlink)
            after = c.inspect(self.adb)
            c.require_compatible(after)
            self.unchanged(after, journal)
            journal["phase"], journal["restored"] = "restored", True
            journal["primary_receiver"] = None
            journal["restored_at"] = c.now()
            c.write_json(self.path, journal)
            return self.result(journal, "restored")
        except (Exception, KeyboardInterrupt) as exc:
            journal["phase"] = "recovery_required"
            journal["recovery_error"] = str(exc) or type(exc).__name__
            c.write_json(self.path, journal)
            raise c.SetupError("CarLink trial recovery is incomplete: " + journal["recovery_error"],
                               recovery=self.result(journal, "recovery_required")) from exc

    def start(self, supplied=None, verify_reboot=False, remove_openhu=False):
        c = self.c
        journal = self.load() if self.path.exists() else None
        if journal and journal["restored"]:
            raise c.SetupError("This CarLink trial was restored. Preserve it and use a new state "
                               "directory for a later trial.")
        if journal and journal["phase"] not in {"backed_up", "waiting_for_permissions", "trial_ready"}:
            raise c.SetupError("An earlier CarLink operation was interrupted. Run carlink-restore first.")
        if journal and remove_openhu and not journal.get("remove_openhu"):
            raise c.SetupError("Cannot change the removal mode of an existing trial; restore it first.")
        r, state = self.inspect(journal)
        if not journal and self.pin == BASE_PIN and not remove_openhu:
            raise c.SetupError("The official CarLink trial requires --remove-openhu; removal happens before installation.")
        if state["present"] and not journal:
            raise c.SetupError("CarLink already exists outside this trial. It will not be adopted or overwritten.")
        if state["present"]:
            self.require_owned(state)
            if not self.touched(journal, "install_carlink") or state["enabled"] not in (0, 1):
                raise c.SetupError("Unexpected existing CarLink state; run carlink-restore.")
        elif journal and self.touched(journal, "install_carlink"):
            raise c.SetupError("CarLink disappeared after its recorded installation; run carlink-restore.")
        apk = obtain_apk(c, self.state_dir, supplied) if not state["installed"] else None
        if not journal:
            journal = {"schema": 1, "kind": "carlink_trial", "profile": c.PROFILE["id"],
                       "serial": self.adb.serial, "created_at": c.now(), "phase": "backed_up",
                       "apk_sha256": self.pin["sha256"], "restored": False, "operations": [],
                       "variant": self.pin["variant"],
                       "remove_openhu": remove_openhu,
                       "android_reboot_verified": False,
                       "original": {**{key: r[key] for key in
                                       ("receiver", "carauto", "fullscreen_value", "launcher")},
                                    "carlink_present": False}}
            c.write_json(self.path, journal)
        try:
            install_baseline = None
            if journal.get("remove_openhu"):
                if not self.touched(journal, "remove_openhu"):
                    self.step(journal, "backup_openhu", self.backup_receiver)
                else:
                    c.verify_apk(self.receiver_backup())
            if not state["installed"]:
                def baseline_health():
                    self.launch(c.PROFILE["launcher"]["home"])
                    self.launch(c.MAIN_ACTIVITY)
                    return self.launch(c.PROFILE["launcher"]["home"])
                self.step(journal, "baseline_health", baseline_health)
                install_baseline = c.health.logs(self.adb)
                if self.pin == BASE_PIN and r["receiver"].get("installed"):
                    self.step(journal, "remove_openhu", self.remove_receiver)
                def install():
                    output = self.adb.run("install", "--user", "0", str(apk), timeout=120).stdout
                    if "Success" not in output:
                        raise c.SetupError("CarLink install did not report Success.")
                    installed = self.package()
                    self.require_owned(installed)
                    return installed
                self.step(journal, "install_carlink", install)
            r, state = self.inspect(journal)
            self.require_owned(state)
            if journal.get("remove_openhu"):
                if r["receiver"].get("installed"):
                    self.step(journal, "remove_openhu", self.remove_receiver)
            elif r["receiver"]["enabled"] != 3:
                self.step(journal, "pause_openhu", lambda: self.enabled(c.RECEIVER, 3))
            self.step(journal, "launch_carlink", lambda: self.launch(PIN["activity"], install_baseline))
            if verify_reboot and not journal.get("android_reboot_verified"):
                self.step(journal, "android_reboot", lambda: self.reboot(journal))
                journal["android_reboot_verified"] = True
            r, state = self.inspect(journal)
            self.require_owned(state)
            if not self.isolated(r, journal) or state["enabled"] not in (0, 1):
                raise c.SetupError("Only CarLink must be enabled during its phone trial.")
            journal["phase"] = "trial_ready"
            c.write_json(self.path, journal)
            return self.result(journal, "trial_ready")
        except c.NeedsPermissions as exc:
            journal["phase"] = "waiting_for_permissions"
            c.write_json(self.path, journal)
            return {**self.result(journal, journal["phase"]), "message": str(exc)}
        except (Exception, KeyboardInterrupt) as exc:
            journal["failed_stage"] = journal["phase"]
            journal["error"] = str(exc) or type(exc).__name__
            c.write_json(self.path, journal)
            try:
                recovery = self.restore(journal)
            except c.SetupError as recovery_error:
                recovery = recovery_error.details.get("recovery", {"status": "recovery_required"})
            raise c.SetupError("CarLink trial failed: " + journal["error"],
                               failed_stage=journal["failed_stage"], recovery=recovery) from exc

    def result(self, journal, status):
        return {"status": status, "experimental": True, "journal": str(self.path),
                "variant": self.pin["variant"],
                "openhu_removal_mode": bool(journal.get("remove_openhu")),
                "openhu_apk_backup": str(self.receiver_backup()) if journal.get("remove_openhu") else None,
                "primary_receiver": journal.get("primary_receiver"),
                "carlink_launcher_reboot_verified": bool(journal.get("carlink_launcher_reboot_verified")),
                "projection_tested": False,
                "android_reboot_verified": bool(journal.get("android_reboot_verified")),
                "next_action": ("inspect_permission_prompt" if status == "waiting_for_permissions"
                                else "carlink_restore" if status == "recovery_required"
                                else "trial_restore_complete" if journal["restored"]
                                else "phone_handoff" if journal.get("android_reboot_verified")
                                else "inspect_existing_setup_with_status")}


def run(core, adb, state_dir, command, supplied=None, verify_reboot=False, remove_openhu=False):
    adb.select_usb()
    trial = Trial(core, adb, state_dir)
    if command == "carlink-check":
        journal = trial.load() if trial.path.exists() else None
        r, state = trial.inspect(journal if journal and not journal["restored"] else None)
        if state["present"]:
            if not journal or journal["restored"] or not trial.touched(journal, "install_carlink"):
                raise core.SetupError("Preexisting CarLink is outside trial ownership; no writes are allowed.")
            trial.require_owned(state)
        interrupted = bool(journal and journal["phase"] not in
                           {"backed_up", "waiting_for_permissions", "trial_ready", "restored"})
        restored = bool(journal and journal["restored"])
        primary = bool(journal and not restored and not interrupted and
                       journal.get("primary_receiver") == "carlink" and
                       r["launcher"]["sha256"] == LAUNCHER_PIN["sha256"])
        return {"status": "recovery_required" if interrupted else
                          "trial_restored" if restored else "carlink_configured" if primary else "trial_eligible",
                "trial_eligible": not interrupted and not restored,
                "primary_receiver": "carlink" if primary else None,
                "carlink_launcher_reboot_verified": bool(journal and journal.get("carlink_launcher_reboot_verified")),
                "experimental": True, "device_writes": False,
                "projection_tested": False, "carlink": state, "openhu": r["receiver"],
                "trial_phase": journal["phase"] if journal else None,
                "next_action": "carlink_restore" if interrupted else
                               "use_new_state_directory" if restored else
                               "inspect_permission_prompt" if journal and journal["phase"] == "waiting_for_permissions" else
                               "phone_handoff" if primary else "inspect_existing_setup_with_status"}
    with core.exclusive(state_dir):
        if command in ("carlink-reference-start", "carlink-reference-collect", "carlink-reference-pages"):
            import reference_capture
            return reference_capture.run(trial, command)
        if command == "carlink-restore":
            return trial.restore(trial.load())
        if command == "carlink-fullscreen":
            return trial.fullscreen(trial.load())
        if command == "carlink-promote":
            return trial.promote(trial.load(), verify_reboot)
        return trial.start(supplied, verify_reboot, remove_openhu)
