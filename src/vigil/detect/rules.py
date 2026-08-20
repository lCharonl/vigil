"""Rule and family registry, plus lexical-term loading."""

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel

DEFAULT_TERMS_PATH = Path("data/detection_terms.yml")


class Family(StrEnum):
    REFERENTIAL = "referential"
    LEXICAL = "lexical"
    ENCODING = "encoding"
    MORPHOLOGICAL = "morphological"
    STATISTICAL = "statistical"
    CERTIFICATE_METADATA = "certificate_metadata"


class Rule(StrEnum):
    R_01 = "R-01"
    R_02 = "R-02"
    R_03 = "R-03"
    R_04 = "R-04"
    L_01 = "L-01"
    L_02 = "L-02"
    L_03 = "L-03"
    L_04 = "L-04"
    E_01 = "E-01"
    E_02 = "E-02"
    M_01 = "M-01"
    M_02 = "M-02"
    M_03 = "M-03"
    M_04 = "M-04"
    S_01 = "S-01"
    S_02 = "S-02"
    S_03 = "S-03"
    C_01 = "C-01"


# family per rule, in evaluation order (decreasing specificity within a family)
RULE_FAMILY: dict[Rule, Family] = {
    Rule.R_01: Family.REFERENTIAL,
    Rule.R_02: Family.REFERENTIAL,
    Rule.R_03: Family.REFERENTIAL,
    Rule.R_04: Family.REFERENTIAL,
    Rule.L_01: Family.LEXICAL,
    Rule.L_02: Family.LEXICAL,
    Rule.L_03: Family.LEXICAL,
    Rule.L_04: Family.LEXICAL,
    Rule.E_01: Family.ENCODING,
    Rule.E_02: Family.ENCODING,
    Rule.M_01: Family.MORPHOLOGICAL,
    Rule.M_02: Family.MORPHOLOGICAL,
    Rule.M_03: Family.MORPHOLOGICAL,
    Rule.M_04: Family.MORPHOLOGICAL,
    Rule.S_01: Family.STATISTICAL,
    Rule.S_02: Family.STATISTICAL,
    Rule.S_03: Family.STATISTICAL,
    Rule.C_01: Family.CERTIFICATE_METADATA,
}

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
