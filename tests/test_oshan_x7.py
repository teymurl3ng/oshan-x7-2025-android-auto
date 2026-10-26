"""Offline safety and recovery tests. No car, network, or real ADB is used."""

import contextlib
import copy
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import oshan_x7 as tool


class FakeADB(tool.ADB):
    """Stateful Android simulator; unrecognized commands fail the test."""

    def __init__(self, receiver=False, enabled=0, layout=None):
        super().__init__()
        self.listing = "CAR device usb:1-1 product:full_spm8666p1_64 model:F202_MCA\n"
        self.props = copy.deepcopy(tool.PROFILE["properties"])
        self.props["OTG_MODE"] = "1"
        self.size = "Physical size: 1920x720"
        self.root = True
        self.booted = "1"
        self.user = "0"
        self.packages = {
            name: {"installed": True, "enabled": 0}
            for name in tool.PROFILE["required_packages"] + ["com.chinatsp.launcher"]
        }
        self.packages[tool.CARAUTO]["enabled"] = enabled
        self.packages[tool.RECEIVER] = {"installed": receiver, "enabled": 0,
                                       "version_code": 119, "version_name": "3.5.0"}
        self.paths = {"com.chinatsp.launcher": tool.PROFILE["launcher"]["path"],
                      tool.RECEIVER: "/data/app/com.andrerinas.headunitrevived-abc==/base.apk"}
        self.hashes = {self.paths["com.chinatsp.launcher"]: tool.PROFILE["launcher"]["sha256"],
                       self.paths[tool.RECEIVER]: tool.PROFILE["receiver"]["sha256"]}
        self.layout = layout
        self.writes = []
        self.commands = []
        self.fail_at = None
        self.fail_after_effect = False
        self.on_write = None
        self.persist_layout = True

    def xml(self):
        item = "" if self.layout is None else f'<int name="{tool.RECEIVER}" value="{self.layout}" />'
        return f'<map><int name="unrelated.key" value="40" />{item}</map>'

    def mutate(self, name, effect):
        if self.on_write:
            self.on_write(name)
        self.writes.append(name)
        if self.fail_at == name and not self.fail_after_effect:
            raise tool.SetupError("simulated cable loss")
        effect()
        if self.fail_at == name:
            raise tool.SetupError("simulated cable loss after uncertain completion")

    def run(self, *args, target=True, timeout=30, allow_failure=False):
        self.commands.append(args)
        if args == ("devices", "-l"):
            return subprocess.CompletedProcess(args, 0, "List of devices attached\n" + self.listing, "")
        if args[0] == "install":
            assert args[1:3] == ("--user", "0")
            def effect():
                self.packages[tool.RECEIVER]["installed"] = True
            self.mutate("install", effect)
            return subprocess.CompletedProcess(args, 0, "Success\n", "")
        if args[0] != "shell":
            raise AssertionError(f"Unexpected ADB command: {args}")
        words = shlex.split(args[1])
        root = words[:2] == ["su", "0"]
        if root:
            words = words[2:]
        text = self.respond(words, root)
        return subprocess.CompletedProcess(args, 0, text, "")

    def respond(self, words, root):
        if words == ["getprop"]:
            return "\n".join(f"[{key}]: [{value}]" for key, value in self.props.items())
        if words == ["getprop", "sys.boot_completed"]:
            return self.booted
        if words == ["wm", "size"]:
            return self.size
        if words == ["am", "get-current-user"]:
            return self.user
        if words[:2] == ["dumpsys", "package"]:
            state = self.packages.get(words[2], {"installed": False})
            if not state["installed"]:
                return "Unable to find package"
            return (f'versionCode={state.get("version_code", 1)} minSdk=16\n'
                    f'versionName={state.get("version_name", "factory")}\n'
                    f'User 0: installed=true hidden=false stopped=false enabled={state["enabled"]}\n')
        if words[:4] == ["pm", "path", "--user", "0"]:
            return "package:" + self.paths[words[4]]
        if words[0] == "sha256sum":
            return self.hashes[words[1]] + "  " + words[1]
        if words == ["id"] and root:
            return "uid=0(root) gid=0(root)" if self.root else "uid=2000(shell) gid=2000(shell)"
        if words == ["cat", tool.PREFS] and root:
            return self.xml()
        if words[:2] == ["am", "broadcast"] and root:
            action = words[words.index("-a") + 1]
            if action == "com.chinatsp.systemui.ACTION_APP_INFO":
                value = int(words[-1])
                def effect():
                    if self.persist_layout:
                        self.layout = value
                self.mutate("layout", effect)
            elif action == "com.chinatsp.activity.onpostresume":
                self.mutate("refresh", lambda: None)
            else:
                raise AssertionError(f"Unexpected broadcast: {words}")
            return "Broadcast completed: result=0"
        if words[:2] == ["am", "start"]:
            self.mutate("launch", lambda: None)
            return "Starting: Intent"
        if words[:2] == ["pm", "uninstall"] and root and words[-1] == tool.RECEIVER:
            def effect():
                self.packages[tool.RECEIVER]["installed"] = False
            self.mutate("uninstall", effect)
            return "Success"
        if words[0] == "pm" and root and words[1] in tool.ENABLE_COMMANDS.values():
            assert words[-1] == tool.CARAUTO
            state = next(k for k, v in tool.ENABLE_COMMANDS.items() if v == words[1])
            self.mutate("carauto", lambda: self.packages[tool.CARAUTO].update(enabled=state))
            return "new state"
        raise AssertionError(f"Unexpected shell command: {words}, root={root}")


class DeviceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / "state"
        # Download logic and artifact verification have separate tests.
        self.downloader = patch.object(tool, "obtain_apk", return_value=Path("pinned.apk"))
        self.downloader.start()
        self.addCleanup(self.downloader.stop)

    def setup_car(self, car):
        return tool.setup(car, self.state, tool.inspect(car))

    def restore_car(self, car):
        return tool.restore(car, self.state, tool.inspect(car))

    def test_matching_firmware_check_is_read_only(self):
        car = FakeADB()
        report = tool.inspect(car)
        self.assertTrue(report["compatible"])
        self.assertEqual([], car.writes)
        self.assertFalse(self.state.exists())

    def test_every_profile_property_is_a_gate(self):
        for key in tool.PROFILE["properties"]:
            with self.subTest(property=key):
                car = FakeADB()
                car.props[key] = "unknown"
                report = tool.inspect(car)
                self.assertFalse(report["compatible"])
                with self.assertRaises(tool.SetupError):
                    tool.setup(car, self.state, report)
                self.assertEqual([], car.writes)
                self.assertFalse(any("su 0" in str(x) for x in car.commands))
                self.assertFalse(self.state.exists())

    def test_model_match_cannot_override_firmware_mismatch(self):
        car = FakeADB()
        car.props["ro.build.display.id"] = "F202RHD_D1_OTHER"
        self.assertFalse(tool.inspect(car)["compatible"])

    def test_original_launcher_hash_is_required(self):
        car = FakeADB()
        car.hashes[car.paths["com.chinatsp.launcher"]] = "0" * 64
        self.assertFalse(tool.inspect(car)["compatible"])
        self.assertEqual([], car.writes)

    def test_wrong_display_and_overrides_are_rejected(self):
        for size in ("Physical size: 1280x720", "Physical size: 1920x720\nOverride size: 1280x720"):
            car = FakeADB()
            car.size = size
            self.assertFalse(tool.inspect(car)["compatible"])

    def test_boot_user_and_required_packages_are_checked(self):
        for attr, value in (("booted", "0"), ("user", "10")):
            car = FakeADB()
            setattr(car, attr, value)
            self.assertFalse(tool.inspect(car)["compatible"])
        car = FakeADB()
        car.packages[tool.CARAUTO]["installed"] = False
        self.assertFalse(tool.inspect(car)["compatible"])

    def test_no_root_refuses_without_mutation(self):
        car = FakeADB()
        car.root = False
        with self.assertRaises(tool.SetupError):
            self.setup_car(car)
        self.assertEqual([], car.writes)

    def test_offline_unauthorized_network_and_emulator_rejected(self):
        for line in ("CAR offline usb:1-1", "CAR unauthorized usb:1-1",
                     "10.0.0.2:5555 device model:F202_MCA", "emulator-5554 device model:F202_MCA"):
            with self.subTest(line=line):
                car = FakeADB()
                car.listing = line
                with self.assertRaises(tool.SetupError):
                    tool.inspect(car)
                car.serial = line.split()[0]
                with self.assertRaises(tool.SetupError):
                    tool.inspect(car)
                self.assertEqual([], car.writes)

    def test_multiple_usb_devices_require_explicit_serial(self):
        car = FakeADB()
        car.listing += "PHONE device usb:1-2 model:Phone\n"
        with self.assertRaises(tool.SetupError):
            tool.inspect(car)
        car.serial = "CAR"
        self.assertTrue(tool.inspect(car)["compatible"])

    def test_other_receiver_version_or_hash_is_never_overwritten(self):
        for change in ("version", "hash", "disabled"):
            car = FakeADB(receiver=True)
            if change == "version":
                car.packages[tool.RECEIVER]["version_code"] = 120
            elif change == "hash":
                car.hashes[car.paths[tool.RECEIVER]] = "1" * 64
            else:
                car.packages[tool.RECEIVER]["enabled"] = 3
            with self.assertRaises(tool.SetupError):
                self.setup_car(car)
            self.assertEqual([], car.writes)

    def test_fresh_setup_preserves_backup_before_first_mutation(self):
        car = FakeADB()
        def verify_backup(name):
            path = tool.backup_path(car, self.state)
            journal = json.loads(path.read_text())
            self.assertEqual(0, journal["original"]["carauto"]["enabled"])
            self.assertIsNone(journal["original"]["fullscreen_value"])
            self.assertFalse(journal["original"]["receiver"]["installed"])
            self.assertTrue((path.parent / "systemui-prefs-before.xml").exists())
            self.assertFalse(journal["operations"][-1]["complete"])
        car.on_write = verify_backup
        result = self.setup_car(car)
        self.assertEqual("configured", result["status"])
        self.assertEqual(["install", "carauto", "layout", "launch", "refresh"], car.writes)
        self.assertEqual(3, car.packages[tool.CARAUTO]["enabled"])
        self.assertEqual(0, car.layout)
        self.assertTrue(car.packages[tool.RECEIVER]["installed"])
        self.assertFalse(result["projection_tested"])
        self.assertEqual("1", car.props["OTG_MODE"])  # Port role was not changed.

    def test_repeated_setup_does_not_write_or_replace_backup(self):
        car = FakeADB()
        self.setup_car(car)
        path = tool.backup_path(car, self.state)
        first = path.read_bytes()
        writes = car.writes[:]
        result = self.setup_car(car)
        self.assertEqual("already_configured", result["status"])
        self.assertEqual(writes, car.writes)
        self.assertEqual(first, path.read_bytes())

    def test_restore_original_state_and_remove_only_new_receiver(self):
        car = FakeADB()
        self.setup_car(car)
        result = self.restore_car(car)
        self.assertEqual("restored", result["status"])
        self.assertEqual(0, car.packages[tool.CARAUTO]["enabled"])
        self.assertEqual(-1, car.layout)
        self.assertFalse(car.packages[tool.RECEIVER]["installed"])
        writes = car.writes[:]
        self.assertEqual("already_restored", self.restore_car(car)["status"])
        self.assertEqual(writes, car.writes)

    def test_restore_keeps_preexisting_receiver_and_nondefault_settings(self):
        car = FakeADB(receiver=True, enabled=1, layout=2)
        self.setup_car(car)
        self.restore_car(car)
        self.assertNotIn("install", car.writes)
        self.assertNotIn("uninstall", car.writes)
        self.assertTrue(car.packages[tool.RECEIVER]["installed"])
        self.assertEqual(1, car.packages[tool.CARAUTO]["enabled"])
        self.assertEqual(2, car.layout)

    def test_already_disabled_carauto_stays_disabled_on_restore(self):
        car = FakeADB(receiver=True, enabled=3)
        self.setup_car(car)
        self.restore_car(car)
        self.assertEqual(3, car.packages[tool.CARAUTO]["enabled"])

    def test_interrupted_setup_requires_restore_and_retains_original(self):
        car = FakeADB()
        car.fail_at = "carauto"
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(tool.SetupError):
            self.setup_car(car)
        self.assertTrue(car.packages[tool.RECEIVER]["installed"])
        with self.assertRaises(tool.SetupError):
            self.setup_car(car)
        car.fail_at = None
        self.restore_car(car)
        self.assertFalse(car.packages[tool.RECEIVER]["installed"])
        self.assertEqual(0, car.packages[tool.CARAUTO]["enabled"])

    def test_uncertain_install_completion_can_be_restored(self):
        car = FakeADB()
        car.fail_at, car.fail_after_effect = "install", True
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(tool.SetupError):
            self.setup_car(car)
        self.assertTrue(car.packages[tool.RECEIVER]["installed"])
        car.fail_at = None
        self.restore_car(car)
        self.assertFalse(car.packages[tool.RECEIVER]["installed"])

    def test_interrupted_restore_can_be_retried(self):
        car = FakeADB(receiver=True)
        self.setup_car(car)
        car.fail_at = "carauto"
        with self.assertRaises(tool.SetupError):
            self.restore_car(car)
        car.fail_at = None
        self.assertEqual("restored", self.restore_car(car)["status"])
        self.assertEqual(0, car.packages[tool.CARAUTO]["enabled"])

    def test_modified_backup_identity_refuses_restore(self):
        car = FakeADB()
        self.setup_car(car)
        path = tool.backup_path(car, self.state)
        journal = json.loads(path.read_text())
        journal["serial"] = "DIFFERENT_CAR"
        tool.write_json(path, journal)
        writes = car.writes[:]
        with self.assertRaises(tool.SetupError):
            self.restore_car(car)
        self.assertEqual(writes, car.writes)

    def test_missing_backup_never_changes_car(self):
        car = FakeADB()
        with self.assertRaises(tool.SetupError):
            self.restore_car(car)
        self.assertEqual([], car.writes)

    def test_firmware_change_prevents_restore_writes(self):
        car = FakeADB()
        self.setup_car(car)
        car.props["ro.build.display.id"] = "updated"
        writes = car.writes[:]
        with self.assertRaises(tool.SetupError):
            self.restore_car(car)
        self.assertEqual(writes, car.writes)

    def test_invalid_backup_types_prevent_restore_writes(self):
        car = FakeADB()
        self.setup_car(car)
        path = tool.backup_path(car, self.state)
        saved = json.loads(path.read_text())
        invalid = [[], {**saved, "original": []}, {**saved, "operations": ["bad"]},
                   {**saved, "restored": "false"}]
        for record in invalid:
            with self.subTest(record=record):
                tool.write_json(path, record)
                writes = car.writes[:]
                with self.assertRaises(tool.SetupError):
                    self.restore_car(car)
                self.assertEqual(writes, car.writes)

    def test_external_setting_change_does_not_destroy_baseline(self):
        car = FakeADB()
        self.setup_car(car)
        car.layout = 2
        writes = car.writes[:]
        with self.assertRaises(tool.SetupError):
            self.setup_car(car)
        self.assertEqual(writes, car.writes)

    def test_setup_after_restore_requires_new_cycle_directory(self):
        car = FakeADB()
        self.setup_car(car)
        self.restore_car(car)
        with self.assertRaises(tool.SetupError):
            self.setup_car(car)

    def test_broadcast_completion_without_persisted_value_is_failure(self):
        car = FakeADB(receiver=True)
        car.persist_layout = False
        with patch.object(tool.time, "sleep"), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(tool.SetupError):
                self.setup_car(car)
        journal = json.loads(tool.backup_path(car, self.state).read_text())
        self.assertEqual("fullscreen", journal["phase"])
        self.assertFalse(journal["operations"][-1]["complete"])

    def test_lock_prevents_parallel_setup(self):
        car = FakeADB()
        with tool.exclusive(self.state):
            with self.assertRaises(tool.SetupError):
                self.setup_car(car)
        self.assertEqual([], car.writes)


