from __future__ import annotations

import importlib.resources
from pathlib import Path

from pydantic import BaseModel


class TemplateField(BaseModel):
    name: str
    display_name: str
    field_type: str  # "text" | "password" | "email" | "tel"


class TemplateManifest(BaseModel):
    name: str
    display_name: str
    redirect_url: str
    fields: list[TemplateField]
    auth_flow: str = "single"  # "single" | "multi-step"
    max_attempts: int = 2
    description: str = ""


class TemplateRegistry:
    """Discovers and caches available phishing templates."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        self._templates_dir = templates_dir or self._discover_templates_dir()
        self._manifests: dict[str, TemplateManifest] = {}

    def scan(self) -> None:
        self._manifests.clear()
        if not self._templates_dir.is_dir():
            return
        for entry in sorted(self._templates_dir.iterdir()):
            manifest_path = entry / "manifest.json"
            if entry.is_dir() and manifest_path.exists():
                manifest = TemplateManifest.model_validate_json(manifest_path.read_text())
                self._manifests[manifest.name] = manifest

    def get(self, name: str) -> TemplateManifest | None:
        return self._manifests.get(name)

    def list_names(self) -> list[str]:
        return list(self._manifests.keys())

    def list_all(self) -> list[TemplateManifest]:
        return list(self._manifests.values())

    def get_template_dir(self, name: str) -> Path | None:
        if name in self._manifests:
            return self._templates_dir / name
        return None

    @staticmethod
    def _discover_templates_dir() -> Path:
        # 1. Check CWD (development — running from project root)
        cwd_templates = Path.cwd() / "templates"
        if cwd_templates.is_dir() and any(cwd_templates.iterdir()):
            return cwd_templates

        # 2. Check relative to this source file (development — running from anywhere)
        src_relative = Path(__file__).resolve().parent.parent.parent.parent / "templates"
        if src_relative.is_dir() and any(src_relative.iterdir()):
            return src_relative

        # 3. Bundled templates (installed via pip/uv)
        try:
            ref = importlib.resources.files("crystal_eye") / "_bundled_templates"
            bundled = Path(str(ref))
            if bundled.is_dir():
                return bundled
        except (ModuleNotFoundError, TypeError):
            pass

        return cwd_templates
