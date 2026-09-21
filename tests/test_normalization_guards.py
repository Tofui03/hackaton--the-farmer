from __future__ import annotations

"""Negative Normalization Regression Guards (DEC-P06C / DEC-P06D / DEC-P06E).

GOVERNANCE INVARIANTS:
These regression guards protect CURRENT baseline behavior only. They verify that
normalization preserves strict canonical DISTINCTNESS between values that must not
be conflated by unauthorized semantic equivalence, alias translation, suffix
stripping, or numeric tolerances.

Comparator outcomes (MATCH / MISMATCH) are NOT derived or instantiated in T03;
the Stage 4 Deterministic Comparator (T04) is expected to derive MISMATCH from
these distinct canonical values later.

These tests remain amendment-sensitive and do NOT resolve the DEC-P06C, DEC-P06D,
or DEC-P06E TBD decisions autonomously.
"""

from decimal import Decimal
import pytest

from src.normalization import normalize_gross_weight_kg, normalize_text


def test_reg_004_no_undocumented_weight_tolerance() -> None:
    """REG-004 / REG-NORM-001 (DEC-P06E): No undocumented ±1kg numeric tolerance.

    SI: 22000 kg vs BL: 22001 kg.
    Enforces exact Decimal equality after approved unit normalization.
    Normalization preserves strict canonical distinctness.
    T04 is expected to derive MISMATCH from these distinct canonical values later.
    Protects CURRENT baseline behavior only; amendment-sensitive; does NOT resolve DEC-P06E TBD.
    """
    si_norm = normalize_gross_weight_kg("22000 kg")
    bl_norm = normalize_gross_weight_kg("22001 kg")

    assert si_norm.state == "VALID"
    assert bl_norm.state == "VALID"
    assert si_norm.value == Decimal("22000")
    assert bl_norm.value == Decimal("22001")

    # Canonical values must be strictly distinct: no tolerance collapsed them into equality
    assert si_norm.value != bl_norm.value


def test_reg_006_no_port_semantic_equivalence() -> None:
    """REG-006 / REG-NORM-002 (DEC-P06C): No automatic port/city/terminal equivalence.

    SI: 'SHANGHAI' vs BL: 'PORT OF SHANGHAI'.
    Enforces exact equality after currently approved normalization; no automatic port alias,
    UN/LOCODE, city, or terminal equivalence.
    Normalization preserves strict canonical distinctness.
    T04 is expected to derive MISMATCH from these distinct canonical values later.
    Protects CURRENT baseline behavior only; amendment-sensitive; does NOT resolve DEC-P06C TBD.
    """
    si_norm = normalize_text("port_of_loading", "SHANGHAI")
    bl_norm = normalize_text("port_of_loading", "PORT OF SHANGHAI")

    assert si_norm.state == "VALID"
    assert bl_norm.state == "VALID"
    assert si_norm.value == "SHANGHAI"
    assert bl_norm.value == "PORT OF SHANGHAI"

    # Canonical values must be strictly distinct: no port aliasing collapsed them into equality
    assert si_norm.value != bl_norm.value


def test_reg_005_no_organization_name_equivalence() -> None:
    """REG-005 / REG-NORM-003 (DEC-P06D): No broad legal-suffix stripping.

    SI: 'ACME CORP' vs BL: 'ACME CORPORATION'.
    Enforces exact equality after currently approved normalization; no broad legal-suffix stripping;
    no token reordering or organization alias equivalence.
    Normalization preserves strict canonical distinctness.
    T04 is expected to derive MISMATCH from these distinct canonical values later.
    Protects CURRENT baseline behavior only; amendment-sensitive; does NOT resolve DEC-P06D TBD.
    """
    si_norm = normalize_text("shipper", "ACME CORP")
    bl_norm = normalize_text("shipper", "ACME CORPORATION")

    assert si_norm.state == "VALID"
    assert bl_norm.state == "VALID"
    assert si_norm.value == "ACME CORP"
    assert bl_norm.value == "ACME CORPORATION"

    # Canonical values must be strictly distinct: no suffix stripping collapsed them into equality
    assert si_norm.value != bl_norm.value
