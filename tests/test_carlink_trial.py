"""App-only trial, conflict isolation and interrupted recovery; no real ADB."""
import contextlib
import copy
import io
import hashlib
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import carlink_trial as trial
import oshan_x7 as core
from test_oshan_x7 import DeviceFixture, FakeADB


class TrialADB(FakeADB):
    def __init__(self, old_enabled=0):
        super().__init__(receiver=True, enabled=3, layout=0)
        self.packages[core.RECEIVER]["enabled"] = old_enabled
        self.packages[trial.PIN["package"]] = {
            "installed": False, "enabled": 0, "version_code": 10007, "version_name": "1.0.7"}
        self.global_carlink = False
        self.paths[trial.PIN["package"]] = "/data/app/com.carlink.app-trial==/base.apk"
        self.hashes[self.paths[trial.PIN["package"]]] = trial.PIN["sha256"]
        self.carlink_permission = False
        self.carlink_layout = None
        self.persist_carlink_layout = True
        self.launcher_updated = True
        self.paths[core.PROFILE["launcher"]["package"]] = "/data/app/com.chinatsp.launcher-owned==/base.apk"
        self.hashes[self.paths[core.PROFILE["launcher"]["package"]]] = core.PROFILE["launcher"]["update"]["sha256"]

    def xml(self):
        xml = super().xml()
        if self.carlink_layout is not None:
            xml = xml.replace("</map>", f'<int name="{trial.PIN["package"]}" value="{self.carlink_layout}" /></map>')
        return xml

    def run(self, *args, **kwargs):
        if args[:3] == ("install", "--user", "0"):
            if self.disconnected:
                raise core.SetupError("simulated disconnected transport")
            self.commands.append(args)
            def effect():
                self.global_carlink = True
                self.packages[trial.PIN["package"]]["installed"] = True
            self.mutate("carlink_install", effect)
            return subprocess.CompletedProcess(args, 0, "Success\n", "")
        return super().run(*args, **kwargs)

    def respond(self, words, root):
        name = trial.PIN["package"]
        if words[:2] == ["am", "broadcast"] and root and name in words:
            action = words[words.index("-a") + 1]
            if action == "com.chinatsp.systemui.ACTION_APP_INFO":
                value = int(words[-1])
                def effect():
                    if self.persist_carlink_layout:
                        self.carlink_layout = value
                self.mutate("carlink_layout", effect)
            elif action == "com.chinatsp.activity.onpostresume":
                self.mutate("carlink_refresh", lambda: None)
            else:
                raise AssertionError(words)
            return "Broadcast completed: result=0"
        if words == ["dumpsys", "package", name]:
            state = self.packages[name]
            if not self.global_carlink:
                return "Unable to find package"
            return (f'Packages:\n  Package [{name}] (abc):\n'
                    '    userId=10123\n    pkgFlags=[ HAS_CODE ]\n'
                    f'    versionCode={state["version_code"]} minSdk=25\n'
                    f'    versionName={state["version_name"]}\n'
                    f'    User 0: installed={str(state["installed"]).lower()} hidden=false enabled={state["enabled"]}\n')
        if words == ["pm", "uninstall", "--user", "0", name]:
            assert not root
            # Android may retain a global package record after user-scoped removal.
            self.mutate("carlink_remove", lambda: self.packages[name].update(installed=False))
            return "Success"
        if (words[:1] == ["pm"] and len(words) == 5 and
                words[1] in core.ENABLE_COMMANDS.values() and words[-1] in (name, core.RECEIVER)):
            assert not root
            value = next(k for k, v in core.ENABLE_COMMANDS.items() if v == words[1])
            label = "stop_carlink" if words[-1] == name else "pause_openhu" if value == 3 else "restore_openhu"
            self.mutate(label, lambda: self.packages[words[-1]].update(enabled=value))
            return "new state"
        if words[:2] == ["am", "start"]:
            component = words[-1]
            package = component.split("/")[0]
            if self.packages.get(package, {}).get("enabled") == 3:
                return "Error: activity is disabled"
            result = super().respond(words, root)
            if component == trial.PIN["activity"] and self.carlink_permission:
                self.foreground = "com.android.packageinstaller/.permission.ui.GrantPermissionsActivity"
            return result
        return super().respond(words, root)


