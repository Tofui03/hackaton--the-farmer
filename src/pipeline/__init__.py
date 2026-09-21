from src.pipeline.schema import AuditOutputRecord, Discrepancy, HITLEscalation
from src.pipeline.stage1_classify import (
    Stage1Classifier,
    deterministic_classify_email,
    rule_based_classify,
)
from src.pipeline.stage2_extract import Stage2Extractor
from src.pipeline.stage3_compare import Stage3Comparator, rule_based_compare_audit
from src.pipeline.validator import validate_submission_dict

# Backward-compatibility alias
rule_based_compare = rule_based_compare_audit

__all__ = [
    "Stage1Classifier",
    "deterministic_classify_email",
    "rule_based_classify",
    "Stage2Extractor",
    "Stage3Comparator",
    "rule_based_compare",
    "rule_based_compare_audit",
    "validate_submission_dict",
    "AuditOutputRecord",
    "Discrepancy",
    "HITLEscalation",
]
