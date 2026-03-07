from __future__ import annotations

from crystal_eye.db.models import Credential


def test_create_campaign(campaign_repo):
    campaign = campaign_repo.create("test-campaign", "facebook")
    assert campaign.id is not None
    assert campaign.name == "test-campaign"
    assert campaign.template == "facebook"
    assert campaign.is_active is True


def test_get_campaign_by_name(campaign_repo):
    campaign_repo.create("my-test", "facebook")
    found = campaign_repo.get_by_name("my-test")
    assert found is not None
    assert found.name == "my-test"


def test_get_campaign_not_found(campaign_repo):
    assert campaign_repo.get_by_name("nonexistent") is None


def test_list_campaigns(campaign_repo):
    campaign_repo.create("camp1", "facebook")
    campaign_repo.create("camp2", "facebook")
    campaigns = campaign_repo.list_all()
    assert len(campaigns) == 2


def test_deactivate_campaign(campaign_repo):
    campaign = campaign_repo.create("test", "facebook")
    campaign_repo.deactivate(campaign.id)
    found = campaign_repo.get_by_name("test")
    assert found.is_active is False


def test_save_credential(campaign_repo, cred_repo):
    campaign = campaign_repo.create("test", "facebook")
    cred = Credential(
        campaign_id=campaign.id,
        fields={"email": "user@example.com", "pass": "secret123"},
        source_ip="127.0.0.1",
        user_agent="TestAgent/1.0",
    )
    saved = cred_repo.save(cred)
    assert saved.id is not None


def test_get_credentials_by_campaign(campaign_repo, cred_repo):
    campaign = campaign_repo.create("test", "facebook")
    cred_repo.save(Credential(
        campaign_id=campaign.id,
        fields={"email": "a@b.com", "pass": "123"},
        source_ip="127.0.0.1",
    ))
    cred_repo.save(Credential(
        campaign_id=campaign.id,
        fields={"email": "c@d.com", "pass": "456"},
        source_ip="127.0.0.1",
    ))
    creds = cred_repo.get_by_campaign(campaign.id)
    assert len(creds) == 2
    assert creds[0].fields["email"] in ("a@b.com", "c@d.com")


def test_count_credentials(campaign_repo, cred_repo):
    campaign = campaign_repo.create("test", "facebook")
    assert cred_repo.count_by_campaign(campaign.id) == 0

    cred_repo.save(Credential(
        campaign_id=campaign.id,
        fields={"email": "x@y.com", "pass": "pw"},
        source_ip="127.0.0.1",
    ))
    assert cred_repo.count_by_campaign(campaign.id) == 1