class ParsingAndCLITests(unittest.TestCase):
    def test_bad_xml_types_duplicates_and_out_of_range_refused(self):
        for xml in ("not XML", "<wrong/>", f'<map><string name="{tool.RECEIVER}">0</string></map>',
                    f'<map><int name="{tool.RECEIVER}" value="0"/><int name="{tool.RECEIVER}" value="2"/></map>',
                    f'<map><int name="{tool.RECEIVER}" value="no"/></map>',
                    f'<map><int name="{tool.RECEIVER}" value="2147483648"/></map>'):
            with self.subTest(xml=xml), self.assertRaises(tool.SetupError):
                tool.parse_layout(xml)

    def test_package_parser_uses_user_zero_only(self):
        self.assertFalse(tool.parse_package("User 10: installed=true enabled=0")["installed"])
        self.assertFalse(tool.parse_package("User 0: installed=false enabled=0")["installed"])
        with self.assertRaises(tool.SetupError):
            tool.parse_package("User 0: installed=true enabled=99")

    def test_json_check_emits_one_object_and_never_exposes_xml(self):
        car, output = FakeADB(), io.StringIO()
        with patch.object(tool, "ADB", return_value=car), contextlib.redirect_stdout(output):
            code = tool.main(["check", "--json"])
        result = json.loads(output.getvalue())
        self.assertEqual(0, code)
        self.assertTrue(result["ok"])
        self.assertNotIn("_prefs_xml", result)
        self.assertNotIn("serial", result)
        self.assertEqual([], car.writes)

    def test_json_failure_exit_code_and_no_writes(self):
        car, output = FakeADB(), io.StringIO()
        car.props["ro.product.model"] = "phone"
        with patch.object(tool, "ADB", return_value=car), contextlib.redirect_stdout(output):
            code = tool.main(["setup", "--json"])
        self.assertEqual(2, code)
        self.assertFalse(json.loads(output.getvalue())["ok"])
        self.assertEqual([], car.writes)

    def test_adb_uses_explicit_port_and_target_without_local_shell(self):
        adb = tool.ADB("/path with spaces/adb", 5038, "CAR")
        with patch.object(tool.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "ok", "")) as run:
            adb.shell("am", "broadcast", "--es", "packageName", tool.RECEIVER, root=True)
        command = run.call_args.args[0]
        self.assertEqual(["/path with spaces/adb", "-P", "5038", "-s", "CAR", "shell"], command[:6])
        self.assertTrue(command[-1].startswith("su 0 am broadcast"))
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_missing_adb_and_timeout_are_clear_errors(self):
        for error in (FileNotFoundError(), subprocess.TimeoutExpired("adb", 30)):
            with patch.object(tool.subprocess, "run", side_effect=error), self.assertRaises(tool.SetupError):
                tool.ADB(serial="CAR").run("shell", "id")

    def test_corrupt_artifact_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wrong.apk"
            path.write_bytes(b"not an APK")
            with self.assertRaises(tool.SetupError):
                tool.verify_apk(path)
            pinned = {**tool.PROFILE["receiver"], "bytes": path.stat().st_size}
            with patch.dict(tool.PROFILE, receiver=pinned), self.assertRaises(tool.SetupError):
                tool.verify_apk(path)

    def test_exact_artifact_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.apk"
            path.write_bytes(b"synthetic pinned artifact")
            pinned = {**tool.PROFILE["receiver"], "bytes": path.stat().st_size, "sha256": tool.digest(path)}
            with patch.dict(tool.PROFILE, receiver=pinned):
                self.assertEqual(path.resolve(), tool.verify_apk(path))

    def test_download_validates_pin_and_cleans_up_bad_bytes(self):
        class Response(io.BytesIO):
            def geturl(self):
                return "https://release-assets.githubusercontent.com/test"
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            with patch.object(tool.urllib.request, "urlopen", return_value=Response(b"bad download")):
                with self.assertRaises(tool.SetupError):
                    tool.obtain_apk(state)
            self.assertEqual([], list((state / "cache").iterdir()))

    def test_download_and_cached_artifact_use_same_verification(self):
        payload = b"synthetic pinned download"
        class Response(io.BytesIO):
            def geturl(self):
                return "https://release-assets.githubusercontent.com/test"
        import hashlib
        pinned = {**tool.PROFILE["receiver"], "bytes": len(payload),
                  "sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as folder, patch.dict(tool.PROFILE, receiver=pinned):
            state = Path(folder)
            with patch.object(tool.urllib.request, "urlopen", return_value=Response(payload)) as download:
                result = tool.obtain_apk(state)
                self.assertEqual(payload, result.read_bytes())
                self.assertEqual(result, tool.obtain_apk(state))
                self.assertEqual(1, download.call_count)
            result.write_bytes(b"corruption")
            with self.assertRaises(tool.SetupError):
                tool.obtain_apk(state)

    def test_download_size_limit_is_enforced(self):
        class Response(io.BytesIO):
            def geturl(self):
                return "https://release-assets.githubusercontent.com/test"
        with tempfile.TemporaryDirectory() as folder:
            pinned = {**tool.PROFILE["receiver"], "bytes": 3}
            with patch.dict(tool.PROFILE, receiver=pinned):
                with patch.object(tool.urllib.request, "urlopen", return_value=Response(b"too large")):
                    with self.assertRaises(tool.SetupError):
                        tool.obtain_apk(Path(folder))


if __name__ == "__main__":
    unittest.main()
