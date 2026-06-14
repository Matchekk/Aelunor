"""Second Brain is part of the default fast runtime: default ON, with an
escape hatch. These tests pin the flag semantics from app.config.feature_flags.
"""
import pytest

from app.config.feature_flags import second_brain_enabled


def test_second_brain_on_by_default(monkeypatch):
    monkeypatch.delenv("AELUNOR_SECOND_BRAIN", raising=False)
    assert second_brain_enabled() is True


def test_second_brain_empty_string_is_on(monkeypatch):
    # An empty value is treated as "unset" -> default ON.
    monkeypatch.setenv("AELUNOR_SECOND_BRAIN", "")
    assert second_brain_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "off", "no", "FALSE", "Off", " 0 "])
def test_escape_hatch_disables(monkeypatch, value):
    monkeypatch.setenv("AELUNOR_SECOND_BRAIN", value)
    assert second_brain_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "on", "yes", "anything-else"])
def test_truthy_and_other_values_stay_on(monkeypatch, value):
    monkeypatch.setenv("AELUNOR_SECOND_BRAIN", value)
    assert second_brain_enabled() is True
