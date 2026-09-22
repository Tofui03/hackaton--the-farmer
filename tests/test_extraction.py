from __future__ import annotations

from decimal import Decimal
import pytest

from src.models.extraction import DocumentExtraction, FieldReliability
from src.pipeline.stage3_extract import (
    Stage3Extractor,
    extract_fields_from_text,
)
from tests.mocks.mock_ai_adapter import MockAIAdapter


SAMPLE_FULL_DOC = """
Shipper: ACME EXPORTS LTD
123 INDUSTRIAL WAY
SINGAPORE 068896

Consignee:
AL GURG STATIONERY LLC
P.O. BOX 5069
DUBAI, UNITED ARAB EMIRATES

Notify Party:
SAME AS CONSIGNEE

Port of Loading: SHANGHAI (CNSHA)
Port of Discharge: ROTTERDAM, NETHERLANDS
Container Count: 2 X 40HC, 1 X 20GP
Gross Weight: 25,432.50 KGS
Description: PAPER PRODUCTS
"""


def test_ut_ext_001_standard_field_extraction():
    """UT-EXT-001 / FR-010: Standard field extraction for shipper."""
    text = "Shipper: ACME EXPORTS LTD\nConsignee: GLOBAL BUYER INC\n"
    extractor = Stage3Extractor()
    doc_ext, evidence = extractor.extract_document_fields("doc_01", "SI", text)

    shipper_field = doc_ext.fields["shipper"]
    assert shipper_field.reliability == FieldReliability.RELIABLE
    assert shipper_field.selected_candidate == 0
    assert shipper_field.candidates[0].raw_value == "ACME EXPORTS LTD"
    assert shipper_field.normalized is not None
    assert shipper_field.normalized.value == "ACME EXPORTS LTD"
    assert len(evidence) >= 1


def test_ut_ext_002_alternative_field_labels():
    """UT-EXT-002 / FR-010: Alternative field label 'Consignor / Exporter'."""
    text = "Consignor / Exporter: GLOBAL TRADE CORP\nConsignee: RECEIVER CO\n"
    extractor = Stage3Extractor()
    doc_ext, evidence = extractor.extract_document_fields("doc_02", "SI", text)

    shipper_field = doc_ext.fields["shipper"]
    assert shipper_field.reliability == FieldReliability.RELIABLE
    assert shipper_field.candidates[0].raw_value == "GLOBAL TRADE CORP"
    assert shipper_field.normalized is not None
    assert shipper_field.normalized.value == "GLOBAL TRADE CORP"


def test_ut_ext_003_multiline_address_preservation():
    """UT-EXT-003 / FR-010: Preserves full multi-line corporate address block without truncation."""
    text = (
        "Consignee:\n"
        "AL GURG STATIONERY LLC\n"
        "P.O. BOX 5069\n"
        "DUBAI, UNITED ARAB EMIRATES\n\n"
        "Notify Party: SAME AS CONSIGNEE\n"
    )
    extractor = Stage3Extractor()
    doc_ext, evidence = extractor.extract_document_fields("doc_03", "BL", text)

    consignee_field = doc_ext.fields["consignee"]
    assert consignee_field.reliability == FieldReliability.RELIABLE
    expected_address = (
        "AL GURG STATIONERY LLC\n"
        "P.O. BOX 5069\n"
        "DUBAI, UNITED ARAB EMIRATES"
    )
    assert consignee_field.candidates[0].raw_value == expected_address
    # Normalized collapses whitespace per DEC-P06A
    assert "AL GURG STATIONERY LLC" in consignee_field.normalized.value
    assert "DUBAI, UNITED ARAB EMIRATES" in consignee_field.normalized.value


def test_ut_ext_004_notify_party_same_as_consignee():
    """UT-EXT-004 / FR-010: Literal 'SAME AS CONSIGNEE' preserved as raw value."""
    text = "Notify Party: SAME AS CONSIGNEE\nConsignee: ACME TRADING\n"
    extractor = Stage3Extractor()
    doc_ext, _ = extractor.extract_document_fields("doc_04", "SI", text)

    np_field = doc_ext.fields["notify_party"]
    assert np_field.reliability == FieldReliability.RELIABLE
    assert np_field.candidates[0].raw_value == "SAME AS CONSIGNEE"
    assert np_field.normalized.value == "SAME AS CONSIGNEE"


def test_ut_ext_005_port_of_loading_with_code():
    """UT-EXT-005 / FR-010: Port of Loading with code: raw text and port name/code preserved."""
    text = "PORT OF LOADING: SHANGHAI (CNSHA)\nPORT OF DISCHARGE: ROTTERDAM\n"
    extractor = Stage3Extractor()
    doc_ext, _ = extractor.extract_document_fields("doc_05", "SI", text)

    pol_field = doc_ext.fields["port_of_loading"]
    assert pol_field.reliability == FieldReliability.RELIABLE
    assert pol_field.candidates[0].raw_value == "SHANGHAI (CNSHA)"
    assert pol_field.normalized.value == "SHANGHAI (CNSHA)"


