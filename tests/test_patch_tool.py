"""Patch generation selects current/legacy pins and refuses mismatched artifacts."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import make_launcher_patch as tool


class PatchToolTests(unittest.TestCase):
    def test_profile_selection_and_output_verification(self):
        for profile in ('carlink', 'openhu'):
            for corrupt in (False, True):
                with self.subTest(profile=profile, corrupt=corrupt), tempfile.TemporaryDirectory() as folder:
                    root = Path(folder)
                    (root / 'profiles').mkdir()
                    old, new, delta = b'factory', profile.encode(), b'delta:' + profile.encode()
                    def identity(data):
                        return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                    pin = {**identity(old), 'update': {**identity(new),
                           'patch_bytes': len(delta), 'patch_sha256': hashlib.sha256(delta).hexdigest()}}
                    name = 'f202-carlink.json' if profile == 'carlink' else 'f202-mca-rhd-20241022.json'
                    (root / 'profiles' / name).write_text(json.dumps({'launcher': pin}))
                    (root / 'factory.apk').write_bytes(old)
                    (root / 'modified.apk').write_bytes(new)
                    output = root / 'output.bsdiff'
                    args = ['--factory', str(root / 'factory.apk'), '--modified', str(root / 'modified.apk'),
                            '--output', str(output), '--bsdiff', 'synthetic-bsdiff']
                    if profile == 'openhu': args += ['--profile', profile]
                    def generate(command, **kwargs):
                        Path(command[-1]).write_bytes(b'wrong' if corrupt else delta)
                    with patch.object(tool, 'ROOT', root), patch.object(tool.subprocess, 'run', side_effect=generate), \
                            contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        if corrupt:
                            with self.assertRaises(SystemExit): tool.main(args)
                            self.assertFalse(output.exists())
                        else:
                            tool.main(args)
                            self.assertEqual(delta, output.read_bytes())
                        (root / 'modified.apk').write_bytes(b'unknown')
                        with self.assertRaises(SystemExit): tool.main(args)
