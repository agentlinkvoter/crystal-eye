from __future__ import annotations

import secrets
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from crystal_eye.config import CrystalEyeConfig
from crystal_eye.db.models import Credential
from crystal_eye.server.routes import register_routes
from crystal_eye.templates.loader import TemplateLoader
from crystal_eye.templates.registry import TemplateManifest


def create_app(
    config: CrystalEyeConfig,
    template_manifest: TemplateManifest,
    template_dir: Path,
    on_credential: Callable[[Credential], None],
) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    app.state.config = config
    app.state.manifest = template_manifest
    app.state.loader = TemplateLoader(template_dir, template_manifest)
    app.state.on_credential = on_credential
    app.state.attempt_tracker: dict[str, int] = {}

    static_dir = template_dir / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    register_routes(app)

    return app