def test_ut_ext_006_port_of_discharge_alternative_label():
    """UT-EXT-006 / FR-010: Alternative label 'Discharge Port: ROTTERDAM, NETHERLANDS'."""
    text = "Discharge Port: ROTTERDAM, NETHERLANDS\nPort of Loading: SINGAPORE\n"
    extractor = Stage3Extractor()
    doc_ext, _ = extractor.extract_document_fields("doc_06", "BL", text)

    pod_field = doc_ext.fields["port_of_discharge"]
    assert pod_field.reliability == FieldReliability.RELIABLE
    assert pod_field.candidates[0].raw_value == "ROTTERDAM, NETHERLANDS"
    assert pod_field.normalized.value == "ROTTERDAM, NETHERLANDS"


def test_ut_ext_007_container_count_spelled_words():
    """UT-EXT-007 / FR-010: Container count in words 'Three (3) Containers' -> integer 3."""
    text = "Container Count: Three (3) Containers\nGross Weight: 25000 KG\n"
    extractor = Stage3Extractor()
    doc_ext, _ = extractor.extract_document_fields("doc_07", "SI", text)

    cnt_field = doc_ext.fields["container_count"]
    assert cnt_field.reliability == FieldReliability.RELIABLE
    assert cnt_field.candidates[0].raw_value == "Three (3) Containers"
    assert cnt_field.normalized.value == 3
    assert isinstance(cnt_field.normalized.value, int)


def test_ut_ext_008_container_count_multi_size_sum():
    """UT-EXT-008 / FR-010: Container count multi-size notation '2 X 40HC, 1 X 20GP' -> sum 3."""
    text = "Number of Containers: 2 X 40HC, 1 X 20GP\nGross Weight: 22000 KG\n"
    extractor = Stage3Extractor()
    doc_ext, _ = extractor.extract_document_fields("doc_08", "BL", text)

    cnt_field = doc_ext.fields["container_count"]
    assert cnt_field.reliability == FieldReliability.RELIABLE
    assert cnt_field.candidates[0].raw_value == "2 X 40HC, 1 X 20GP"
    assert cnt_field.normalized.value == 3


def test_ut_ext_009_gross_weight_metric_tons():
    """UT-EXT-009 / FR-010: Gross weight in metric tons 'G.W.: 25 MT' -> Decimal('25000')."""
    text = "G.W.: 25 MT\nContainer Count: 2\n"
    extractor = Stage3Extractor()
    doc_ext, _ = extractor.extract_document_fields("doc_09", "SI", text)

    gw_field = doc_ext.fields["gross_weight_kg"]
    assert gw_field.reliability == FieldReliability.RELIABLE
    assert gw_field.candidates[0].raw_value == "25 MT"
    assert gw_field.normalized.value == Decimal("25000")
    assert isinstance(gw_field.normalized.value, Decimal)


def test_ut_ext_010_gross_weight_comma_separators():
    """UT-EXT-010 / FR-010: Gross weight with comma separators 'Gross Weight: 25,432.50 KGS'."""
    text = "Gross Weight: 25,432.50 KGS\nContainer Count: 3\n"
    extractor = Stage3Extractor()
    doc_ext, _ = extractor.extract_document_fields("doc_10", "BL", text)

    gw_field = doc_ext.fields["gross_weight_kg"]
    assert gw_field.reliability == FieldReliability.RELIABLE
    assert gw_field.candidates[0].raw_value == "25,432.50 KGS"
    assert gw_field.normalized.value == Decimal("25432.50")


def test_ut_ext_011_missing_mandatory_field_escalates():
    """UT-EXT-011 / FR-010 / FR-014: Mandatory field completely absent from document."""
    # Text lacks container_count
    text = (
        "Shipper: ACME EXPORTS LTD\n"
        "Consignee: GLOBAL TRADE CORP\n"
        "Port of Loading: SINGAPORE\n"
        "Port of Discharge: ROTTERDAM\n"
        "Gross Weight: 25000 KG\n"
    )
    extractor = Stage3Extractor()
    doc_ext, _ = extractor.extract_document_fields("doc_11", "SI", text)

    cnt_field = doc_ext.fields["container_count"]
    assert cnt_field.reliability == FieldReliability.MISSING
    assert cnt_field.candidates == []
    assert cnt_field.selected_candidate is None
    assert cnt_field.normalized is None
    assert "absent" in cnt_field.explanation.lower()


def test_ut_ext_012_strict_evidence_grounding_all_seven_fields():
    """UT-EXT-012 / DEC-AI-P05 / DC-05: Every extracted field links to verbatim quote in text."""
    extractor = Stage3Extractor()
    doc_ext, evidence = extractor.extract_document_fields("doc_12", "SI", SAMPLE_FULL_DOC)

    ev_map = {e.evidence_id: e for e in evidence}

    for field_name, ext_field in doc_ext.fields.items():
        assert ext_field.reliability == FieldReliability.RELIABLE
        assert ext_field.selected_candidate is not None
        selected = ext_field.candidates[ext_field.selected_candidate]
        assert len(selected.evidence_ids) >= 1

        for ev_id in selected.evidence_ids:
            assert ev_id in ev_map
            ev = ev_map[ev_id]
            assert ev.kind == "text_span"
            assert ev.quote is not None
            # Strict verbatim grounding check (UT-EXT-012)
            assert ev.quote.lower() in SAMPLE_FULL_DOC.lower()


