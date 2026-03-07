from __future__ import annotations

from pathlib import Path

import pytest

from crystal_eye.config import CrystalEyeConfig
from crystal_eye.db.engine import Database
from crystal_eye.db.repository import CampaignRepository, CredentialRepository
from crystal_eye.templates.registry import TemplateRegistry


@pytest.fixture
def db(tmp_path):
    db = Database(tmp_path / "test.db")
    db.connect()
    yield db
    db.close()


@pytest.fixture
def campaign_repo(db):
    return CampaignRepository(db)


@pytest.fixture
def cred_repo(db):
    return CredentialRepository(db)


@pytest.fixture
def config(tmp_path):
    return CrystalEyeConfig(
        campaign="test",
        templates_dir=str(Path(__file__).parent.parent / "templates"),
    )


@pytest.fixture
def template_registry():
    templates_dir = Path(__file__).parent.parent / "templates"
    registry = TemplateRegistry(templates_dir)
    registry.scan()
    return registry
