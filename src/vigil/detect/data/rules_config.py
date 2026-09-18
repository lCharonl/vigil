"""Rule enable/disable loading from a YAML config file."""

from pathlib import Path

import yaml
from pydantic import BaseModel

from vigil.detect.registry import Rule

DEFAULT_RULES_CONFIG_PATH = Path("data/rules.yml")


class RulesConfig(BaseModel):
    rules: dict[str, bool]


def load_enabled_rules(path: Path | str = DEFAULT_RULES_CONFIG_PATH) -> frozenset[Rule]:
    """Rules enabled in the config file, or every rule if the file is missing."""
    path = Path(path)
    if not path.exists():
        return frozenset(Rule)
    parsed = RulesConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    return frozenset(Rule(key.upper()) for key, enabled in parsed.rules.items() if enabled)
