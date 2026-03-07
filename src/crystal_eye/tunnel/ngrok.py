from __future__ import annotations

from crystal_eye.tunnel.base import TunnelProvider


class NgrokTunnel(TunnelProvider):
    """ngrok tunnel via pyngrok (auto-downloads the binary)."""

    def __init__(self) -> None:
        super().__init__()
        self._tunnel = None

    @property
    def name(self) -> str:
        return "ngrok"

    @property
    def binary_name(self) -> str:
        return "ngrok"

    def is_installed(self) -> bool:
        return True

    def start(self, local_port: int, protocol: str = "http", auth_token: str | None = None) -> str:
        from pyngrok import conf, ngrok

        pyngrok_config = conf.get_default()
        pyngrok_config.log_level = "critical"
        if auth_token:
            pyngrok_config.auth_token = auth_token

        self._tunnel = ngrok.connect(local_port, "http", pyngrok_config=pyngrok_config)
        self._url = self._tunnel.public_url
        if self._url.startswith("http://"):
            self._url = self._url.replace("http://", "https://", 1)
        return self._url

    def stop(self) -> None:
        if self._tunnel:
            from pyngrok import ngrok

            ngrok.disconnect(self._tunnel.public_url)
            self._tunnel = None
        self._url = None

    @property
    def is_running(self) -> bool:
        return self._tunnel is not None
