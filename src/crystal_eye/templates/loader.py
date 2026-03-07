from __future__ import annotations

from pathlib import Path

import jinja2

from crystal_eye.templates.registry import TemplateManifest


class TemplateLoader:
    """Renders phishing page templates with Jinja2."""

    def __init__(self, template_dir: Path, manifest: TemplateManifest) -> None:
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            autoescape=True,
        )
        self._manifest = manifest

    def render_login(self, **context) -> str:
        template = self._env.get_template("login.html")
        return template.render(fields=self._manifest.fields, **context)

    def render_error(self, **context) -> str:
        template = self._env.get_template("error.html")
        return template.render(fields=self._manifest.fields, **context)

    def render_2fa(self, **context) -> str:
        template = self._env.get_template("2fa.html")
        return template.render(**context)
