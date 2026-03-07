from __future__ import annotations

import json
from datetime import datetime

from crystal_eye.db.engine import Database
from crystal_eye.db.models import Campaign, Credential


class CampaignRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, name: str, template: str) -> Campaign:
        cursor = self._db.execute(
            "INSERT INTO campaigns (name, template) VALUES (?, ?)",
            (name, template),
        )
        return Campaign(
            id=cursor.lastrowid,
            name=name,
            template=template,
            created_at=datetime.now(),
            is_active=True,
        )

    def get_by_name(self, name: str) -> Campaign | None:
        row = self._db.fetchone("SELECT * FROM campaigns WHERE name = ?", (name,))
        if row is None:
            return None
        return self._row_to_campaign(row)

    def get_by_id(self, campaign_id: int) -> Campaign | None:
        row = self._db.fetchone("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        if row is None:
            return None
        return self._row_to_campaign(row)

    def list_all(self) -> list[Campaign]:
        rows = self._db.fetchall("SELECT * FROM campaigns ORDER BY created_at DESC")
        return [self._row_to_campaign(r) for r in rows]

    def deactivate(self, campaign_id: int) -> None:
        self._db.execute(
            "UPDATE campaigns SET is_active = 0 WHERE id = ?",
            (campaign_id,),
        )

    @staticmethod
    def _row_to_campaign(row) -> Campaign:
        return Campaign(
            id=row["id"],
            name=row["name"],
            template=row["template"],
            created_at=datetime.fromisoformat(row["created_at"]),
            is_active=bool(row["is_active"]),
        )


class CredentialRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def merge_by_ip(self, credential: Credential) -> Credential | None:
        """Find the most recent credential from the same IP and merge fields into it."""
        row = self._db.fetchone(
            "SELECT * FROM credentials WHERE campaign_id = ? AND source_ip = ? "
            "ORDER BY captured_at DESC LIMIT 1",
            (credential.campaign_id, credential.source_ip),
        )
        if row is None:
            return None

        existing = self._row_to_credential(row)
        existing.fields.update(credential.fields)
        self._db.execute(
            "UPDATE credentials SET fields_json = ? WHERE id = ?",
            (json.dumps(existing.fields), existing.id),
        )
        return existing

    def save(self, credential: Credential) -> Credential:
        cursor = self._db.execute(
            "INSERT INTO credentials (campaign_id, template, fields_json, source_ip, user_agent) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                credential.campaign_id,
                credential.template,
                json.dumps(credential.fields),
                credential.source_ip,
                credential.user_agent,
            ),
        )
        credential.id = cursor.lastrowid
        return credential

    def get_by_campaign(self, campaign_id: int) -> list[Credential]:
        rows = self._db.fetchall(
            "SELECT * FROM credentials WHERE campaign_id = ? ORDER BY captured_at DESC",
            (campaign_id,),
        )
        return [self._row_to_credential(r) for r in rows]

    def get_all(self) -> list[Credential]:
        rows = self._db.fetchall("SELECT * FROM credentials ORDER BY captured_at DESC")
        return [self._row_to_credential(r) for r in rows]

    def count_by_campaign(self, campaign_id: int) -> int:
        row = self._db.fetchone(
            "SELECT COUNT(*) as cnt FROM credentials WHERE campaign_id = ?",
            (campaign_id,),
        )
        return row["cnt"] if row else 0

    @staticmethod
    def _row_to_credential(row) -> Credential:
        return Credential(
            id=row["id"],
            campaign_id=row["campaign_id"],
            template=row["template"] if "template" in row.keys() else "",
            fields=json.loads(row["fields_json"]),
            source_ip=row["source_ip"],
            user_agent=row["user_agent"],
            captured_at=datetime.fromisoformat(row["captured_at"]),
        )
