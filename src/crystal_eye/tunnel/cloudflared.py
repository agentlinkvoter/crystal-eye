from __future__ import annotations

import re
import subprocess
import threading

from crystal_eye.tunnel.base import TunnelProvider


class CloudflaredTunnel(TunnelProvider):
    """Cloudflare quick tunnel via cloudflared."""

    @property
    def name(self) -> str:
        return "cloudflared"

    @property
    def binary_name(self) -> str:
        return "cloudflared"

    def start(self, local_port: int, protocol: str = "http", **kwargs) -> str:
        url = f"{protocol}://localhost:{local_port}"
        self._process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        # cloudflared prints the public URL to stderr
        event = threading.Event()

        def _read_stderr():
            for line in self._process.stderr:
                match = re.search(r"(https://[^\s|]+\.trycloudflare\.com)", line)
                if match:
                    self._url = match.group(1)
                    event.set()

        reader = threading.Thread(target=_read_stderr, daemon=True)
        reader.start()

        if not event.wait(timeout=15):
            self.stop()
            raise RuntimeError("Timed out waiting for cloudflared tunnel URL")

        return self._url