class RemovalADB(TrialADB):
    apk_payload = b"synthetic pinned OpenHU APK for offline recovery tests"
    readback_lag = 0
    pending_reads = 0

    def run(self, *args, **kwargs):
        if args[:1] == ("pull",):
            self.commands.append(args)
            Path(args[2]).write_bytes(self.apk_payload)
            return subprocess.CompletedProcess(args, 0, "pulled", "")
        if args[:4] == ("install", "--user", "0", "-r"):
            self.commands.append(args)
            assert Path(args[4]).read_bytes() == self.apk_payload
            self.mutate("reinstall_openhu", lambda: self.packages[core.RECEIVER].update(installed=True))
            return subprocess.CompletedProcess(args, 0, "Success", "")
        return super().run(*args, **kwargs)

    def respond(self, words, root):
        if words == ["pm", "uninstall", "-k", "--user", "0", "--versionCode", "119", core.RECEIVER]:
            assert not root
            self.mutate("remove_openhu", lambda: self.packages[core.RECEIVER].update(installed=False))
            self.pending_reads = self.readback_lag
            return "Success"
        if words == ["dumpsys", "package", core.RECEIVER] and self.pending_reads:
            self.pending_reads -= 1
            self.packages[core.RECEIVER]["installed"] = True
            try:
                return super().respond(words, root)
            finally:
                self.packages[core.RECEIVER]["installed"] = False
        return super().respond(words, root)


