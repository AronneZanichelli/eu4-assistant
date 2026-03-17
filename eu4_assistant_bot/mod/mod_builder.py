"""Mod builder — generates and installs the monthly autosave mod for EU4.

The mod consists of three files:
- A ``.mod`` descriptor (``eu4_assistant_autosave.mod``)
- An event file (``events/monthly_save.txt``) with the hidden save event
- An on_actions file (``common/on_actions/eu4_assistant.txt``) that fires
  the event every in-game month via ``on_monthly_pulse``

Installation is idempotent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ModInstallStatus(str, Enum):
    INSTALLED = "installed"
    UPDATED   = "updated"
    SKIPPED   = "skipped"


@dataclass
class ModInstallResult:
    status: ModInstallStatus
    mod_path: Path
    version: str


_MOD_FILE_TEMPLATE = """\
name = "EU4 Assistant - Monthly Autosave"
supported_version = "{version}"
path = "mod/eu4_assistant_autosave"
"""

_EVENT_FILE = """\
namespace = eu4_assistant

country_event = {
    id = eu4_assistant.1
    hidden = yes
    is_triggered_only = yes

    immediate = {
        save_game = yes
    }

    option = {
        name = eu4_assistant.1.a
    }
}
"""

_ON_ACTIONS_FILE = """\
on_actions = {
    on_monthly_pulse = {
        events = { eu4_assistant.1 }
    }
}
"""


class ModBuilder:
    """Installs the EU4 Assistant monthly autosave mod into the EU4 mod folder.

    The mod adds a hidden country_event triggered every in-game month that
    calls ``save_game = yes``, ensuring the companion always has a fresh save
    to read without requiring the user to manually save.

    Install is idempotent: calling ``install`` twice with the same version
    returns ``SKIPPED`` on the second call.
    """

    MOD_NAME = "eu4_assistant_autosave"

    def install(self, mod_folder: Path, eu4_version: str = "1.37.*") -> ModInstallResult:
        """Install or update the autosave mod.

        Args:
            mod_folder: Path to the EU4 mod directory
                (e.g. ``Documents/Paradox Interactive/Europa Universalis IV/mod``).
            eu4_version: ``supported_version`` string written to the ``.mod`` file.

        Returns:
            :class:`ModInstallResult` with status INSTALLED, UPDATED, or SKIPPED.
        """
        mod_folder.mkdir(parents=True, exist_ok=True)

        dot_mod         = mod_folder / f"{self.MOD_NAME}.mod"
        mod_dir         = mod_folder / self.MOD_NAME
        event_dir       = mod_dir / "events"
        event_file      = event_dir / "monthly_save.txt"
        on_actions_dir  = mod_dir / "common" / "on_actions"
        on_actions_file = on_actions_dir / "eu4_assistant.txt"

        # Determine current status
        if dot_mod.exists() and event_file.exists() and on_actions_file.exists():
            existing_version = self._read_version(dot_mod)
            if existing_version == eu4_version:
                return ModInstallResult(
                    status=ModInstallStatus.SKIPPED,
                    mod_path=mod_dir,
                    version=eu4_version,
                )
            status = ModInstallStatus.UPDATED
        else:
            status = ModInstallStatus.INSTALLED

        # Write files
        event_dir.mkdir(parents=True, exist_ok=True)
        on_actions_dir.mkdir(parents=True, exist_ok=True)
        dot_mod.write_text(_MOD_FILE_TEMPLATE.format(version=eu4_version), encoding="utf-8")
        event_file.write_text(_EVENT_FILE, encoding="utf-8")
        on_actions_file.write_text(_ON_ACTIONS_FILE, encoding="utf-8")

        return ModInstallResult(status=status, mod_path=mod_dir, version=eu4_version)

    @staticmethod
    def _read_version(dot_mod: Path) -> str:
        """Extract the supported_version value from an existing .mod file."""
        for line in dot_mod.read_text(encoding="utf-8").splitlines():
            if line.startswith("supported_version"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    return parts[1].strip().strip('"')
        return ""
