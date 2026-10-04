"""Detection rules (rule-id combinations) loaded from a YAML config file."""

from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator

from vigil.detect.registry import Rule

DEFAULT_RULES_CONFIG_PATH = Path("data/rules.yml")

Detection = frozenset[Rule]


class RulesConfig(BaseModel):
    detections: list[list[str]]

    @field_validator("detections")
    @classmethod
    def _non_empty(cls, value: list[list[str]]) -> list[list[str]]:
        if not value or any(not combo for combo in value):
            raise ValueError("detections must be a non-empty list of non-empty rule lists")
        return value


def load_detections(path: Path | str = DEFAULT_RULES_CONFIG_PATH) -> list[Detection]:
    """Rule combinations to report, or every rule alone if the file is missing."""
    path = Path(path)
    if not path.exists():
        return [frozenset({rule}) for rule in Rule]
    parsed = RulesConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    return [frozenset(Rule(rule_id.upper()) for rule_id in combo) for combo in parsed.detections]
