from __future__ import annotations

from crystal_eye.config import CrystalEyeConfig


def test_default_config():
    config = CrystalEyeConfig()
    assert config.host == "0.0.0.0"
    assert config.port == 8080
    assert config.use_https is False
    assert config.template is None
    assert config.campaign is None
    assert config.max_attempts == 2
    assert config.verbose is False


def test_is_ready():
    config = CrystalEyeConfig()
    assert config.is_ready() is False

    config.template = "facebook"
    assert config.is_ready() is False

    config.campaign = "test-campaign"
    assert config.is_ready() is True


def test_campaign_dir():
    config = CrystalEyeConfig(campaign="my-test")
    assert config.campaign_dir is not None
    assert "my-test" in str(config.campaign_dir)
    assert config.db_path is not None
    assert "my-test" in config.db_path


def test_no_campaign_no_paths():
    config = CrystalEyeConfig()
    assert config.campaign_dir is None
    assert config.db_path is None
    assert config.exports_dir is None


def test_save_and_load(tmp_path):
    config = CrystalEyeConfig(
        port=9090,
        template="facebook",
        campaign="test",
    )
    save_path = tmp_path / "config.json"
    config.save(save_path)

    loaded = CrystalEyeConfig.load(save_path)
    assert loaded.port == 9090
    assert loaded.template == "facebook"
    assert loaded.campaign == "test"


def test_load_nonexistent(tmp_path):
    config = CrystalEyeConfig.load(tmp_path / "nonexistent.json")
    assert config.port == 8080
