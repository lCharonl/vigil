"""Tests for the rule-toggle YAML config."""

from pathlib import Path

import yaml

from vigil.detect.data.rules_config import DEFAULT_RULES_CONFIG_PATH, RulesConfig, load_enabled_rules
from vigil.detect.registry import Rule


def test_default_config_enables_every_rule():
    enabled = load_enabled_rules()
    assert enabled == frozenset(Rule)


def test_every_registered_rule_has_a_toggle():
    parsed = RulesConfig.model_validate(
        yaml.safe_load(DEFAULT_RULES_CONFIG_PATH.read_text(encoding="utf-8"))
    )
    configured = {Rule(key.upper()) for key in parsed.rules}
    assert configured == set(Rule)


def test_missing_file_enables_every_rule():
    assert load_enabled_rules(Path("/nonexistent/rules.yml")) == frozenset(Rule)


def test_subset_disabled_is_excluded(tmp_path):
    path = tmp_path / "rules.yml"
    path.write_text("rules:\n  M-01: true\n  M-03: false\n", encoding="utf-8")
    assert load_enabled_rules(path) == frozenset({Rule.M_01})
