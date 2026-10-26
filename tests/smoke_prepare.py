"""CI-only real download check: runs 'adb version'; never starts a device session."""

import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare

with tempfile.TemporaryDirectory() as directory:
    with patch.object(prepare, "TOOLS", Path(directory) / "tools"):
        with patch.object(prepare, "find_adb", return_value=None):
            result = prepare.prepare()
        assert result["downloaded"]
        assert prepare.working_adb(result["adb"])
        found = prepare.find_adb()
        assert found is not None
        print(json.dumps({"downloaded": True, "source": result["source"],
                          "version": prepare.working_adb(result["adb"])}))
