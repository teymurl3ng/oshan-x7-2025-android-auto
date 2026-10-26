# Contributing

If you get this working on another Oshan X7, I'd like to hear what headunit and
firmware you have. For now, I'm keeping this repo focused on the wired setup I
got working on my car.

If you find a problem, please include the tool version, command, mismatch/error message,
firmware/MCU versions, and whether a device operation had started. Redact device
serials, IP/MAC addresses, Wi-Fi names, account data, and local backup paths.
Please don't attach raw dumps or your private backups.

Before I can call another firmware supported, I need evidence: exact device properties,
firmware and MCU identifiers, factory package identities and hashes, existing root
behavior, the actual fullscreen handler semantics, and successful wired projection.
Document setup, a repeated run, reboot, restore, and retained access to factory
controls on that device. The same model/year, or an AI saying it should work,
doesn't establish that.

Please don't remove checks just to get a different unit through setup. Don't submit proprietary factory
APKs, phone data, credentials, or broad debloat lists. The original code is MIT;
upstream apps retain their own licenses.

The supported launcher is distributed as a pinned binary patch applied to the
owner's matching original APK. Keep both full APKs and all signing keys private.
Do not change an artifact pin without inspecting the resulting code and
qualifying that exact build on the car. Preserve legacy backup compatibility,
unchanged factory-base checks and ownership on rollback; an update that was
already present before setup must never be claimed or removed by a new cycle.

Run `python3 -m unittest discover -s tests -v` for code changes. Tests must exercise
failure paths and the limits on device mutations as well as successful setup.
