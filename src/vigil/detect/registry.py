"""Rule and family registry: stable identifiers carried by every Reason."""

from enum import StrEnum


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
