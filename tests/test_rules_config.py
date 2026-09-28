"""Tests for the rule toggles and points YAML config."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from vigil.detect.data.rules_config import DEFAULT_RULES_CONFIG_PATH, RulesConfig, load_rule_points
from vigil.detect.registry import Rule


def test_default_config_enables_every_rule():
    assert set(load_rule_points()) == set(Rule)


def test_every_registered_rule_has_a_setting():
    parsed = RulesConfig.model_validate(
        yaml.safe_load(DEFAULT_RULES_CONFIG_PATH.read_text(encoding="utf-8"))
    )
    configured = {Rule(key.upper()) for key in parsed.rules}
    assert configured == set(Rule)


def test_missing_file_enables_every_rule_at_zero_points():
    assert load_rule_points(Path("/nonexistent/rules.yml")) == dict.fromkeys(Rule, 0)


def test_disabled_rule_is_excluded_and_points_are_read(tmp_path):
    path = tmp_path / "rules.yml"
    path.write_text(
        "rules:\n  M-01: {enabled: true, points: 7}\n  M-03: {enabled: false, points: 5}\n",
        encoding="utf-8",
    )
    assert load_rule_points(path) == {Rule.M_01: 7}


def test_negative_points_are_rejected(tmp_path):
    path = tmp_path / "rules.yml"
    path.write_text("rules:\n  M-01: {points: -1}\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_rule_points(path)
