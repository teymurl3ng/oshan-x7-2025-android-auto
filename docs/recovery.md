# Restore and recover

Keep the repository and the original **`.oshan-x7`** folder, or the custom
`--state-dir` used during installation. Restore uses the saved original settings
and operation records. It is not a factory reset.

## Reconnect and inspect

1. Disconnect your phone from the car.
2. Select **Device模式** in `开发模式`. [Car menu instructions](car-menu.md).
3. Reconnect the trusted laptop and accept its debugging authorization if shown.
4. Open the original repository folder and run status using the same Python,
   ADB executable/server port, USB target and state directory as installation:

```sh
python3 oshan_x7.py status --adb "/path/to/adb" --json
```

Replace the ADB path with your verified executable. On Windows use `py -3` or
your recorded Python path. Include the same custom `--adb-port`, `--serial` and
`--state-dir` values if you used them.

## Choose the next step

| Result | What it means / next step |
| --- | --- |
| Unexpected permission screen / exit 3 | Keep the laptop connected. Inspect the screen and diagnose the missing access before responding. After resolving it, rerun the same setup command. |
| `inspect_configuration_drift` | Settings differ from the completed installation. Inspect the change before using the phone or deciding to restore. |
| Setup failed, nested recovery says `restored` | Installation failed, but its changes were reversed. Diagnose the reported cause before a new installation. |
| `recovery_required`, interrupted operation or lost USB | Keep the backup, reconnect in Device mode, resolve the reported issue and run restore. |
| Identity mismatch | Stop. Do not bypass firmware/app/launcher checks or change the profile. |

To undo the installation or finish an interrupted recovery:

```sh
python3 oshan_x7.py restore --adb "/path/to/adb" --json
```

A failed setup invokes the same recovery engine automatically. If recovery is
incomplete, inspect `failed_stage`, `recovery`, `component_issues`, errors and
`next_action`. Reuse the original backup when retrying; do not repeat raw package
commands or replace the saved original state.

`restored` means the recorded changes were reversed and applicable checks passed.
`recovery_required` means work remains. Repeating completed restore makes no car
changes. For a later new installation, retain this backup and select a new
`--state-dir`.

## What restore changes

Restore removes a launcher update only if this installation added it, checks
factory Home, restores changed fullscreen/permission/CarAuto settings, and removes
CarLink only if this installation added it. Apps and launcher updates already
present before setup are retained. If the original fullscreen key was absent,
restore uses the factory default value `-1` after a changed layout.

Permission recovery preserves previously granted access and unrelated accessibility
services, including services added later. If CarLink has already been removed,
restore checks and cleans up its recorded global service/battery changes without
trying to grant or revoke permissions on an absent app. Unknown replacement APKs
are left untouched. [Permission details](permissions.md).

A broken app or lost root can prevent some recovery steps without blocking an
otherwise valid launcher rollback. Such a partial recovery remains incomplete.
CarLink is retained while required Home, permission or CarAuto recovery is blocked.

## Access limits

Recovery needs responsive Android/package management and authorized USB.
While Device mode is active, the laptop can diagnose a launcher failure if those
services still work. After disconnection, the laptop cannot supervise the car.
If menus remain usable, return from Host to Device and reconnect. A way back
with an unusable launcher/menu has **not been tested**; this is not a boot rescue
or firmware repair tool.

## Stale locks

`operation.lock` prevents concurrent setup/restore commands. Check its PID and
actual running command before removing it; PIDs can be reused. Wait for an active
operation. Remove only a verified stale lock, keeping all backup files intact.
