from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from pathlib import Path

import uvicorn

from crystal_eye.config import CrystalEyeConfig
from crystal_eye.db.models import Credential
from crystal_eye.server.app import create_app
from crystal_eye.templates.registry import TemplateManifest


class ServerRunner:
    """Manages the FastAPI/uvicorn server in a background daemon thread."""

    def __init__(
        self,
        config: CrystalEyeConfig,
        template_manifest: TemplateManifest,
        template_dir: Path,
        on_credential: Callable[[Credential], None],
    ) -> None:
        self._config = config
        self._template_manifest = template_manifest
        self._template_dir = template_dir
        self._on_credential = on_credential
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        app = create_app(
            config=self._config,
            template_manifest=self._template_manifest,
            template_dir=self._template_dir,
            on_credential=self._on_credential,
        )
        uv_config = uvicorn.Config(
            app,
            host=self._config.host,
            port=self._config.port,
            ssl_keyfile=self._config.key_path if self._config.use_https else None,
            ssl_certfile=self._config.cert_path if self._config.use_https else None,
            log_level="info" if self._config.verbose else "error",
        )
        self._server = uvicorn.Server(uv_config)
        self._thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="crystal-eye-server",
        )
        self._thread.start()

    def _run_server(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._server.serve())

    def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
            self._server = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
