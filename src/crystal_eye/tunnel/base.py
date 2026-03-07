from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod


class TunnelProvider(ABC):
    """Abstract base for tunnel providers (cloudflared, ngrok, etc.)."""

    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None
        self._url: str | None = None

    @abstractmethod
    def start(self, local_port: int, protocol: str = "http") -> str:
        """Start tunnel and return the public URL."""
        ...

    def stop(self) -> None:
        """Tear down the tunnel."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        self._url = None

    def get_url(self) -> str | None:
        """Return the current public URL, or None if not running."""
        return self._url

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...

    @property
    @abstractmethod
    def binary_name(self) -> str:
        """Name of the CLI binary to look for."""
        ...

    def is_installed(self) -> bool:
        return shutil.which(self.binary_name) is not None
