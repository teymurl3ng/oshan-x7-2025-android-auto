"""Launcher ownership, recovery and patch tests without a car or proprietary APK."""
import bz2
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import launcher_patch
import oshan_x7 as tool
from test_oshan_x7 import DeviceFixture, FakeADB


def integer(n):
    return (abs(n) | ((1 << 63) if n < 0 else 0)).to_bytes(8, "little")


def binary_patch(triples, diff=b"", extra=b"", size=None):
    control = bz2.compress(b"".join(integer(v) for t in triples for v in t))
    diff = bz2.compress(diff)
    extra = bz2.compress(extra)
    size = sum(x + y for x, y, z in triples) if size is None else size
    return b"BSDIFF40" + integer(len(control)) + integer(len(diff)) + integer(size) + control + diff + extra


class LauncherDeviceTests(DeviceFixture):
    def test_launcher_identity_and_immutable_base_remain_required_after_setup(self):
        car = FakeADB()
        self.setup_car(car)
        for change in ("factory", "update", "uid", "version", "home", "disabled", "flag"):
            with self.subTest(change=change):
                altered = copy.deepcopy(car)
                pin = tool.PROFILE["launcher"]
                if change == "factory": altered.hashes[pin["path"]] = "f" * 64
                if change == "update": altered.hashes[altered.paths[pin["package"]]] = "f" * 64
                if change == "uid": altered.launcher_uid = 1001
                if change == "version": altered.launcher_version += 1
                if change == "home": altered.launcher_home = "other/.Home"
                if change == "disabled": altered.packages[pin["package"]]["enabled"] = 3
                if change == "flag": altered.launcher_updated = False
                self.assertFalse(tool.inspect(altered)["compatible"])
                writes = altered.writes.copy()
                with self.assertRaises(tool.SetupError): self.restore_car(altered)
                self.assertEqual(writes, altered.writes)

    def test_restore_removes_owned_update_before_receiver_and_never_uninstalls_home_for_user(self):
        car = FakeADB()
        self.setup_car(car)
        car.writes.clear()
        self.restore_car(car)
        self.assertEqual("launcher_restore", car.writes[0])
        self.assertLess(car.writes.index("launcher_restore"), car.writes.index("uninstall"))
        self.assertEqual("factory", tool.launcher_state(car)["build"])
        self.assertTrue(any(cmd == ("shell", "pm uninstall -k com.chinatsp.launcher") for cmd in car.commands))
        self.assertFalse(any("--user" in str(c) and "uninstall" in str(c) and "com.chinatsp.launcher" in str(c)
                             for c in car.commands))

    def test_preexisting_exact_update_is_kept_and_never_claimed(self):
        car = FakeADB(receiver=True)
        car.run("install", "--no-streaming", "-r", "preexisting.apk")
        car.writes.clear()
        self.setup_car(car)
        self.assertNotIn("launcher_install", car.writes)
        self.restore_car(car)
        self.assertNotIn("launcher_restore", car.writes)
        self.assertEqual("openhu", tool.launcher_state(car)["build"])

    def test_install_disconnect_before_or_after_effect_is_recoverable(self):
        for uncertain in (False, True):
            with self.subTest(uncertain=uncertain), tempfile.TemporaryDirectory() as folder:
                state = Path(folder)
                car = FakeADB()
                car.fail_at, car.fail_after_effect = "launcher_install", uncertain
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(tool.SetupError):
                    tool.setup(car, state, tool.inspect(car))
                saved = tool.load_backup(tool.backup_path(car, state), car)
                self.assertEqual("install_launcher", saved["phase"])
                self.assertEqual("factory", saved["original"]["launcher"]["build"])
                car.fail_at = None
                writes = car.writes.copy()
                with self.assertRaises(tool.SetupError): tool.setup(car, state, tool.inspect(car))
                self.assertEqual(writes, car.writes)
                tool.restore(car, state, tool.inspect(car, recovery=True))
                self.assertEqual("factory", tool.launcher_state(car)["build"])

    def test_rollback_disconnect_after_effect_is_not_repeated(self):
        car = FakeADB()
        self.setup_car(car)
        car.fail_at, car.fail_after_effect = "launcher_restore", True
        with self.assertRaises(tool.SetupError): self.restore_car(car)
        self.assertEqual("factory", tool.launcher_state(car)["build"])
        car.fail_at = None
        self.restore_car(car)
        self.assertEqual(1, car.writes.count("launcher_restore"))

    def test_factory_change_after_install_prevents_rollback(self):
        car = FakeADB()
        self.setup_car(car)
        car.hashes[tool.PROFILE["launcher"]["path"]] = "0" * 64
        writes = car.writes.copy()
        with self.assertRaises(tool.SetupError): self.restore_car(car)
        self.assertEqual(writes, car.writes)

    def test_host_mode_refuses_both_setup_and_restore(self):
        car = FakeADB()
        car.props["OTG_MODE"] = "2"
        with self.assertRaises(tool.SetupError): self.setup_car(car)
        self.assertEqual([], car.writes)
        car.props["OTG_MODE"] = "1"
        self.setup_car(car)
        car.props["OTG_MODE"] = "2"
        writes = car.writes.copy()
        with self.assertRaises(tool.SetupError): self.restore_car(car)
        self.assertEqual(writes, car.writes)

    def test_missing_patch_refuses_before_first_device_write(self):
        car = FakeADB()
        with patch.object(tool, "prepare_launcher", side_effect=tool.SetupError("missing patch")):
            with self.assertRaises(tool.SetupError): self.setup_car(car)
        self.assertEqual([], car.writes)
        self.assertFalse(tool.backup_path(car, self.state).exists())

    def legacy_configured(self, car):
        self.setup_car(car)
        path = tool.backup_path(car, self.state)
        j = json.loads(path.read_text())
        j["schema"] = 1
        del j["original"]["launcher"]
        j["operations"] = [x for x in j["operations"] if x["name"] not in {"install_launcher", "open_launcher"}]
        tool.write_json(path, j)
        return path, j

    def test_legacy_cycle_upgrade_preserves_original_aa_settings(self):
        car = FakeADB()
        path, legacy = self.legacy_configured(car)
        car.shell("pm", "uninstall", "-k", "com.chinatsp.launcher")
        self.setup_car(car)
        upgraded = tool.load_backup(path, car)
        self.assertEqual(2, upgraded["schema"])
        for key in ("carauto", "receiver", "fullscreen_value"):
            self.assertEqual(legacy["original"][key], upgraded["original"][key])
        self.restore_car(car)
        self.assertFalse(car.packages[tool.RECEIVER]["installed"])
        self.assertEqual("factory", tool.launcher_state(car)["build"])

    def test_legacy_cycle_does_not_claim_externally_installed_launcher(self):
        car = FakeADB()
        path, legacy = self.legacy_configured(car)
        writes = car.writes.copy()
        self.assertEqual("already_configured", self.setup_car(car)["status"])
        self.assertEqual(writes, car.writes)
        self.assertEqual("openhu", tool.load_backup(path, car)["original"]["launcher"]["build"])
        self.restore_car(car)
        self.assertEqual("openhu", tool.launcher_state(car)["build"])

    def test_legacy_restore_without_upgrade_leaves_launcher_alone(self):
        car = FakeADB()
        self.legacy_configured(car)
        self.restore_car(car)
        self.assertNotIn("launcher_restore", car.writes)

    def test_unknown_update_cannot_be_adopted_from_hash_only(self):
        car = FakeADB()
        car.paths["com.chinatsp.launcher"] = "/data/app/com.chinatsp.launcher-foreign/base.apk"
        car.hashes[car.paths["com.chinatsp.launcher"]] = tool.PROFILE["launcher"]["update"]["sha256"]
        # Without UPDATED_SYSTEM_APP this cannot be treated as the factory update.
        self.assertFalse(tool.inspect(car)["compatible"])
        self.assertEqual([], car.writes)

    def test_restore_does_not_need_patch_or_local_apk_files(self):
        car = FakeADB()
        self.setup_car(car)
        with patch.object(tool, "ROOT", self.state / "missing"), \
                patch.object(tool, "prepare_launcher", side_effect=AssertionError("no rebuilding on restore")), \
                patch.object(tool, "verify_launcher_file", side_effect=AssertionError("no APK cache dependency")):
            self.restore_car(car)
        self.assertEqual("factory", tool.launcher_state(car)["build"])

    def test_corrupt_launcher_backup_identity_cannot_authorize_removal(self):
        car = FakeADB()
        self.setup_car(car)
        p = tool.backup_path(car, self.state)
        original = json.loads(p.read_text())
        writes = car.writes.copy()
        for key, value in (("build", "foreign"), ("uid", 0), ("sha256", "f" * 64), ("version_code", 1)):
            bad = copy.deepcopy(original)
            bad["original"]["launcher"][key] = value
            tool.write_json(p, bad)
            with self.assertRaises(tool.SetupError): self.restore_car(car)
            self.assertEqual(writes, car.writes)

    def test_broken_home_recovery_stops_after_factory_rollback_until_home_is_resolved(self):
        car = FakeADB()
        self.setup_car(car)
        car.launcher_home = "No activity found"
        self.assertFalse(tool.inspect(car)["compatible"])
        report = tool.inspect(car, recovery=True)
        self.assertTrue(report["compatible"])
        with self.assertRaises(tool.SetupError): tool.restore(car, self.state, report)
        self.assertEqual("factory", tool.launcher_state(car, check_home=False)["build"])
        self.assertTrue(car.packages[tool.RECEIVER]["installed"])
        car.launcher_home = tool.PROFILE["launcher"]["home"]
        self.restore_car(car)
        self.assertEqual(1, car.writes.count("launcher_restore"))

    def test_broken_home_without_owned_update_never_allows_restore_writes(self):
        car = FakeADB(receiver=True)
        car.run("install", "--no-streaming", "-r", "preexisting.apk")
        self.setup_car(car)
        car.launcher_home = "other/.Home"
        writes = car.writes.copy()
        with self.assertRaises(tool.SetupError):
            tool.restore(car, self.state, tool.inspect(car, recovery=True))
        self.assertEqual(writes, car.writes)


