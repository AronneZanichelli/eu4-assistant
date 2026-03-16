"""Tests for ModBuilder install, update and idempotency."""

from pathlib import Path
import pytest
from eu4_assistant_bot.mod import ModBuilder, ModInstallResult, ModInstallStatus


def test_install_creates_mod_files(tmp_path):
    ModBuilder().install(tmp_path)
    assert (tmp_path / "eu4_assistant_autosave.mod").exists()
    assert (tmp_path / "eu4_assistant_autosave" / "events" / "monthly_save.txt").exists()


def test_install_returns_installed_status(tmp_path):
    result = ModBuilder().install(tmp_path)
    assert result.status == ModInstallStatus.INSTALLED
    assert isinstance(result, ModInstallResult)
    assert result.version == "1.37.*"


def test_install_idempotent_same_version(tmp_path):
    ModBuilder().install(tmp_path, eu4_version="1.37.*")
    result = ModBuilder().install(tmp_path, eu4_version="1.37.*")
    assert result.status == ModInstallStatus.SKIPPED


def test_install_updates_different_version(tmp_path):
    ModBuilder().install(tmp_path, eu4_version="1.36.*")
    result = ModBuilder().install(tmp_path, eu4_version="1.37.*")
    assert result.status == ModInstallStatus.UPDATED
    assert result.version == "1.37.*"


def test_install_creates_missing_directory(tmp_path):
    nested = tmp_path / "deep" / "mod"
    ModBuilder().install(nested)
    assert nested.exists()


def test_generated_mod_file_contains_version(tmp_path):
    ModBuilder().install(tmp_path, eu4_version="1.37.*")
    content = (tmp_path / "eu4_assistant_autosave.mod").read_text()
    assert "1.37.*" in content
    assert "EU4 Assistant" in content


def test_generated_event_file_contains_namespace(tmp_path):
    ModBuilder().install(tmp_path)
    content = (tmp_path / "eu4_assistant_autosave" / "events" / "monthly_save.txt").read_text()
    assert "namespace = eu4_assistant" in content
    assert "save_game = yes" in content
    assert "on_monthly_pulse" in content
