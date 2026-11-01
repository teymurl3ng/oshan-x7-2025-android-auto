"""Reference capture bounds, identity and private PNG validation; no car."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import Mock

import oshan_x7 as core
import reference_capture as capture


class CaptureTests(unittest.TestCase):
    def test_remote_path_cannot_escape_owned_directory(self):
        for value in ("/", "/data/local/tmp/other", "/data/local/tmp/oshan-carlink-reference-" + "a"*16 + ";id"):
            with self.assertRaises(ValueError):
                capture.script(value)
        text = capture.script("/data/local/tmp/oshan-carlink-reference-" + "a"*16)
        self.assertIn("for frame in 1 2 3 4 5 6", text)
        self.assertNotIn("while", text)
        self.assertNotIn("su ", text)

    def test_capture_identity_mismatch_never_reads_or_removes_remote_files(self):
        with tempfile.TemporaryDirectory() as folder:
            trial = Mock()
            trial.c = core
            trial.adb.serial = "original-car"
            trial.path = Path(folder) / "carlink-trial.json"
            trial.load.return_value = {"phase":"trial_ready", "restored":False}
            trial.inspect.return_value = ({}, {"installed":True,"verified":True})
            root = Path(folder)/"reference-capture"
            root.mkdir()
            remote = "/data/local/tmp/oshan-carlink-reference-" + "a"*16
            (root/"capture.json").write_text(json.dumps({"schema":1,"serial":"another-car","remote":remote,
                "script_sha256":"bad","frames":6,"collected":False}))
            with self.assertRaises(core.SetupError):
                capture.run(trial,"carlink-reference-collect")
            trial.adb.shell.assert_not_called()
            trial.adb.run.assert_not_called()

    def test_screenshot_validator_rejects_incomplete_or_wrong_image(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/"frame.png"
            for raw in (b"",b"not PNG",b"\x89PNG\r\n\x1a\n"+b"broken"*100):
                p.write_bytes(raw)
                with self.assertRaises(ValueError):
                    capture.png(p)