class PatchTests(unittest.TestCase):
    def test_diff_extra_and_negative_seek(self):
        p = binary_patch([(3, 1, -3), (3, 0, 0)], bytes([0, 1, 0, 0, 0, 1]), b"!")
        self.assertEqual(b"acc!abd", launcher_patch.apply(b"abc", p, 7))

    def test_seek_only_instruction_from_real_bsdiff_format(self):
        p = binary_patch([(0, 0, 1), (2, 0, 0)], b"\0\0")
        self.assertEqual(b"bc", launcher_patch.apply(b"abc", p, 2))

    def test_old_positions_outside_input_are_zero_extended(self):
        p = binary_patch([(1, 0, -2), (2, 0, 0)], bytes([0, 7, 1]))
        self.assertEqual(b"a\x07b", launcher_patch.apply(b"a", p, 3))

    def test_invalid_sizes_truncation_and_trailing_data_refused(self):
        good = binary_patch([(0, 3, 0)], extra=b"new")
        for p, n in [(b"bad", 3), (good, 4), (good[:-1], 3), (good + b"junk", 3),
                     (good, 0), (binary_patch([(4, 0, 0)], b"1234", size=3), 3),
                     (binary_patch([(0, 0, 0)], size=3), 3)]:
            with self.subTest(size=n), self.assertRaises(launcher_patch.PatchError):
                launcher_patch.apply(b"old", p, n)

    def test_unused_data_negative_lengths_and_bzip_bomb_refused(self):
        for p in [binary_patch([(0, 3, 0)], diff=b"unused", extra=b"new"),
                  binary_patch([(-1, 4, 0)], extra=b"new!", size=3),
                  binary_patch([(0, 3, 0)], extra=b"x" * 10000, size=3)]:
            with self.assertRaises(launcher_patch.PatchError): launcher_patch.apply(b"old", p, 3)

    def test_bundled_patch_pin_and_output_header(self):
        pin = tool.PROFILE["launcher"]["update"]
        p = tool.ROOT / pin["patch"]
        self.assertEqual(pin["patch_bytes"], p.stat().st_size)
        self.assertEqual(pin["patch_sha256"], tool.digest(p))
        self.assertEqual(pin["bytes"], launcher_patch._integer(p.read_bytes()[24:32]))

    def test_prepare_pulls_factory_checks_both_pins_and_caches_exact_output(self):
        old, new = b"synthetic original", b"synthetic signed update"
        data = binary_patch([(0, len(new), 0)], extra=new)
        class Pull:
            calls = 0
            def run(self, *args, **kwargs):
                self.calls += 1
                assert args[:2] == ("pull", tool.PROFILE["launcher"]["path"])
                Path(args[2]).write_bytes(old)
        pin = copy.deepcopy(tool.PROFILE["launcher"])
        pin.update(bytes=len(old), sha256=hashlib.sha256(old).hexdigest())
        pin["update"].update(bytes=len(new), sha256=hashlib.sha256(new).hexdigest(),
            patch="test.bsdiff", patch_bytes=len(data), patch_sha256=hashlib.sha256(data).hexdigest())
        with tempfile.TemporaryDirectory() as folder, patch.dict(tool.PROFILE, launcher=pin):
            root = Path(folder)
            (root / "test.bsdiff").write_bytes(data)
            car = Pull()
            with patch.object(tool, "ROOT", root):
                target = tool.prepare_launcher(car, root / "private")
                self.assertEqual(new, target.read_bytes())
                self.assertEqual(old, (target.parent / "factory-launcher.apk").read_bytes())
                self.assertEqual(target, tool.prepare_launcher(car, root / "private"))
                self.assertEqual(1, car.calls)
                target.write_bytes(b"corrupt")
                with self.assertRaises(tool.SetupError): tool.prepare_launcher(car, root / "private")
                target.unlink()
                (target.parent / "factory-launcher.apk").write_bytes(b"wrong original")
                with self.assertRaises(tool.SetupError): tool.prepare_launcher(car, root / "private")


if __name__ == "__main__":
    unittest.main()
