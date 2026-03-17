"""Shared pytest fixtures for the eu4_assistant_bot test suite."""

import zipfile
import pytest
from pathlib import Path


@pytest.fixture
def sample_save_zip(tmp_path: Path) -> Path:
    """A valid .eu4 ZIP save with a 'gamestate' entry."""
    p = tmp_path / "save.eu4"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("meta", "date = 1460.06.01\n")
        zf.writestr("gamestate", 'date = 1460.06.01\nplayer = "POR"\n')
        zf.writestr("ai", "")
    return p


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
