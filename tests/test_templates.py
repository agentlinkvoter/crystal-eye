from __future__ import annotations

from pathlib import Path

from crystal_eye.templates.registry import TemplateRegistry


def test_scan_finds_facebook(template_registry):
    names = template_registry.list_names()
    assert "facebook" in names


def test_get_facebook_manifest(template_registry):
    manifest = template_registry.get("facebook")
    assert manifest is not None
    assert manifest.display_name == "Facebook"
    assert manifest.auth_flow == "single"
    assert len(manifest.fields) == 2


def test_get_template_dir(template_registry):
    template_dir = template_registry.get_template_dir("facebook")
    assert template_dir is not None
    assert (template_dir / "login.html").exists()
    assert (template_dir / "error.html").exists()


def test_get_nonexistent(template_registry):
    assert template_registry.get("nonexistent") is None


def test_empty_registry(tmp_path):
    registry = TemplateRegistry(tmp_path)
    registry.scan()
    assert registry.list_names() == []
