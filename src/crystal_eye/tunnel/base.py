from __future__ import annotations

from abc import ABC, abstractmethod


class TunnelProvider(ABC):
    """Abstract base for tunnel providers (cloudflared, ngrok, etc.)."""

    @abstractmethod
    async def start(self, local_port: int, protocol: str = "http") -> str:
        """Start tunnel and return the public URL."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Tear down the tunnel."""
        ...

    @abstractmethod
    def get_url(self) -> str | None:
        """Return the current public URL, or None if not running."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...
