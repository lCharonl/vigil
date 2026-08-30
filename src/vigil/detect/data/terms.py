"""Lexical-term loading for the rules whose vocabulary lives in a YAML file."""

from pathlib import Path

import yaml
from pydantic import BaseModel

from vigil.detect.registry import Rule

DEFAULT_TERMS_PATH = Path("data/detection_terms.yml")

# rules whose terms live in data/detection_terms.yml
TERM_RULES: tuple[Rule, ...] = (Rule.R_04, Rule.L_01, Rule.L_02, Rule.L_04)


class DetectionTerms(BaseModel):
    terms: dict[str, list[str]]


def load_terms(path: Path | str = DEFAULT_TERMS_PATH) -> dict[Rule, frozenset[str]]:
    """Load lexical terms keyed by rule from the YAML file."""
    parsed = DetectionTerms.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
    result: dict[Rule, frozenset[str]] = {}
    for key, words in parsed.terms.items():
        result[Rule(key.upper())] = frozenset(w.strip().lower() for w in words)
    return result
