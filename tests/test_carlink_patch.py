"""Reject broad APK edits and changed patch inputs without device access."""
import hashlib
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

import carlink_trial as trial
from tools import prepare_carlink_coexist as builder


class CoexistPatchTests(unittest.TestCase):
    def test_manifest_patch_preserves_length_and_refuses_ambiguous_inputs(self):
        original = b"header" + builder.OLD.encode("utf-16le") + b"tail"
        result = builder.manifest_only(original)
        self.assertEqual(len(original), len(result))
        self.assertIn(builder.NEW.encode("utf-16le"), result)
        for invalid in (b"unknown", original + original, result):
            with self.subTest(invalid=invalid[:6]):
                with self.assertRaises(ValueError):
                    builder.manifest_only(invalid)

    def test_audit_rejects_any_executable_or_asset_change(self):
        with tempfile.TemporaryDirectory() as folder:
            base, output = Path(folder) / "base.apk", Path(folder) / "new.apk"
            manifest = b"prefix" + builder.OLD.encode("utf-16le")
            with zipfile.ZipFile(base, "w") as z:
                z.writestr("AndroidManifest.xml", manifest)
                z.writestr("classes.dex", b"unchanged executable")
                z.writestr("assets/test", b"unchanged asset")
            with patch.object(builder, "verify_base"):
                builder.prepare(base, output)
                self.assertEqual(3, builder.audit(base, output))
                for modified_name in ("classes.dex", "assets/test"):
                    bad = Path(folder) / (modified_name.replace("/", "-") + ".apk")
                    with zipfile.ZipFile(output) as src, zipfile.ZipFile(bad, "w") as dst:
                        for name in src.namelist():
                            dst.writestr(name, b"tampered" if name == modified_name else src.read(name))
                    with self.assertRaises(ValueError):
                        builder.audit(base, bad)

    def test_patch_is_the_exact_audited_artifact(self):
        path = Path(__file__).resolve().parents[1] / trial.PIN["patch"]
        self.assertEqual(trial.PIN["patch_bytes"], path.stat().st_size)
        self.assertEqual(trial.PIN["patch_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_unknown_original_apk_cannot_produce_an_output(self):
        with tempfile.TemporaryDirectory() as folder:
            base, output = Path(folder) / "unknown.apk", Path(folder) / "new.apk"
            base.write_bytes(b"unverified base")
            with self.assertRaises(ValueError):
                builder.prepare(base, output)
            self.assertFalse(output.exists())
