from app.config import Settings


REQUIRED_ENV = {
    "PROWLARR_URL": "http://prowlarr:9696",
    "PROWLARR_API_KEY": "prowlarr-key",
    "CROSSSEED_URL": "http://cross-seed:2468",
    "CROSSSEED_API_KEY": "crossseed-key",
    "CROSSSEED_CONFIG_PATH": "/config",
}


def test_settings_reads_required_fields_from_env(monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    settings = Settings(_env_file=None)

    assert settings.prowlarr_url == "http://prowlarr:9696"
    assert settings.prowlarr_api_key == "prowlarr-key"
    assert settings.crossseed_url == "http://cross-seed:2468"
    assert settings.crossseed_api_key == "crossseed-key"
    assert str(settings.crossseed_config_path) == "/config"


def test_settings_optional_fields_default_to_none_or_false(monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    settings = Settings(_env_file=None)

    assert settings.sync_exclude_public is False
    assert settings.sync_exclude_tag is None
    assert settings.sync_interval_minutes is None
    assert settings.docker_manager_url is None


def test_settings_parses_optional_fields_from_env(monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("SYNC_EXCLUDE_PUBLIC", "true")
    monkeypatch.setenv("SYNC_EXCLUDE_TAG", "no-cross-seed")
    monkeypatch.setenv("SYNC_INTERVAL_MINUTES", "60")
    monkeypatch.setenv("DOCKER_MANAGER_URL", "https://portainer.example.com")

    settings = Settings(_env_file=None)

    assert settings.sync_exclude_public is True
    assert settings.sync_exclude_tag == "no-cross-seed"
    assert settings.sync_interval_minutes == 60
    assert settings.docker_manager_url == "https://portainer.example.com"