def test_ut_ext_013_evidence_hallucination_rejection():
    """UT-EXT-013 / DEC-AI-P05 / REG-011: Mock LLM hallucinated quote is rejected as ungrounded."""
    # Document contains no container count
    text = (
        "Shipper: ACME EXPORTS LTD\n"
        "Consignee: GLOBAL BUYER INC\n"
        "Port of Loading: SINGAPORE\n"
        "Port of Discharge: ROTTERDAM\n"
        "Gross Weight: 22000 KG\n"
    )

    # Mock AI adapter returning hallucinated container count quote that doesn't exist in text
    mock_adapter = MockAIAdapter(
        default_response={
            "document_id": "doc_13",
            "role": "SI",
            "fields": {
                "container_count": {
                    "raw_value": "5",
                    "status": "FOUND",
                    "evidence": "Total Container Count: 5 Units in Yard",  # Hallucinated! Not in text!
                }
            },
        }
    )

    extractor = Stage3Extractor(ai_adapter=mock_adapter)
    doc_ext, _ = extractor.extract_document_fields("doc_13", "SI", text)

    # Hallucinated quote must be rejected; container_count remains MISSING
    cnt_field = doc_ext.fields["container_count"]
    assert cnt_field.reliability == FieldReliability.MISSING


def test_hitl_part_001_and_reg_009_partial_work_preservation():
    """HITL-PART-001 / REG-009 / DEC-AI-P04: When 1 field fails gate, passing 6 fields are preserved."""
    # SI has all 7 fields
    si_text = SAMPLE_FULL_DOC

    # BL lacks container_count, but other 6 fields are identical to SI
    bl_text = (
        "Shipper: ACME EXPORTS LTD\n"
        "123 INDUSTRIAL WAY\n"
        "SINGAPORE 068896\n\n"
        "Consignee:\n"
        "AL GURG STATIONERY LLC\n"
        "P.O. BOX 5069\n"
        "DUBAI, UNITED ARAB EMIRATES\n\n"
        "Notify Party:\n"
        "SAME AS CONSIGNEE\n\n"
        "Port of Loading: SHANGHAI (CNSHA)\n"
        "Port of Discharge: ROTTERDAM, NETHERLANDS\n"
        "Gross Weight: 25,432.50 KGS\n"
        "Description: PAPER PRODUCTS\n"
    )

    extractor = Stage3Extractor()
    si_ext, _ = extractor.extract_document_fields("si_doc", "SI", si_text)
    bl_ext, _ = extractor.extract_document_fields("bl_doc", "BL", bl_text)

    assert si_ext.fields["container_count"].reliability == FieldReliability.RELIABLE
    assert bl_ext.fields["container_count"].reliability == FieldReliability.MISSING

    # 1. SI extraction has all 7 reliable fields
    assert all(f.reliability == FieldReliability.RELIABLE for f in si_ext.fields.values())

    # 2. BL extraction preserves exactly the 6 reliable fields
    assert bl_ext.fields["container_count"].reliability == FieldReliability.MISSING
    assert bl_ext.fields["container_count"].normalized is None

    reliable_bl_fields = {
        name for name, f in bl_ext.fields.items() if f.reliability == FieldReliability.RELIABLE
    }
    assert reliable_bl_fields == {
        "shipper",
        "consignee",
        "notify_party",
        "port_of_loading",
        "port_of_discharge",
        "gross_weight_kg",
    }

    # 3. Verified values and normalization on preserved fields remain intact (no work discarded)
    assert bl_ext.fields["shipper"].normalized is not None
    assert bl_ext.fields["shipper"].normalized.value == "ACME EXPORTS LTD 123 INDUSTRIAL WAY SINGAPORE 068896"
    assert bl_ext.fields["gross_weight_kg"].normalized is not None
    assert bl_ext.fields["gross_weight_kg"].normalized.value == Decimal("25432.50")
    assert bl_ext.fields["port_of_loading"].normalized is not None
    assert bl_ext.fields["port_of_loading"].normalized.value == "SHANGHAI (CNSHA)"

    # 4. T10 strictly returns DocumentExtraction and does not emit comparator types or mismatch booleans
    assert isinstance(si_ext, DocumentExtraction)
    assert isinstance(bl_ext, DocumentExtraction)
    assert not hasattr(si_ext, "mismatch_detected")
    assert not hasattr(bl_ext, "mismatch_detected")
    assert not hasattr(si_ext, "comparisons")
    assert not hasattr(bl_ext, "comparisons")
