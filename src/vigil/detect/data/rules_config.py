"""Rule toggles and scoring points loaded from a YAML config file."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from vigil.detect.registry import Rule

DEFAULT_RULES_CONFIG_PATH = Path("data/rules.yml")


class RuleSetting(BaseModel):
    enabled: bool = True
    points: int = Field(default=0, ge=0)


class RulesConfig(BaseModel):
    rules: dict[str, RuleSetting]


def load_rule_points(path: Path | str = DEFAULT_RULES_CONFIG_PATH) -> dict[Rule, int]:
    """Points of each enabled rule, or every rule at 0 points if the file is missing."""
    path = Path(path)
    if not path.exists():
        return dict.fromkeys(Rule, 0)
    parsed = RulesConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    return {
        Rule(key.upper()): setting.points
        for key, setting in parsed.rules.items()
        if setting.enabled
    }