class RemovalTests(DeviceFixture):
    def setUp(self):
        super().setUp()
        profile = copy.deepcopy(core.PROFILE)
        profile["receiver"].update(bytes=len(RemovalADB.apk_payload),
                                   sha256=hashlib.sha256(RemovalADB.apk_payload).hexdigest())
        for p in (patch.object(core, "PROFILE", profile),
                  patch.object(trial, "DEFAULT_PIN", trial.PIN),
                  patch.object(trial, "obtain_apk", return_value=Path("pinned-carlink.apk"))):
            p.start()
            self.addCleanup(p.stop)

    def start(self, car, reboot=True):
        return trial.run(core, car, self.state, "carlink-trial", verify_reboot=reboot, remove_openhu=True)

    def restore(self, car):
        return trial.run(core, car, self.state, "carlink-restore")

    def test_backup_before_writes_and_keep_data_uninstall_survives_reboot(self):
        car = RemovalADB(old_enabled=1)
        def check_backup(name):
            backup = trial.Trial(core, car, self.state).receiver_backup()
            self.assertEqual(RemovalADB.apk_payload, core.verify_apk(backup).read_bytes())
        car.on_write = check_backup
        result = self.start(car)
        self.assertTrue(result["android_reboot_verified"])
        self.assertFalse(car.packages[core.RECEIVER]["installed"])
        self.assertNotIn("pause_openhu", car.writes)
        self.assertEqual("trial_eligible", trial.run(core, car, self.state, "carlink-check")["status"])
        self.assertEqual("restored", self.restore(car)["status"])
        self.assertTrue(car.packages[core.RECEIVER]["installed"])
        self.assertEqual(1, car.packages[core.RECEIVER]["enabled"])
        self.assertLess(car.writes.index("reinstall_openhu"), car.writes.index("carlink_remove"))
        before = car.writes[:]
        self.assertEqual("already_restored", self.restore(car)["status"])
        self.assertEqual(before, car.writes)

    def test_uncertain_removal_restores_from_same_backup_without_repeating_removal(self):
        car = RemovalADB()
        car.fail_at, car.fail_after_effect = "remove_openhu", True
        with self.assertRaises(core.SetupError):
            self.start(car)
        self.assertFalse(car.packages[core.RECEIVER]["installed"])
        car.disconnected, car.fail_at = False, None
        self.assertEqual("restored", self.restore(car)["status"])
        self.assertEqual(1, car.writes.count("remove_openhu"))
        self.assertEqual(1, car.writes.count("reinstall_openhu"))

    def test_official_signature_recovery_frees_permission_before_previous_app_reinstall(self):
        car = RemovalADB()
        self.start(car)
        instance = trial.Trial(core, car, self.state)
        journal = instance.load()
        journal["apk_sha256"] = trial.BASE_PIN["sha256"]
        journal["variant"] = trial.BASE_PIN["variant"]
        core.write_json(instance.path, journal)
        car.hashes[car.paths[trial.PIN["package"]]] = trial.BASE_PIN["sha256"]
        self.assertEqual("restored", self.restore(car)["status"])
        self.assertLess(car.writes.index("carlink_remove"), car.writes.index("reinstall_openhu"))

    def test_uncertain_reinstall_is_read_back_without_second_install(self):
        car = RemovalADB()
        self.start(car)
        car.fail_at, car.fail_after_effect = "reinstall_openhu", True
        with self.assertRaises(core.SetupError):
            self.restore(car)
        car.disconnected, car.fail_at = False, None
        self.assertEqual("restored", self.restore(car)["status"])
        self.assertEqual(1, car.writes.count("reinstall_openhu"))

    def test_corrupt_backup_blocks_reinstall_and_retains_carlink(self):
        car = RemovalADB()
        self.start(car)
        trial.Trial(core, car, self.state).receiver_backup().write_bytes(b"tampered")
        with self.assertRaises(core.SetupError):
            self.restore(car)
        self.assertNotIn("reinstall_openhu", car.writes)
        self.assertNotIn("carlink_remove", car.writes)

    def test_unknown_receiver_replacement_is_not_overwritten(self):
        car = RemovalADB()
        self.start(car)
        car.packages[core.RECEIVER]["installed"] = True
        car.hashes[car.paths[core.RECEIVER]] = "f" * 64
        with self.assertRaises(core.SetupError):
            self.restore(car)
        self.assertNotIn("reinstall_openhu", car.writes)
        self.assertNotIn("carlink_remove", car.writes)

    def test_no_owned_absence_without_recorded_removal(self):
        car = RemovalADB()
        car.packages[core.RECEIVER]["installed"] = False
        with self.assertRaises(core.SetupError):
            self.start(car)
        self.assertEqual([], car.writes)

    def test_incorrect_pulled_apk_prevents_removal_and_installation(self):
        car = RemovalADB()
        car.apk_payload = b"wrong APK"
        with self.assertRaises(core.SetupError):
            self.start(car)
        self.assertNotIn("remove_openhu", car.writes)
        self.assertNotIn("carlink_install", car.writes)

    def test_delayed_removal_readback_waits_without_repeating_uninstall(self):
        car = RemovalADB()
        car.readback_lag = 3
        self.assertEqual("trial_ready", self.start(car)["status"])
        self.assertEqual(1, car.writes.count("remove_openhu"))
        self.assertEqual("restored", self.restore(car)["status"])

    def test_retained_dumpsys_metadata_without_active_registration_is_absent(self):
        car = RemovalADB()
        original = car.respond
        def retained(words, root):
            if words == ["pm", "list", "packages", "--user", "0", core.RECEIVER]:
                return ""
            return original(words, root)
        car.respond = retained
        self.assertTrue(core.package(car, core.RECEIVER)["installed"])
        self.assertEqual({"installed": False, "verified": True}, core.receiver_state(car))

    def test_malformed_active_registration_is_refused(self):
        car = RemovalADB()
        original = car.respond
        car.respond = lambda words, root: ("Error: package service failed" if words ==
            ["pm", "list", "packages", "--user", "0", core.RECEIVER] else original(words, root))
        with self.assertRaises(core.SetupError):
            core.receiver_state(car)


