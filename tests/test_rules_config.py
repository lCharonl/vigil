"""Tests for the detection rules YAML config."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from vigil.detect.data.rules_config import load_detections
from vigil.detect.registry import Rule


def test_default_config_loads_valid_combinations():
    detections = load_detections()
    assert detections
    assert frozenset({Rule.R_03, Rule.M_01}) in detections


def test_missing_file_makes_every_rule_a_detection():
    detections = load_detections(Path("/nonexistent/rules.yml"))
    assert detections == [frozenset({rule}) for rule in Rule]


def test_combinations_are_read_case_insensitively(tmp_path):
    path = tmp_path / "rules.yml"
    path.write_text("detections:\n  - [r-03, M-01]\n  - [E-01]\n", encoding="utf-8")
    assert load_detections(path) == [frozenset({Rule.R_03, Rule.M_01}), frozenset({Rule.E_01})]


def test_unknown_rule_is_rejected(tmp_path):
    path = tmp_path / "rules.yml"
    path.write_text("detections:\n  - [X-99]\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_detections(path)


@pytest.mark.parametrize("body", ["detections: []\n", "detections:\n  - []\n"])
def test_empty_detections_are_rejected(tmp_path, body):
    path = tmp_path / "rules.yml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ValidationError):
        load_detections(path)
