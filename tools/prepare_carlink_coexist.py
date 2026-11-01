#!/usr/bin/env python3
"""Prepare/audit the manifest-only CarLink 1.0.7 coexistence fix, offline.

No device access or signing keys. Sign the unsigned output separately using a
private trial key. Executable code and all other APK entry payloads are kept.
"""
import argparse
import hashlib
from pathlib import Path
import zipfile

BASE_SHA256 = "16e8b98436a5c5f355aa4b49086e28d41bee9f9f874174658cafb682fd503e77"
OLD = "com.andrerinas.openheadunit.permission.NAVIGATION_UPDATE"
NEW = "com.carlink.oshanx7trialapp.permission.NAVIGATION_UPDATE"


def manifest_only(data):
    old, new = OLD.encode("utf-16le"), NEW.encode("utf-16le")
    if len(old) != len(new) or data.count(old) != 1 or new in data:
        raise ValueError("Unexpected manifest strings; refusing any inferred patch")
    # Equal lengths preserve binary XML string indices, offsets and attributes.
    return data.replace(old, new)


def verify_base(path):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != BASE_SHA256:
        raise ValueError("Input is not the exact reviewed official CarLink 1.0.7 APK")


def prepare(base, output):
    verify_base(base)
    with zipfile.ZipFile(base) as src, zipfile.ZipFile(output, "x") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == "AndroidManifest.xml":
                data = manifest_only(data)
            dst.writestr(info, data)


def audit(base, modified):
    verify_base(base)
    with zipfile.ZipFile(base) as src, zipfile.ZipFile(modified) as dst:
        if len(src.namelist()) != len(set(src.namelist())) or len(dst.namelist()) != len(set(dst.namelist())):
            raise ValueError("Duplicate ZIP entries are unsupported")
        if set(src.namelist()) != set(dst.namelist()):
            raise ValueError("APK entry set changed")
        for name in src.namelist():
            expected = src.read(name)
            if name == "AndroidManifest.xml":
                expected = manifest_only(expected)
            if dst.read(name) != expected:
                raise ValueError("Unexpected entry change: " + name)
        return len(src.namelist())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "audit"))
    parser.add_argument("base", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.base, args.output)
    count = audit(args.base, args.output)
    print(f"Verified {count} APK entry payloads; only the one manifest permission name differs.")


if __name__ == "__main__":
    main()
