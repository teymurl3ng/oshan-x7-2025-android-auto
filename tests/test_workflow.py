"""Stage verification and unified recovery regressions; all device I/O is simulated."""
import contextlib
import copy
import io
import json
from unittest.mock import patch

import health_checks as health
import oshan_x7 as tool
from test_oshan_x7 import DeviceFixture, FakeADB


class WorkflowTests(DeviceFixture):
    def journal(self, car):
        return tool.load_backup(tool.backup_path(car, self.state), car)

    def test_zero_exit_activity_error_cannot_report_configured(self):
        car = FakeADB()
        car.start_errors[tool.MAIN_ACTIVITY] = "Error type 3\nError: Activity class does not exist."
        with self.assertRaises(tool.SetupError) as caught:
            self.setup_car(car)
        self.assertEqual("verify_receiver", caught.exception.details["failed_stage"])
        self.assertEqual("restored", caught.exception.details["recovery"]["status"])
        self.assertNotIn("carauto", car.writes)
        self.assertNotIn("launcher_install", car.writes)
        self.assertFalse(car.packages[tool.RECEIVER]["installed"])
        self.assertTrue(self.journal(car)["restored"])

    def test_launcher_crash_rolls_back_through_shared_restore_engine(self):
        car = FakeADB()
        original_xml = car.xml()
        def crash_after_install(name):
            if name == "home" and car.launcher_updated:
                car.log_output += "\n10-26 12:00:00 E AndroidRuntime: Process: com.chinatsp.launcher, PID: 1234"
        car.on_write = crash_after_install
        with self.assertRaises(tool.SetupError) as caught:
            self.setup_car(car)
        recovery = caught.exception.details["recovery"]
        self.assertEqual("restored", recovery["status"])
        self.assertFalse(car.launcher_updated)
        self.assertFalse(car.packages[tool.RECEIVER]["installed"])
        self.assertEqual(0, car.packages[tool.CARAUTO]["enabled"])
        journal = self.journal(car)
        self.assertEqual("install_launcher", journal["failed_stage"])
        self.assertTrue(journal["restored"])
        self.assertEqual(original_xml + "\n", (tool.backup_path(car, self.state).parent /
                         "systemui-prefs-before.xml").read_text())
        before = car.writes[:]
        self.assertEqual("already_restored", self.restore_car(car)["status"])
        self.assertEqual(before, car.writes)

    def test_permission_pause_has_distinct_exit_and_resumes_same_backup(self):
        car = FakeADB()
        car.permission_prompt = True
        output = io.StringIO()
        with patch.object(tool, "ADB", return_value=car), contextlib.redirect_stdout(output):
            code = tool.main(["setup", "--state-dir", str(self.state), "--json"])
        result = json.loads(output.getvalue())
        self.assertEqual(3, code)
        self.assertFalse(result["ok"])
        self.assertEqual("waiting_for_permissions", result["status"])
        original = copy.deepcopy(self.journal(car)["original"])
        self.assertNotIn("carauto", car.writes)
        self.assertNotIn("uninstall", car.writes)
        car.permission_prompt = False
        self.assertEqual("configured", self.setup_car(car)["status"])
        self.assertEqual(1, car.writes.count("install"))
        self.assertEqual(original, self.journal(car)["original"])
        self.restore_car(car)
        self.assertFalse(car.packages[tool.RECEIVER]["installed"])

    def test_disabled_exact_receiver_does_not_block_owned_launcher_recovery(self):
        car = FakeADB()
        self.setup_car(car)
        car.packages[tool.RECEIVER]["enabled"] = 3
        self.assertFalse(tool.inspect(car)["compatible"])
        self.assertTrue(tool.inspect(car, recovery=True)["recovery_eligible"])
        self.assertEqual("restored", self.restore_car(car)["status"])
        self.assertFalse(car.launcher_updated)
        self.assertFalse(car.packages[tool.RECEIVER]["installed"])

    def test_unknown_receiver_is_kept_while_other_owned_changes_are_recovered(self):
        car = FakeADB()
        self.setup_car(car)
        car.hashes[car.paths[tool.RECEIVER]] = "a" * 64
        with self.assertRaises(tool.SetupError) as caught:
            self.restore_car(car)
        self.assertFalse(car.launcher_updated)
        self.assertTrue(car.packages[tool.RECEIVER]["installed"])
        self.assertEqual(0, car.packages[tool.CARAUTO]["enabled"])
        self.assertIn("remove_receiver", caught.exception.details["recovery"]["errors"])
        self.assertEqual("recovery_required", self.journal(car)["phase"])
        car.hashes[car.paths[tool.RECEIVER]] = tool.PROFILE["receiver"]["sha256"]
        self.assertEqual("restored", self.restore_car(car)["status"])
        self.assertEqual(1, car.writes.count("launcher_restore"))

    def test_root_loss_does_not_block_standard_system_update_rollback(self):
        car = FakeADB()
        self.setup_car(car)
        original = copy.deepcopy(self.journal(car)["original"])
        car.root = False
        with self.assertRaises(tool.SetupError) as caught:
            self.restore_car(car)
        self.assertFalse(car.launcher_updated)
        errors = caught.exception.details["recovery"]["errors"]
        self.assertIn("restore_fullscreen", errors)
        self.assertIn("restore_carauto", errors)
        self.assertNotIn("uninstall", car.writes)
        self.assertFalse(self.journal(car)["restored"])
        self.assertEqual(original, self.journal(car)["original"])
        car.root = True
        self.assertEqual("restored", self.restore_car(car)["status"])
        self.assertEqual(1, car.writes.count("launcher_restore"))

    def test_bad_preferences_do_not_block_launcher_and_carauto_recovery(self):
        car = FakeADB()
        self.setup_car(car)
        xml = car.xml
        car.xml = lambda: "broken XML"
        with self.assertRaises(tool.SetupError) as caught:
            self.restore_car(car)
        self.assertFalse(car.launcher_updated)
        self.assertEqual(0, car.packages[tool.CARAUTO]["enabled"])
        self.assertIn("restore_fullscreen", caught.exception.details["recovery"]["errors"])
        car.xml = xml
        self.assertEqual("restored", self.restore_car(car)["status"])

    def test_identity_change_after_write_blocks_all_automatic_recovery_writes(self):
        car = FakeADB()
        def change_firmware(name):
            if name == "launcher_install":
                car.props["ro.build.display.id"] = "unknown"
        car.on_write = change_firmware
        with self.assertRaises(tool.SetupError) as caught:
            self.setup_car(car)
        self.assertEqual("recovery_required", caught.exception.details["recovery"]["status"])
        self.assertNotIn("launcher_restore", car.writes)
        self.assertNotIn("uninstall", car.writes)
        self.assertFalse(self.journal(car)["restored"])

    def test_cable_loss_defers_recovery_and_status_identifies_failed_stage(self):
        car = FakeADB()
        car.fail_at, car.fail_after_effect = "launcher_install", True
        with self.assertRaises(tool.SetupError) as caught:
            self.setup_car(car)
        self.assertEqual("recovery_required", caught.exception.details["recovery"]["status"])
        self.assertTrue(self.journal(car)["operations"])
        car.disconnected, car.fail_at = False, None
        output = io.StringIO()
        before = car.writes[:]
        with patch.object(tool, "ADB", return_value=car), contextlib.redirect_stdout(output):
            code = tool.main(["status", "--state-dir", str(self.state), "--json"])
        result = json.loads(output.getvalue())
        self.assertEqual(0, code)
        self.assertEqual("install_launcher", result["failed_stage"])
        self.assertEqual("restore", result["next_action"])
        self.assertEqual(before, car.writes)
        self.assertEqual("restored", self.restore_car(car)["status"])

    def test_recovery_keeps_receiver_when_factory_home_is_not_healthy(self):
        car = FakeADB()
        self.setup_car(car)
        car.dead_packages.add(tool.PROFILE["launcher"]["package"])
        with self.assertRaises(tool.SetupError):
            self.restore_car(car)
        self.assertFalse(car.launcher_updated)
        self.assertTrue(car.packages[tool.RECEIVER]["installed"])
        self.assertEqual(0, car.packages[tool.CARAUTO]["enabled"])
        car.dead_packages.clear()
        self.assertEqual("restored", self.restore_car(car)["status"])

    def test_health_requires_live_systemui_and_expected_foreground(self):
        car = FakeADB(receiver=True)
        for dead, activity in (({tool.SYSTEMUI}, tool.MAIN_ACTIVITY),
                               (set(), "other/.Activity")):
            with self.subTest(dead=dead, activity=activity):
                car.dead_packages = dead
                car.foreground = activity
                with self.assertRaises(health.HealthError):
                    health.observe(car, tool.RECEIVER, foreground=True)

    def test_crash_history_is_ignored_but_fresh_crash_anr_and_native_crash_are_detected(self):
        car = FakeADB(receiver=True)
        car.log_output = "old Process: com.andrerinas.headunitrevived, PID: 1000"
        car.foreground = tool.MAIN_ACTIVITY
        self.assertEqual(3, health.observe(car, tool.RECEIVER, foreground=True)["stable_samples"])
        for event in ("Process: com.andrerinas.headunitrevived, PID: 3000",
                      "am_anr: [0,3000,com.andrerinas.headunitrevived,123,reason]",
                      "am_crash: [0,3000,com.andrerinas.headunitrevived,123,reason]",
                      ">>> com.andrerinas.headunitrevived <<<"):
            with self.subTest(event=event):
                car.log_output = event
                with self.assertRaises(health.HealthError):
                    health.observe(car, tool.RECEIVER, baseline="", foreground=True)
        self.assertFalse(any("logcat -c" in str(c) for c in car.commands))

    def test_pid_restart_during_sampling_is_failure(self):
        car = FakeADB(receiver=True)
        original = car.respond
        count = 0
        def respond(words, root):
            nonlocal count
            if words == ["pidof", tool.RECEIVER]:
                count += 1
                return str(1000 + count)
            return original(words, root)
        car.respond = respond
        with self.assertRaises(health.HealthError):
            health.observe(car, tool.RECEIVER)

    def test_reboot_verifies_new_boot_id_and_state_and_does_not_repeat(self):
        car = FakeADB()
        result = tool.setup(car, self.state, tool.inspect(car), verify_reboot=True)
        self.assertTrue(result["android_reboot_verified"])
        self.assertEqual("phone_handoff", result["next_action"])
        self.assertEqual(1, car.writes.count("reboot"))
        before = car.writes[:]
        self.assertEqual("already_configured", tool.setup(car, self.state, tool.inspect(car),
                         verify_reboot=True)["status"])
        self.assertEqual(before, car.writes)
        self.assertEqual("1", car.props["OTG_MODE"])

    def test_reboot_check_can_extend_completed_setup(self):
        car = FakeADB()
        self.assertEqual("rerun_setup_with_reboot_check", self.setup_car(car)["next_action"])
        before = car.writes.count("launcher_install")
        result = tool.setup(car, self.state, tool.inspect(car), verify_reboot=True)
        self.assertTrue(result["android_reboot_verified"])
        self.assertEqual(before, car.writes.count("launcher_install"))

    def test_stalled_boot_attempts_recovery_without_claiming_reboot_success(self):
        car = FakeADB()
        car.reboot_returns = False
        with self.assertRaises(tool.SetupError) as caught:
            tool.setup(car, self.state, tool.inspect(car), verify_reboot=True)
        self.assertEqual("verify_android_reboot", caught.exception.details["failed_stage"])
        self.assertFalse(self.journal(car).get("android_reboot_verified", False))
        self.assertEqual("restored", caught.exception.details["recovery"]["status"])
        self.assertFalse(car.launcher_updated)
        self.assertLess(self.ticks, 150)

    def test_unrelated_events_do_not_blame_the_receiver(self):
        car = FakeADB(receiver=True)
        car.log_output = "Process: other.app, PID: 10\nam_anr: [0,10,other.app,123,reason]"
        result = health.observe(car, tool.RECEIVER, baseline="")
        self.assertFalse(result["fresh_crash_or_anr"])

    def test_grouped_and_rotated_logs_do_not_reclassify_old_crash(self):
        before = "old crash\nold event 1\nold event 2"
        after = "old crash\nold event 2\nnew event"
        self.assertEqual(["new event"], health.new_lines(before, after))
        self.assertEqual(["same event"], health.new_lines("same event", "same event\nsame event"))

    def test_exact_home_activity_accepts_full_name_and_rejects_another_launcher_screen(self):
        car = FakeADB()
        car.foreground = "com.chinatsp.launcher/com.chinatsp.launcher.MainAct"
        health.observe(car, "com.chinatsp.launcher", foreground=True,
                       expected_activity=tool.PROFILE["launcher"]["home"])
        car.foreground = "com.chinatsp.launcher/.OtherScreen"
        with self.assertRaises(health.HealthError):
            health.observe(car, "com.chinatsp.launcher", foreground=True,
                           expected_activity=tool.PROFILE["launcher"]["home"])

    def test_health_timeout_bounds_individual_adb_reads(self):
        car = FakeADB()
        reads = []
        original = car.run
        def run(*args, **kwargs):
            if args[0] == "shell":
                reads.append(kwargs.get("timeout"))
            return original(*args, **kwargs)
        car.run = run
        health.observe(car, tool.SYSTEMUI)
        self.assertTrue(reads)
        self.assertTrue(all(0 < timeout <= 5 for timeout in reads))

    def test_new_firmware_mismatch_is_caught_before_next_install_stage(self):
        car = FakeADB()
        def change_after_baseline(name):
            if name == "home":
                car.props["ro.build.display.id"] = "other"
        car.on_write = change_after_baseline
        with self.assertRaises(tool.SetupError):
            self.setup_car(car)
        self.assertEqual(["home"], car.writes)
        self.assertEqual("factory", self.journal(car)["original"]["launcher"]["build"])

    def test_restore_does_not_claim_unchanged_setting_as_owned(self):
        car = FakeADB(receiver=True, enabled=3, layout=0)
        self.setup_car(car)
        car.layout = 2
        self.restore_car(car)
        self.assertEqual(2, car.layout)
        self.assertNotIn("layout", car.writes)
        self.assertNotIn("carauto", car.writes)

    def test_status_keeps_journal_visible_on_identity_mismatch_without_writes(self):
        car = FakeADB()
        self.setup_car(car)
        car.props["ro.build.display.id"] = "other"
        before = car.writes[:]
        output = io.StringIO()
        with patch.object(tool, "ADB", return_value=car), contextlib.redirect_stdout(output):
            code = tool.main(["status", "--state-dir", str(self.state), "--json"])
        result = json.loads(output.getvalue())
        self.assertEqual(2, code)
        self.assertEqual("configured", result["backup_phase"])
        self.assertEqual("diagnose_identity_mismatch_no_writes", result["next_action"])
        self.assertEqual(before, car.writes)

    def test_invalid_boot_id_after_reboot_cannot_count_as_verified(self):
        car = FakeADB()
        original = car.respond
        def respond(words, root):
            if words == ["cat", "/proc/sys/kernel/random/boot_id"] and "reboot" in car.writes:
                return "permission denied"
            return original(words, root)
        car.respond = respond
        with self.assertRaises(tool.SetupError):
            tool.setup(car, self.state, tool.inspect(car), verify_reboot=True)
        self.assertFalse(self.journal(car).get("android_reboot_verified", False))

    def test_recovery_status_does_not_treat_broken_home_as_setup_compatible(self):
        car = FakeADB()
        self.setup_car(car)
        car.launcher_home = "No activity found"
        report = tool.inspect(car, recovery=True)
        self.assertTrue(report["recovery_eligible"])
        self.assertTrue(report["compatible"])
        self.assertFalse(report["setup_compatible"])
        self.assertTrue(report["component_issues"])

    def test_host_role_is_not_compatible_even_in_recovery_status(self):
        car = FakeADB()
        car.props["OTG_MODE"] = "2"
        for recovery in (False, True):
            report = tool.inspect(car, recovery=recovery)
            self.assertFalse(report["compatible"])
            self.assertFalse(report["recovery_eligible"])
        self.assertEqual([], car.writes)
