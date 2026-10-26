# Testing

These are the checks I use for the scripts, followed by the car tests I still
need to complete. I don't want a passing software test to be mistaken for a
successful Android Auto session.

## Offline tests

Run with Python 3.10 or later:

```sh
python3 -m unittest discover -s tests -v
```

The tests simulate ADB responses and local state. They exercise compatibility
refusals, wrong/multiple transports, exact artifact checks, write-ahead backup,
setup read-back, repeated runs, restore, and interrupted operations. These are
software checks, not a substitute for actual USB/projection testing.

Host preparation tests also exercise existing-tool reuse, private SDK extraction,
invalid archive paths, and failed binary validation. The CI additionally downloads
Google's real Platform Tools on each OS with Python 3.13 and runs only `adb version`.
That network smoke test neither starts an ADB server nor accesses a car.

## What I still need to test on the car

The individual changes worked on my car, but I haven't run the new installer
through its full setup-and-restore cycle there yet. This is the checklist for
that test on the matching firmware:

1. Read-only check of identity, original enabled/layout states, and existing receiver.
2. Setup with a verified APK; retain the original backup and journal.
3. Repeat setup; confirm no additional device writes and the original backup unchanged.
4. USB Host handoff and real wired AA: image, audio, touch, voice, navigation.
5. Access to factory Home/Back, camera, climate controls, and other usual functions
   while parked. Do not operate vehicle systems through improvised ADB commands.
6. Normal reboot and repeat wired test; separately identify any cold ignition test.
7. Restore via USB Device mode; verify original CarAuto/layout behavior and receiver
   ownership. Repeat restore and confirm no further writes.
8. Interrupted setup/restore recovery on a controlled test unit, if practical.

If you're helping test, please say what the script read back and what you actually
saw or heard on the car. Keep identifiers, APKs, network settings, and raw private
backups out of public reports.
