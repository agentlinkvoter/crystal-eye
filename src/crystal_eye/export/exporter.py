from __future__ import annotations

import csv
import json
from pathlib import Path

from crystal_eye.db.models import Credential
from crystal_eye.db.repository import CampaignRepository, CredentialRepository


class Exporter:
    def __init__(
        self,
        cred_repo: CredentialRepository,
        campaign_repo: CampaignRepository,
    ) -> None:
        self._cred_repo = cred_repo
        self._campaign_repo = campaign_repo

    def to_csv(
        self,
        campaign_name: str | None = None,
        output_path: Path | None = None,
    ) -> Path:
        creds = self._get_credentials(campaign_name)
        output_path = output_path or Path(f"crystal_eye_export_{campaign_name or 'all'}.csv")

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)

            # Collect all field names across all credentials
            all_field_names: list[str] = []
            for cred in creds:
                for key in cred.fields:
                    if key not in all_field_names:
                        all_field_names.append(key)

            header = ["id", "campaign_id", "template", *all_field_names, "source_ip", "user_agent", "captured_at"]
            writer.writerow(header)

            for cred in creds:
                row = [
                    cred.id,
                    cred.campaign_id,
                    cred.template,
                    *[cred.fields.get(name, "") for name in all_field_names],
                    cred.source_ip,
                    cred.user_agent,
                    cred.captured_at.isoformat(),
                ]
                writer.writerow(row)

        return output_path

    def to_json(
        self,
        campaign_name: str | None = None,
        output_path: Path | None = None,
    ) -> Path:
        creds = self._get_credentials(campaign_name)
        output_path = output_path or Path(f"crystal_eye_export_{campaign_name or 'all'}.json")

        data = [
            {
                "id": cred.id,
                "campaign_id": cred.campaign_id,
                "template": cred.template,
                "fields": cred.fields,
                "source_ip": cred.source_ip,
                "user_agent": cred.user_agent,
                "captured_at": cred.captured_at.isoformat(),
            }
            for cred in creds
        ]

        output_path.write_text(json.dumps(data, indent=2))
        return output_path

    def _get_credentials(self, campaign_name: str | None) -> list[Credential]:
        if campaign_name:
            campaign = self._campaign_repo.get_by_name(campaign_name)
            if campaign and campaign.id is not None:
                return self._cred_repo.get_by_campaign(campaign.id)
            return []
        return self._cred_repo.get_all()
