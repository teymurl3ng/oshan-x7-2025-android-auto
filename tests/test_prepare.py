"""Host tool preparation tests; downloads and execution are simulated."""

import io
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import prepare
import oshan_x7


class Response(io.BytesIO):
    def geturl(self):
        return "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tools = self.root / "tools"
        for replacement in (patch.object(prepare, "TOOLS", self.tools),
                            patch.object(prepare.platform, "system", return_value="Linux"),
                            patch.object(prepare.platform, "machine", return_value="x86_64")):
            replacement.start()
            self.addCleanup(replacement.stop)

    def archive(self, filename="platform-tools/adb", contents=b"synthetic binary", symlink=False):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as package:
            entry = zipfile.ZipInfo(filename)
            # Preserve the raw member spelling even when the Windows writer normalizes it.
            entry.filename = filename
            entry.orig_filename = filename
            if symlink:
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            package.writestr(entry, contents)
        return stream.getvalue()

    def test_existing_adb_is_reused_without_download(self):
        with patch.object(prepare, "find_adb", return_value=(self.root / "adb", "Android Debug Bridge version 1.0.41")), \
                patch.object(prepare.urllib.request, "urlopen") as request:
            result = prepare.prepare()
        self.assertFalse(result["downloaded"])
        request.assert_not_called()
        self.assertFalse(self.tools.exists())

    def test_verify_only_does_not_install(self):
        with patch.object(prepare, "find_adb", return_value=None):
            with self.assertRaises(prepare.PreparationError):
                prepare.prepare(download=False)
        self.assertFalse(self.tools.exists())

    def test_download_installs_whole_directory_and_records_source(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as package:
            package.writestr("platform-tools/adb", b"synthetic executable")
            package.writestr("platform-tools/lib64/libadb.so", b"synthetic support file")
        with patch.object(prepare, "find_adb", return_value=None), \
                patch.object(prepare.urllib.request, "urlopen", return_value=Response(payload.getvalue())), \
                patch.object(prepare, "working_adb", return_value="Android Debug Bridge version 1.0.41"):
            result = prepare.prepare()
        self.assertTrue(result["downloaded"])
        self.assertEqual(prepare.URLS["Linux"], result["source"])
        self.assertEqual((self.tools / "platform-tools" / "adb").resolve(), Path(result["adb"]))
        self.assertTrue((self.tools / "platform-tools/lib64/libadb.so").is_file())
        self.assertTrue((self.tools / "download.json").is_file())
        self.assertEqual(64, len(result["archive_sha256"]))
        self.assertFalse(any(self.tools.glob("prepare-*")))

    def test_archive_paths_and_links_are_rejected(self):
        for filename, link in (("../escape", False), ("platform-tools/../../escape", False),
                               ("/absolute", False), ("platform-tools/C:evil", False),
                               ("platform-tools/dir\\evil", False), ("platform-tools/adb", True)):
            with self.subTest(filename=filename, link=link):
                archive = self.root / "bad.zip"
                archive.write_bytes(self.archive(filename, symlink=link))
                with self.assertRaises(prepare.PreparationError):
                    prepare.extract_tools(archive, self.root / "extracted")
        self.assertFalse((self.root / "extracted").exists())

    def test_missing_executable_rejected(self):
        archive = self.root / "bad.zip"
        archive.write_bytes(self.archive("platform-tools/NOTICE.txt"))
        with self.assertRaises(prepare.PreparationError):
            prepare.extract_tools(archive, self.root / "extracted")

    def test_broken_existing_private_install_is_preserved(self):
        target = self.tools / "platform-tools"
        target.mkdir(parents=True)
        (target / "adb").write_bytes(b"broken")
        with patch.object(prepare, "find_adb", return_value=None), \
                patch.object(prepare.urllib.request, "urlopen") as request:
            with self.assertRaises(prepare.PreparationError):
                prepare.prepare()
        self.assertEqual(b"broken", (target / "adb").read_bytes())
        request.assert_not_called()

    def test_wrong_linux_architecture_needs_native_package(self):
        with patch.object(prepare, "find_adb", return_value=None), \
                patch.object(prepare.platform, "machine", return_value="aarch64"):
            with self.assertRaises(prepare.PreparationError):
                prepare.prepare()
        self.assertFalse(self.tools.exists())

    def test_failed_binary_validation_does_not_install(self):
        with patch.object(prepare, "find_adb", return_value=None), \
                patch.object(prepare.urllib.request, "urlopen", return_value=Response(self.archive())), \
                patch.object(prepare, "working_adb", return_value=None):
            with self.assertRaises(prepare.PreparationError):
                prepare.prepare()
        self.assertFalse((self.tools / "platform-tools").exists())
        self.assertFalse(any(self.tools.glob("prepare-*")))

    def test_version_check_rejects_wrong_program(self):
        for reply in (subprocess.CompletedProcess([], 0, "some other program", ""),
                      subprocess.CompletedProcess([], 1, "Android Debug Bridge version", "")):
            with patch.object(prepare.subprocess, "run", return_value=reply):
                self.assertIsNone(prepare.working_adb("adb"))

    def test_version_check_handles_missing_binary(self):
        with patch.object(prepare.subprocess, "run", side_effect=FileNotFoundError()):
            self.assertIsNone(prepare.working_adb("adb"))

    def test_common_sdk_path_is_used_by_car_cli(self):
        expected = self.root / "SDK path with spaces" / "adb"
        with patch.object(oshan_x7, "find_adb", return_value=(expected, "version")):
            args = oshan_x7.parser().parse_args(["check"])
        self.assertEqual(str(expected), args.adb)


if __name__ == "__main__":
    unittest.main()
