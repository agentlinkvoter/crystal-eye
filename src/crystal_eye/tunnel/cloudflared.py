from __future__ import annotations

from crystal_eye.tunnel.base import TunnelProvider


class CloudflaredTunnel(TunnelProvider):
    """Cloudflare Tunnel (cloudflared) integration — not yet implemented."""

    def __init__(self) -> None:
        self._url: str | None = None

    async def start(self, local_port: int, protocol: str = "http") -> str:
        raise NotImplementedError("Cloudflared tunnel support is coming soon.")

    async def stop(self) -> None:
        raise NotImplementedError("Cloudflared tunnel support is coming soon.")

    def get_url(self) -> str | None:
        return self._url

    @property
    def name(self) -> str:
        return "cloudflared"