class PromotionADB(RemovalADB):
    def run(self, *args, **kwargs):
        if args[:3] == ("install", "--no-streaming", "-r"):
            self.commands.append(args)
            wanted = trial.LAUNCHER_PIN["sha256"] if Path(args[3]).name == "launcher-carlink.apk" else core.PROFILE["launcher"]["update"]["sha256"]
            def effect():
                self.hashes[self.paths[core.PROFILE["launcher"]["package"]]] = wanted
            self.mutate("promote_launcher" if wanted == trial.LAUNCHER_PIN["sha256"] else "return_launcher", effect)
            return subprocess.CompletedProcess(args, 0, "Success\n", "")
        if args == ("reboot",):
            result = super().run(*args, **kwargs)
            self.boot_id = ("33333333-3333-4333-8333-333333333333" if self.writes.count("reboot") > 1
                            else "22222222-2222-4222-8222-222222222222")
            return result
        return super().run(*args, **kwargs)


class PromotionTests(RemovalTests):
    def setUp(self):
        super().setUp()
        def prepare(instance, report):
            instance.launcher_backup().write_bytes(b"original launcher backup")
            instance.path.with_name("launcher-carlink.apk").write_bytes(b"pinned CarLink launcher")
            return {"backup_verified": True}
        p = patch.object(trial.Trial, "prepare_carlink_launcher", prepare)
        p.start(); self.addCleanup(p.stop)
        p = patch.object(trial.Trial, "verify_carlink_launcher", lambda self, path: Path(path))
        p.start(); self.addCleanup(p.stop)

    def ready(self):
        car = PromotionADB()
        self.start(car)
        trial.run(core, car, self.state, "carlink-fullscreen")
        return car

    def promote(self, car):
        return trial.run(core, car, self.state, "carlink-promote", verify_reboot=True)

    def test_promotion_and_return_to_previous_launcher_are_journaled(self):
        car = self.ready()
        result = self.promote(car)
        self.assertEqual("carlink_configured", result["status"])
        self.assertEqual("carlink", result["primary_receiver"])
        self.assertTrue(result["carlink_launcher_reboot_verified"])
        self.assertEqual(2, car.writes.count("reboot"))
        self.assertEqual("carlink", result["launcher"]["build"])
        # Original AA acceptance is deliberately unchanged.
        self.assertFalse(core.inspect(car)["recovery_eligible"])
        self.assertEqual("carlink_configured", trial.run(core, car, self.state, "carlink-check")["status"])
        self.assertEqual("restored", self.restore(car)["status"])
        self.assertEqual("openhu", core.launcher_state(car)["build"])
        self.assertEqual(-1, car.carlink_layout)
        self.assertLess(car.writes.index("return_launcher"), car.writes.index("carlink_remove"))
        self.assertNotIn("launcher_restore", car.writes)
        self.assertFalse(any('uninstall' in str(cmd) and 'com.chinatsp.launcher' in str(cmd) for cmd in car.commands))

    def test_promotion_install_lost_connection_uses_original_backup_on_restore(self):
        car = self.ready()
        car.fail_at, car.fail_after_effect = "promote_launcher", True
        with self.assertRaises(core.SetupError):
            self.promote(car)
        car.disconnected, car.fail_at = False, None
        self.assertEqual("restored", self.restore(car)["status"])
        self.assertEqual(1, car.writes.count("promote_launcher"))
        self.assertEqual(1, car.writes.count("return_launcher"))

    def test_uncertain_return_does_not_repeat_launcher_install(self):
        car = self.ready()
        self.promote(car)
        car.fail_at, car.fail_after_effect = "return_launcher", True
        with self.assertRaises(core.SetupError):
            self.restore(car)
        car.disconnected, car.fail_at = False, None
        self.assertEqual("restored", self.restore(car)["status"])
        self.assertEqual(1, car.writes.count("return_launcher"))

    def test_unknown_replacement_launcher_is_never_overwritten(self):
        car = self.ready()
        self.promote(car)
        car.hashes[car.paths[core.PROFILE["launcher"]["package"]]] = "e" * 64
        before = car.writes[:]
        with self.assertRaises(core.SetupError):
            self.restore(car)
        self.assertEqual(before, car.writes)

    def test_cannot_promote_without_fullscreen(self):
        car = PromotionADB()
        self.start(car)
        before = car.writes[:]
        with self.assertRaises(core.SetupError):
            self.promote(car)
        self.assertEqual(before, car.writes)


