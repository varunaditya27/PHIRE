from backend.app.config import Settings


def test_settings_lift_defaults():
    settings = Settings()
    assert settings.lift_model == "datalab-to/lift"
    assert settings.lift_device in ("auto", "cuda", "cpu")
    assert isinstance(settings.phire_mock_lift, bool)


def test_settings_lift_env_override(monkeypatch):
    monkeypatch.setenv("LIFT_MODEL", "custom/lift-model")
    monkeypatch.setenv("LIFT_DEVICE", "cpu")
    monkeypatch.setenv("PHIRE_MOCK_LIFT", "true")
    settings = Settings()
    assert settings.lift_model == "custom/lift-model"
    assert settings.lift_device == "cpu"
    assert settings.phire_mock_lift is True
