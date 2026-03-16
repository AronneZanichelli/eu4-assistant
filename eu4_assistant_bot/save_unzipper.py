"""EU4 save file decompressor.

EU4 saves are ZIP archives containing ``gamestate``, ``meta`` and ``ai``
entries.  Plain-text saves (uncompressed) are also supported.  Ironman
binary saves are out of scope for v1.0.
"""

from __future__ import annotations

import zipfile
from pathlib import Path


class SaveFormatError(Exception):
    """Raised when a .eu4 save file cannot be read or parsed."""


class SaveUnzipper:
    """Extracts the gamestate text from a .eu4 save file.

    EU4 saves are ZIP archives containing three entries: ``meta``,
    ``gamestate``, and ``ai``.  Plain-text saves (uncompressed, used in some
    older versions or mods) are also supported.
    """

    # ZIP magic bytes
    _ZIP_MAGIC = b"PK"

    def extract_gamestate(self, path: Path) -> str:
        """Return the raw text content of the gamestate entry.

        Args:
            path: Path to the .eu4 save file.

        Raises:
            SaveFormatError: If the file is missing, corrupted, or lacks a
                gamestate entry.
        """
        if not path.exists():
            raise SaveFormatError(f"Save file not found: {path}")

        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise SaveFormatError(f"Cannot read save file: {path}") from exc

        if raw[:2] == self._ZIP_MAGIC:
            return self._extract_from_zip(path, raw)
        else:
            return self._read_plain(path, raw)

    def _extract_from_zip(self, path: Path, raw: bytes) -> str:
        try:
            with zipfile.ZipFile(path, "r") as zf:
                names = zf.namelist()
                # prefer explicit 'gamestate' entry
                if "gamestate" in names:
                    return zf.read("gamestate").decode("utf-8", errors="replace")
                # fallback: first entry that is not 'meta'
                for name in names:
                    if name != "meta":
                        return zf.read(name).decode("utf-8", errors="replace")
                raise SaveFormatError(
                    f"ZIP save '{path}' contains no gamestate entry. "
                    f"Entries found: {names}"
                )
        except zipfile.BadZipFile as exc:
            raise SaveFormatError(f"Corrupted ZIP save: {path}") from exc

    @staticmethod
    def _read_plain(path: Path, raw: bytes) -> str:
        return raw.decode("utf-8", errors="replace")
