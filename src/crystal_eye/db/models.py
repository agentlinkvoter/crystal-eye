from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Campaign:
    id: int | None = None
    name: str = ""
    template: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True


@dataclass
class Credential:
    id: int | None = None
    campaign_id: int = 0
    fields: dict[str, str] = field(default_factory=dict)
    source_ip: str = ""
    user_agent: str = ""
    captured_at: datetime = field(default_factory=datetime.now)
