from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, Field


def get_state_dir() -> Path:
    path = Path.home() / ".crystal-eye"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_campaign_dir(campaign_name: str) -> Path:
    path = get_state_dir() / "campaigns" / campaign_name
    path.mkdir(parents=True, exist_ok=True)
    return path


class CrystalEyeConfig(BaseModel):
    """All runtime configuration for Crystal Eye."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    use_https: bool = False
    cert_path: str | None = None
    key_path: str | None = None

    # Template
    template: str | None = None

    # Campaign
    campaign: str | None = None

    # Behavior
    max_attempts: int = 2
    redirect_url: str | None = None
    verbose: bool = False
    enable_2fa: bool = False

    # Tunnel
    tunnel: str | None = None
    token: str | None = None

    # Paths
    templates_dir: str | None = None

    # Internal (not user-settable, not serialized)
    _active_campaign_id: int | None = None

    SETTABLE_KEYS: ClassVar[set[str]] = {
        "host",
        "port",
        "use_https",
        "template",
        "campaign",
        "max_attempts",
        "redirect_url",
        "verbose",
        "enable_2fa",
        "tunnel",
        "token",
    }

    def is_ready(self) -> bool:
        return self.template is not None and self.campaign is not None

    @property
    def campaign_dir(self) -> Path | None:
        if self.campaign:
            return get_campaign_dir(self.campaign)
        return None

    @property
    def db_path(self) -> str | None:
        if self.campaign:
            return str(get_campaign_dir(self.campaign) / "credentials.db")
        return None

    @property
    def exports_dir(self) -> Path | None:
        if self.campaign:
            d = get_campaign_dir(self.campaign) / "exports"
            d.mkdir(parents=True, exist_ok=True)
            return d
        return None

    def save(self, path: Path | None = None) -> None:
        path = path or get_state_dir() / "config.json"
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path | None = None) -> CrystalEyeConfig:
        path = path or get_state_dir() / "config.json"
        if path.exists():
            return cls.model_validate_json(path.read_text())
        return cls()
