# Restore and recover

Keep the original repository and private `.oshan-x7` directory, or the custom
`--state-dir` used for setup. Recovery uses that original baseline and journal;
it is not a factory reset.

Disconnect the phone, select **Device模式**, reconnect the trusted laptop and
accept debugging authorization if shown. Reuse the original interpreter, ADB
executable/server port, USB target and state directory:

```sh
python3 oshan_x7.py status --json
python3 oshan_x7.py restore --json
```

Windows uses `py -3`. A failed setup invokes the same recovery engine
automatically. After USB loss, regain Device mode and run restore with the
original journal. Do not repeat raw package mutations or create a fresh baseline.

## Owned changes

Recovery restores its exact launcher update to the unchanged factory base,
checks Home, restores the owned fullscreen preference, returns permission and
CarAuto changes to their recorded states, and removes CarLink only if this
cycle installed it. A preexisting app and its settings stay. An originally
absent changed fullscreen key uses factory-default `-1`.

Permission recovery revokes only grants attempted by this cycle that were
originally absent. It restores special app access and the battery exemption,
removes only its added USB auto-confirm service, and preserves other
accessibility services, including ones added later. It does not disable all USB
permission dialogs or modify other apps' access. [Permission details](permissions.md).

The system-launcher update rollback uses `pm uninstall -k` without `--user`.
Use the CLI: a per-user launcher removal would be a different operation.
Older private journals retain their matching recovery behavior automatically;
they are not a prerequisite for new installation.

## Incomplete recovery

`restored` means recorded changes were reversed and eligible health checks
passed. `recovery_required` means work remains. Inspect `failed_stage`,
`recovery`, `component_issues`, errors and `next_action`; keep the backup and
rerun restore after fixing the reported issue. Completed restore is a no-op.
A later new setup uses a new state directory while retaining the completed one.

Mandatory gates still require the saved USB/device identity, exact firmware,
factory/active launcher identity, UID/version and Device mode. Unknown firmware
or launchers stop writes. Independent recovery steps can still run when an app,
root-dependent preference or another component is broken. Unknown replacement
apps are kept. Newly installed CarLink remains until Home, permissions and
CarAuto recovery verify; partial recovery never claims full success.

## Access limits

While connected in Device mode, responsive Android/package management/authorized
USB ADB can be used for recovery. After laptop disconnection, supervision ends.
If the factory menu remains accessible, return from Host to Device and reconnect.
A route back with an unusable launcher/menu has not been qualified; this project
does not promise a boot rescue, emergency button or firmware repair.

An Android reboot check is separate from a cold ignition cycle. It does not
install a watchdog. The complete fresh setup/restore sequence still needs a live
qualification cycle. [Testing](testing.md).

## Stale locks

`operation.lock` prevents concurrent writes. Check its PID and actual running
command before removing it: PIDs can be reused. Wait for an active operation.
Only a verified stale lock may be removed, keeping its original backup intact.
