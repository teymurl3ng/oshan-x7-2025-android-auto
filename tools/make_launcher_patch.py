#!/usr/bin/env python3
"""Maintainer-only: recreate the pinned binary patch from two local APKs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--factory', type=Path, required=True)
    parser.add_argument('--modified', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bsdiff', default=shutil.which('bsdiff'))
    args = parser.parse_args()
    pin = json.loads((ROOT / 'profiles/f202-mca-rhd-20241022.json').read_text())['launcher']
    if not args.bsdiff:
        parser.error('Install bsdiff from your trusted OS package manager or pass --bsdiff.')
    for path, expected in ((args.factory, pin), (args.modified, pin['update'])):
        if path.stat().st_size != expected['bytes'] or sha(path) != expected['sha256']:
            parser.error('Input does not match the already qualified launcher: ' + str(path))
    if args.output.exists():
        parser.error('Output exists; preserve it and choose another path.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=args.output.parent)
    os.close(fd)
    try:
        subprocess.run([args.bsdiff, str(args.factory), str(args.modified), temporary], check=True, timeout=180)
        output = Path(temporary)
        if sha(output) != pin['update']['patch_sha256'] or output.stat().st_size != pin['update']['patch_bytes']:
            parser.error('Generated patch differs from the qualified artifact; nothing published.')
        os.replace(temporary, args.output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print('Recreated the exact pinned patch. No device access or APK publication.')


if __name__ == '__main__':
    main()
