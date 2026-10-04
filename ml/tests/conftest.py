"""Test defaults: run lift in mock mode so no test loads the real 9.7B VLM unless it opts in."""

import pytest


@pytest.fixture(autouse=True)
def _mock_lift_by_default(monkeypatch):
    """Tests that exercise the real extract path call monkeypatch.delenv themselves."""
    monkeypatch.setenv("PHIRE_MOCK_LIFT", "true")