class CarLinkTests(DeviceFixture):
    def setUp(self):
        super().setUp()
        p = patch.object(trial, "DEFAULT_PIN", trial.PIN)
        p.start()
        self.addCleanup(p.stop)
        patcher = patch.object(trial, "obtain_apk", return_value=Path("pinned-carlink.apk"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_trial(self, car, command="carlink-trial", reboot=False):
        return trial.run(core, car, self.state, command, verify_reboot=reboot)

    def journal(self, car):
        return trial.Trial(core, car, self.state).load()

    def test_fullscreen_owns_only_carlink_key_and_restore_uses_factory_default(self):
        car = TrialADB()
        self.run_trial(car, reboot=True)
        result = self.run_trial(car, "carlink-fullscreen")
        self.assertEqual("fullscreen_ready", result["status"])
        self.assertEqual(0, car.carlink_layout)
        self.assertEqual(0, car.layout)
        self.assertFalse(result["fullscreen_phone_tested"])
        self.assertFalse(result["fullscreen_reboot_tested"])
        self.assertTrue(trial.journal_path(core, car, self.state).with_name(
            "systemui-prefs-before-carlink-fullscreen.xml").exists())
        self.assertEqual("restored", self.run_trial(car, "carlink-restore")["status"])
        self.assertEqual(-1, car.carlink_layout)
        self.assertEqual(0, car.layout)
        self.assertNotIn("layout", car.writes)
        self.assertNotIn("launcher_install", car.writes)

    def test_fullscreen_restores_exact_preexisting_value(self):
        car = TrialADB()
        car.carlink_layout = 2
        self.run_trial(car)
        self.run_trial(car, "carlink-fullscreen")
        self.run_trial(car, "carlink-restore")
        self.assertEqual(2, car.carlink_layout)

    def test_fullscreen_failure_restores_layout_and_keeps_working_trial(self):
        car = TrialADB()
        self.run_trial(car)
        car.dead_packages.add(core.SYSTEMUI)
        with self.assertRaises(core.SetupError):
            self.run_trial(car, "carlink-fullscreen")
        self.assertEqual("recovery_required", self.journal(car)["phase"])
        self.assertEqual(-1, car.carlink_layout)
        self.assertTrue(car.packages[trial.PIN["package"]]["installed"])
        car.dead_packages.clear()
        self.assertEqual("restored", self.run_trial(car, "carlink-restore")["status"])

    def test_uncertain_fullscreen_write_recovers_with_original_journal(self):
        car = TrialADB()
        self.run_trial(car)
        car.fail_at, car.fail_after_effect = "carlink_layout", True
        with self.assertRaises(core.SetupError):
            self.run_trial(car, "carlink-fullscreen")
        car.fail_at, car.disconnected = None, False
        self.assertEqual("restored", self.run_trial(car, "carlink-restore")["status"])
        self.assertEqual(-1, car.carlink_layout)
        self.assertEqual(0, car.layout)

    def test_unknown_app_or_firmware_cannot_get_fullscreen_writes(self):
        car = TrialADB()
        self.run_trial(car)
        car.hashes[car.paths[trial.PIN["package"]]] = "f" * 64
        before = car.writes[:]
        with self.assertRaises(core.SetupError):
            self.run_trial(car, "carlink-fullscreen")
        self.assertEqual(before, car.writes)

    def test_corrupt_fullscreen_baseline_is_refused(self):
        car = TrialADB()
        self.run_trial(car)
        self.run_trial(car, "carlink-fullscreen")
        path = trial.journal_path(core, car, self.state)
        journal = json.loads(path.read_text())
        journal["carlink_fullscreen_original"] = True
        path.write_text(json.dumps(journal))
        before = car.writes[:]
        with self.assertRaises(core.SetupError):
            self.run_trial(car, "carlink-restore")
        self.assertEqual(before, car.writes)

    def test_read_only_preflight_and_exact_trial_isolation(self):
        car = TrialADB()
        original = core.inspect(car)
        self.assertEqual("trial_eligible", self.run_trial(car, "carlink-check")["status"])
        self.assertEqual([], car.writes)
        self.assertFalse(self.state.exists())
        result = self.run_trial(car, reboot=True)
        self.assertEqual("trial_ready", result["status"])
        self.assertEqual("phone_handoff", result["next_action"])
        self.assertFalse(result["projection_tested"])
        self.assertTrue(result["android_reboot_verified"])
        self.assertEqual(3, car.packages[core.RECEIVER]["enabled"])
        self.assertTrue(car.packages[core.RECEIVER]["installed"])
        self.assertEqual(0, car.packages[trial.PIN["package"]]["enabled"])
        after = core.inspect(car)
        for key in ("launcher", "carauto", "fullscreen_value"):
            self.assertEqual(original[key], after[key])
        self.assertFalse(after["setup_compatible"])
        self.assertEqual("trial_eligible", self.run_trial(car, "carlink-check")["status"])
        self.assertFalse(core.backup_path(car, self.state).exists())
        self.assertFalse({"carauto", "layout", "refresh", "launcher_install", "launcher_restore"}.intersection(car.writes))

    def test_backup_precedes_first_device_write_and_aa_backup_is_untouched(self):
        car = TrialADB()
        car.select_usb()
        old = core.backup_path(car, self.state)
        old.parent.mkdir(parents=True)
        old.write_text("original AA journal bytes")
        def verify_before_write(name):
            self.assertTrue(trial.journal_path(core, car, self.state).is_file())
            self.assertEqual(0, self.journal(car)["original"]["receiver"]["enabled"])
        car.on_write = verify_before_write
        self.run_trial(car)
        self.run_trial(car, "carlink-restore")
        self.assertEqual("original AA journal bytes", old.read_text())

    def test_restore_preserves_old_app_data_scope_and_exact_enabled_state(self):
        for enabled in (0, 1):
            with self.subTest(enabled=enabled):
                self.state = self.state / str(enabled)
                car = TrialADB(enabled)
                self.run_trial(car)
                self.assertEqual("restored", self.run_trial(car, "carlink-restore")["status"])
                self.assertEqual(enabled, car.packages[core.RECEIVER]["enabled"])
                self.assertTrue(car.packages[core.RECEIVER]["installed"])
                self.assertFalse(car.packages[trial.PIN["package"]]["installed"])
                before = car.writes[:]
                self.assertEqual("already_restored", self.run_trial(car, "carlink-restore")["status"])
                self.assertEqual(before, car.writes)
                self.assertNotIn("uninstall", car.writes)

    def test_every_unknown_identity_and_unowned_receiver_blocks_before_writes(self):
        changes = [lambda car: car.props.update({"ro.build.display.id": "unknown"}),
                   lambda car: car.hashes.update({car.paths[core.RECEIVER]: "a" * 64}),
                   lambda car: car.hashes.update({core.PROFILE["launcher"]["path"]: "b" * 64}),
                   lambda car: car.packages[core.RECEIVER].update(enabled=3),
                   lambda car: car.packages[core.CARAUTO].update(enabled=0),
                   lambda car: car.props.update(OTG_MODE="2"),
                   lambda car: setattr(car, "root", False)]
        for change in changes:
            with self.subTest(change=change):
                car = TrialADB()
                change(car)
                with self.assertRaises(core.SetupError):
                    self.run_trial(car)
                self.assertEqual([], car.writes)

    def test_existing_carlink_including_another_user_is_never_adopted(self):
        for installed in (False, True):
            with self.subTest(installed=installed):
                car = TrialADB()
                car.global_carlink = True
                car.packages[trial.PIN["package"]]["installed"] = installed
                with self.assertRaises(core.SetupError):
                    self.run_trial(car)
                self.assertEqual([], car.writes)

    def test_wrong_local_apk_refused(self):
        path = self.state.parent / "wrong.apk"
        path.write_bytes(b"untrusted")
        with self.assertRaises(core.SetupError):
            trial.verify_apk(core, path)

    def test_visible_permission_pause_resumes_without_reinstalling(self):
        car = TrialADB()
        car.carlink_permission = True
        result = trial.run(core, car, self.state, "carlink-trial")
        self.assertEqual("waiting_for_permissions", result["status"])
        self.assertIn("CarLink", result["message"])
        original = copy.deepcopy(self.journal(car)["original"])
        car.carlink_permission = False
        self.assertEqual("trial_ready", self.run_trial(car)["status"])
        self.assertEqual(1, car.writes.count("carlink_install"))
        self.assertEqual(original, self.journal(car)["original"])

    def test_failure_after_pause_effect_recovers_original_and_new_app_only(self):
        car = TrialADB()
        car.fail_at, car.fail_after_effect = "pause_openhu", True
        car.disconnect_on_failure = False
        with self.assertRaises(core.SetupError) as caught:
            self.run_trial(car)
        self.assertEqual("restored", caught.exception.details["recovery"]["status"])
        self.assertEqual(0, car.packages[core.RECEIVER]["enabled"])
        self.assertFalse(car.packages[trial.PIN["package"]]["installed"])

    def test_install_rejection_does_not_pause_or_remove_the_old_receiver(self):
        car = TrialADB()
        car.fail_at = "carlink_install"
        car.disconnect_on_failure = False
        with self.assertRaises(core.SetupError) as caught:
            self.run_trial(car, reboot=True)
        self.assertEqual("restored", caught.exception.details["recovery"]["status"])
        self.assertNotIn("pause_openhu", car.writes)
        self.assertNotIn("reboot", car.writes)
        self.assertTrue(car.packages[core.RECEIVER]["installed"])
        self.assertEqual(0, car.packages[core.RECEIVER]["enabled"])

    def test_completed_official_failure_journal_stays_readable_but_unfinished_is_refused(self):
        car = TrialADB()
        self.run_trial(car)
        self.run_trial(car, "carlink-restore")
        p = trial.journal_path(core, car, self.state)
        j = json.loads(p.read_text())
        j["apk_sha256"] = trial.BASE_PIN["sha256"]
        p.write_text(json.dumps(j))
        self.assertTrue(self.journal(car)["restored"])
        j["restored"] = False
        p.write_text(json.dumps(j))
        with self.assertRaises(core.SetupError):
            self.journal(car)

    def test_uncertain_install_and_lost_usb_need_restore_without_second_install(self):
        car = TrialADB()
        car.fail_at, car.fail_after_effect = "carlink_install", True
        with self.assertRaises(core.SetupError) as caught:
            self.run_trial(car)
        self.assertEqual("recovery_required", caught.exception.details["recovery"]["status"])
        car.disconnected, car.fail_at = False, None
        check = self.run_trial(car, "carlink-check")
        self.assertFalse(check["trial_eligible"])
        self.assertEqual("carlink_restore", check["next_action"])
        with self.assertRaises(core.SetupError):
            self.run_trial(car)
        self.assertEqual("restored", self.run_trial(car, "carlink-restore")["status"])
        self.assertEqual(1, car.writes.count("carlink_install"))

    def test_permission_after_observed_reboot_does_not_reboot_twice(self):
        car = TrialADB()
        def permission_after_reboot(name):
            if name == "reboot":
                car.carlink_permission = True
        car.on_write = permission_after_reboot
        result = self.run_trial(car, reboot=True)
        self.assertEqual("waiting_for_permissions", result["status"])
        self.assertFalse(result["android_reboot_verified"])
        car.on_write, car.carlink_permission = None, False
        self.assertTrue(self.run_trial(car, reboot=True)["android_reboot_verified"])
        self.assertEqual(1, car.writes.count("reboot"))

    def test_failure_to_return_from_reboot_never_claims_handoff(self):
        car = TrialADB()
        car.reboot_returns = False
        with self.assertRaises(core.SetupError) as caught:
            self.run_trial(car, reboot=True)
        self.assertEqual("recovery_required", caught.exception.details["recovery"]["status"])
        self.assertFalse(self.journal(car)["android_reboot_verified"])

    def test_firmware_change_after_pause_blocks_all_recovery_writes(self):
        car = TrialADB()
        def mismatch(name):
            if name == "pause_openhu":
                car.props["ro.build.display.id"] = "unknown"
                raise core.SetupError("firmware changed")
        car.on_write = mismatch
        with self.assertRaises(core.SetupError) as caught:
            self.run_trial(car)
        self.assertEqual("recovery_required", caught.exception.details["recovery"]["status"])
        self.assertNotIn("carlink_remove", car.writes)
        self.assertNotIn("restore_openhu", car.writes)

    def test_crash_during_install_is_not_hidden_by_the_launch_baseline(self):
        car = TrialADB()
        original = car.mutate
        def crash_after_effect(name, effect):
            original(name, effect)
            if name == "carlink_install":
                car.log_output += "\nProcess: com.carlink.app, PID: 9000"
        car.mutate = crash_after_effect
        with self.assertRaises(core.SetupError) as caught:
            self.run_trial(car)
        self.assertEqual("restored", caught.exception.details["recovery"]["status"])

    def test_uncertain_user_scoped_uninstall_is_read_back_not_repeated(self):
        car = TrialADB()
        self.run_trial(car)
        car.fail_at, car.fail_after_effect = "carlink_remove", True
        with self.assertRaises(core.SetupError):
            self.run_trial(car, "carlink-restore")
        car.disconnected, car.fail_at = False, None
        self.assertEqual("restored", self.run_trial(car, "carlink-restore")["status"])
        self.assertEqual(1, car.writes.count("carlink_remove"))

    def test_unknown_carlink_replacement_is_never_removed(self):
        car = TrialADB()
        self.run_trial(car)
        car.hashes[car.paths[trial.PIN["package"]]] = "a" * 64
        before = car.writes[:]
        with self.assertRaises(core.SetupError):
            self.run_trial(car, "carlink-restore")
        self.assertEqual(before, car.writes)
        self.assertTrue(car.packages[trial.PIN["package"]]["installed"])

    def test_unknown_old_receiver_retains_carlink_during_recovery(self):
        car = TrialADB()
        self.run_trial(car)
        car.hashes[car.paths[core.RECEIVER]] = "b" * 64
        with self.assertRaises(core.SetupError):
            self.run_trial(car, "carlink-restore")
        self.assertNotIn("carlink_remove", car.writes)
        self.assertTrue(car.packages[trial.PIN["package"]]["installed"])

    def test_fresh_carlink_crash_rolls_back_without_touching_factory_components(self):
        car = TrialADB()
        def crash(name):
            if name == "launch" and car.packages[core.RECEIVER]["enabled"] == 3:
                car.log_output += "\nProcess: com.carlink.app, PID: 5000"
        car.on_write = crash
        with self.assertRaises(core.SetupError) as caught:
            self.run_trial(car)
        self.assertEqual("restored", caught.exception.details["recovery"]["status"])
        self.assertEqual(0, car.packages[core.RECEIVER]["enabled"])

    def test_active_trial_blocks_old_aa_restore_without_overwriting_journals(self):
        car = TrialADB()
        self.run_trial(car)
        before = car.writes[:]
        with self.assertRaisesRegex(core.SetupError, "carlink-restore"):
            core.restore(car, self.state)
        self.assertEqual(before, car.writes)

    def test_corrupt_journal_and_wrong_usb_are_refused(self):
        car = TrialADB()
        self.run_trial(car)
        p = trial.journal_path(core, car, self.state)
        j = json.loads(p.read_text())
        j["original"]["receiver"]["enabled"] = True
        p.write_text(json.dumps(j))
        before = car.writes[:]
        with self.assertRaises(core.SetupError):
            self.run_trial(car, "carlink-restore")
        self.assertEqual(before, car.writes)
        other = TrialADB()
        other.listing = "192.0.2.1:5555 device model:F202_MCA\n"
        with self.assertRaises(core.SetupError):
            self.run_trial(other, "carlink-check")
        self.assertEqual([], other.writes)
