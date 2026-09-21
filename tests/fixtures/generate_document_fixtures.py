"""Deterministic Generator for Synthetic Multi-Format Document Fixtures (Task T01-02).

This generator relies strictly on:
- Python standard library (io, json, os, pathlib, struct)
- Declared project dependencies: python-docx, openpyxl

Zero undeclared or global packages (such as Pillow/PIL) are used.
"""

import io
import json
import os
from pathlib import Path
import docx
import openpyxl

BASE_DIR = Path(__file__).resolve().parent / "documents"

TXT_DIR = BASE_DIR / "txt"
DOCX_DIR = BASE_DIR / "docx"
PDF_DIR = BASE_DIR / "pdf"
SCANNED_DIR = BASE_DIR / "scanned"
XLSX_DIR = BASE_DIR / "xlsx"
MALFORMED_DIR = BASE_DIR / "malformed"

for d in [TXT_DIR, DOCX_DIR, PDF_DIR, SCANNED_DIR, XLSX_DIR, MALFORMED_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# Helper 1: Standard-Library Vector PDF Generator (Extractable Text Layer)
# ==============================================================================
def create_vector_pdf(lines: list[str]) -> bytes:
    """Generate a clean vector PDF with an extractable text layer using only stdlib."""
    content_stream = "BT\n/F1 11 Tf\n14 TL\n50 740 Td\n"
    for line in lines:
        safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_stream += f"({safe_line}) '\n"
    content_stream += "ET\n"
    stream_bytes = content_stream.encode("latin1")
    stream_len = len(stream_bytes)

    objects = []
    # 1: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # 2: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # 3: Page
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    # 4: Contents
    objects.append(
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("latin1")
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )
    # 5: Font
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin1")
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode("latin1")
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin1")
    return pdf


# ==============================================================================
# Helper 2: Standard-Library Raster Image PDF Generator (Genuine Visible Glyphs)
# ==============================================================================
SCAN_SI_LINES = [
    "SHIPPING INSTRUCTION (SCANNED DOCUMENT)",
    "========================================",
    "BOOKING NO:    BK-SCAN-1001",
    "SHIPPER:       MARITIME EXPORT CARGO CORP",
    "CONSIGNEE:     NORDIC GLOBAL TRADING BV",
    "NOTIFY PARTY:  NORDIC GLOBAL TRADING BV",
    "PORT OF LOADING:   SINGAPORE",
    "PORT OF DISCHARGE: ROTTERDAM",
    "CONTAINER COUNT:   2",
    "GROSS WEIGHT:      16500 KG",
    "========================================",
    "CARGO: INDUSTRIAL PUMPS AND SPARE PARTS",
    "VESSEL / VOYAGE: NORTHERN STAR / V.042W",
    "STATUS: DRAFT COPY FOR OCR PROCESSING",
]

FONT_5X7 = {
    'A': [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    'B': ["#### ", "#   #", "#### ", "#   #", "#   #", "#   #", "#### "],
    'C': [" ####", "#    ", "#    ", "#    ", "#    ", "#    ", " ####"],
    'D': ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
    'E': ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    'F': ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    'G': [" ####", "#    ", "#    ", "# ###", "#   #", "#   #", " ####"],
    'H': ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    'I': ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"],
    'J': ["  ###", "    #", "    #", "    #", "    #", "#   #", " ### "],
    'K': ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    'L': ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    'M': ["#   #", "## ##", "# # #", "#   #", "#   #", "#   #", "#   #"],
    'N': ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    'O': [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    'P': ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    'Q': [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
    'R': ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
    'S': [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    'T': ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    'U': ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    'V': ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
    'W': ["#   #", "#   #", "#   #", "#   #", "# # #", "## ##", "#   #"],
    'X': ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    'Y': ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "],
    'Z': ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
    '0': [" ### ", "#  ##", "# # #", "# # #", "##  #", "#   #", " ### "],
    '1': ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"],
    '2': [" ### ", "#   #", "    #", "  ## ", " #   ", "#    ", "#####"],
    '3': ["#### ", "    #", "    #", " ### ", "    #", "    #", "#### "],
    '4': ["#   #", "#   #", "#   #", "#####", "    #", "    #", "    #"],
    '5': ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    '6': ["  ## ", " #   ", "#    ", "#### ", "#   #", "#   #", " ### "],
    '7': ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    '8': [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
    '9': [" ### ", "#   #", "#   #", " ####", "    #", "   # ", " ##  "],
    ' ': ["     ", "     ", "     ", "     ", "     ", "     ", "     "],
    ':': ["     ", "  #  ", "     ", "     ", "  #  ", "     ", "     "],
    '-': ["     ", "     ", "     ", "#####", "     ", "     ", "     "],
    '=': ["     ", "#####", "     ", "#####", "     ", "     ", "     "],
    '.': ["     ", "     ", "     ", "     ", "     ", "  #  ", "  #  "],
    ',': ["     ", "     ", "     ", "     ", "  #  ", "  #  ", " #   "],
    '/': ["    #", "   # ", "   # ", "  #  ", " #   ", " #   ", "#    "],
    '&': [" ##  ", "#  # ", " #   ", "###  ", "#  # ", "#  # ", " ## #"],
    '(': ["   # ", "  #  ", " #   ", " #   ", " #   ", "  #  ", "   # "],
    ')': [" #   ", "  #  ", "   # ", "   # ", "   # ", "  #  ", " #   "],
    '+': ["     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "],
    '_': ["     ", "     ", "     ", "     ", "     ", "     ", "#####"],
}


def render_bitmap_text(lines: list[str], width: int = 600, height: int = 800, scale: int = 2, degraded: bool = False) -> bytes:
    """Render plain text lines into a 2D grayscale bitmap using pure stdlib bitmap font."""
    bg_val = 248 if degraded else 255
    text_val = 65 if degraded else 20

    canvas = [[bg_val for _ in range(width)] for _ in range(height)]

    char_w = 5 * scale
    char_h = 7 * scale
    char_spacing = scale
    line_spacing = 4 * scale

    start_y = 50
    start_x = 40

    for row_idx, line in enumerate(lines):
        line_str = line.upper()
        y_pos = start_y + row_idx * (char_h + line_spacing)
        if y_pos + char_h >= height:
            break

        for col_idx, ch in enumerate(line_str):
            x_pos = start_x + col_idx * (char_w + char_spacing)
            if x_pos + char_w >= width:
                break

            glyph = FONT_5X7.get(ch, FONT_5X7[' '])
            for gy in range(7):
                row_pat = glyph[gy]
                for gx in range(5):
                    if row_pat[gx] == '#':
                        for sy in range(scale):
                            for sx in range(scale):
                                py = y_pos + gy * scale + sy
                                px = x_pos + gx * scale + sx
                                if 0 <= py < height and 0 <= px < width:
                                    canvas[py][px] = text_val

    if degraded:
        for y in range(height):
            for x in range(width):
                # Subtle vertical scanner roller streak
                if 120 <= x <= 122:
                    canvas[y][x] = min(canvas[y][x], 210)
                # Deterministic salt-and-pepper scan dust speckle
                noise_hash = (x * 37 + y * 73 + (x ^ y)) % 1000
                if noise_hash < 8:
                    canvas[y][x] = 160
                elif noise_hash > 995 and canvas[y][x] == text_val:
                    canvas[y][x] = 190
                # Faint photocopier margin edge shadow
                if x < 15 or x > width - 15 or y < 15 or y > height - 15:
                    if (x + y) % 3 == 0:
                        canvas[y][x] = min(canvas[y][x], 220)

    raw = bytearray()
    for row in canvas:
        raw.extend(row)
    return bytes(raw)


def create_raster_image_pdf(lines: list[str], degraded: bool = False) -> bytes:
    """Generate a raster image-only PDF containing genuine visible text glyphs with zero extractable text."""
    width, height = 600, 800
    stream_bytes = render_bitmap_text(lines, width=width, height=height, scale=2, degraded=degraded)
    stream_len = len(stream_bytes)

    objects = []
    # 1: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # 2: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # 3: Page with Image XObject in Resources
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /XObject << /Im1 5 0 R >> >> >>\nendobj\n"
    )
    # 4: Page Content: paint image on canvas without text commands (zero BT...ET)
    content_stream = b"q\n540 0 0 720 36 36 cm\n/Im1 Do\nQ\n"
    objects.append(
        f"4 0 obj\n<< /Length {len(content_stream)} >>\nstream\n".encode("latin1")
        + content_stream
        + b"endstream\nendobj\n"
    )
    # 5: Image XObject (DeviceGray 8-bit)
    img_header = (
        f"5 0 obj\n<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
        f"/ColorSpace /DeviceGray /BitsPerComponent 8 /Length {stream_len} >>\nstream\n"
    ).encode("latin1")
    objects.append(img_header + stream_bytes + b"\nendstream\nendobj\n")

    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin1")
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode("latin1")
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin1")
    return pdf


def main():
    fixtures_meta = {}
    pairs_meta = {}

    # ==========================================================================
    # 1. CORE TXT FIXTURES
    # ==========================================================================
    txt_si_001 = (
        "SHIPPING INSTRUCTION\n"
        "--------------------\n"
        "BOOKING NUMBER: BK-SYN-9901\n"
        "SHIPPER: PACIFIC SYNTHETIC LOGISTICS PTE LTD\n"
        "CONSIGNEE: ATLANTIC IMPORTS & TRADING GMBH\n"
        "NOTIFY PARTY: MARITIME CUSTOMS BROKERS INC\n"
        "PORT OF LOADING: SINGAPORE\n"
        "PORT OF DISCHARGE: ROTTERDAM\n"
        "CONTAINER COUNT: 4\n"
        "GROSS WEIGHT: 22000 KG\n"
        "CARGO DESCRIPTION: INDUSTRIAL VALVES AND FITTINGS\n"
    )
    (TXT_DIR / "txt_si_001_clean.txt").write_text(txt_si_001, encoding="utf-8")
    fixtures_meta["txt_si_001_clean"] = {
        "file": "txt/txt_si_001_clean.txt",
        "format": "txt",
        "role": "SI",
        "scenario": "clean_baseline",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": "PAIR-001",
        "tags": ["PAR-TXT-001", "clean_match_si"],
    }

    txt_bl_001 = (
        "DRAFT BILL OF LADING\n"
        "--------------------\n"
        "B/L NUMBER: BL-SYN-9901-DRAFT\n"
        "SHIPPER: PACIFIC SYNTHETIC LOGISTICS PTE LTD\n"
        "CONSIGNEE: ATLANTIC IMPORTS & TRADING GMBH\n"
        "NOTIFY PARTY: MARITIME CUSTOMS BROKERS INC\n"
        "PORT OF LOADING: SINGAPORE\n"
        "PORT OF DISCHARGE: ROTTERDAM\n"
        "CONTAINER COUNT: 4\n"
        "GROSS WEIGHT: 22000 KG\n"
        "REMARKS: SHIPPED ON BOARD IN APPARENT GOOD ORDER\n"
    )
    (TXT_DIR / "txt_bl_001_clean_match.txt").write_text(txt_bl_001, encoding="utf-8")
    fixtures_meta["txt_bl_001_clean_match"] = {
        "file": "txt/txt_bl_001_clean_match.txt",
        "format": "txt",
        "role": "BL",
        "scenario": "clean_baseline_match",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": "PAIR-001",
        "tags": ["PAR-TXT-001", "clean_match_bl"],
    }

    pairs_meta["PAIR-001"] = {
        "si_fixture": "txt_si_001_clean",
        "bl_fixture": "txt_bl_001_clean_match",
        "scenario": "exact_match",
        "expected_mismatches": [],
        "mismatch_detected": False,
        "rationale": "Clean exact match across all seven mandatory fields.",
    }

    # PAIR-002: Single Mismatch (container_count: SI=4, BL=5)
    txt_bl_002 = txt_bl_001.replace("CONTAINER COUNT: 4", "CONTAINER COUNT: 5")
    (TXT_DIR / "txt_bl_002_count_mismatch.txt").write_text(txt_bl_002, encoding="utf-8")
    fixtures_meta["txt_bl_002_count_mismatch"] = {
        "file": "txt/txt_bl_002_count_mismatch.txt",
        "format": "txt",
        "role": "BL",
        "scenario": "single_mismatch",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 5,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": "PAIR-002",
        "tags": ["PAR-TXT-001", "single_mismatch"],
    }
    pairs_meta["PAIR-002"] = {
        "si_fixture": "txt_si_001_clean",
        "bl_fixture": "txt_bl_002_count_mismatch",
        "scenario": "single_mismatch",
        "expected_mismatches": ["container_count"],
        "mismatch_detected": True,
        "rationale": "SI specifies 4 containers, draft BL specifies 5 containers.",
    }

    # PAIR-003: Multiple Mismatches (shipper, port_of_discharge, gross_weight_kg)
    txt_bl_003 = (
        "DRAFT BILL OF LADING\n"
        "--------------------\n"
        "B/L NUMBER: BL-SYN-9903-DRAFT\n"
        "SHIPPER: DIFFERENT SHIPPER TRADING CO\n"
        "CONSIGNEE: ATLANTIC IMPORTS & TRADING GMBH\n"
        "NOTIFY PARTY: MARITIME CUSTOMS BROKERS INC\n"
        "PORT OF LOADING: SINGAPORE\n"
        "PORT OF DISCHARGE: HAMBURG\n"
        "CONTAINER COUNT: 4\n"
        "GROSS WEIGHT: 25500 KG\n"
    )
    (TXT_DIR / "txt_bl_003_multi_mismatch.txt").write_text(txt_bl_003, encoding="utf-8")
    fixtures_meta["txt_bl_003_multi_mismatch"] = {
        "file": "txt/txt_bl_003_multi_mismatch.txt",
        "format": "txt",
        "role": "BL",
        "scenario": "multiple_mismatches",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "DIFFERENT SHIPPER TRADING CO",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "HAMBURG",
            "container_count": 4,
            "gross_weight_kg": "25500",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": "PAIR-003",
        "tags": ["PAR-TXT-001", "multi_mismatch"],
    }
    pairs_meta["PAIR-003"] = {
        "si_fixture": "txt_si_001_clean",
        "bl_fixture": "txt_bl_003_multi_mismatch",
        "scenario": "multiple_mismatches",
        "expected_mismatches": ["shipper", "port_of_discharge", "gross_weight_kg"],
        "mismatch_detected": True,
        "rationale": "Multiple fields differ between SI and BL.",
    }

    # TXT Authoritative Source-Supported Alternative Labels ("Load Port" vs "Port of Loading")
    txt_si_005 = (
        "SHIPPING INSTRUCTION\n"
        "--------------------\n"
        "Shipper: PACIFIC SYNTHETIC LOGISTICS PTE LTD\n"
        "Consignee: ATLANTIC IMPORTS & TRADING GMBH\n"
        "Notify Party: MARITIME CUSTOMS BROKERS INC\n"
        "Load Port: SINGAPORE\n"
        "Port of Discharge: ROTTERDAM\n"
        "Container Count: 4\n"
        "Gross Weight: 22000 KG\n"
    )
    (TXT_DIR / "txt_si_005_alt_labels.txt").write_text(txt_si_005, encoding="utf-8")
    fixtures_meta["txt_si_005_alt_labels"] = {
        "file": "txt/txt_si_005_alt_labels.txt",
        "format": "txt",
        "role": "SI",
        "scenario": "authoritative_label_variant_load_port",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-TXT-001", "authoritative_label_variant", "load_port"],
        "rationale": "Uses the label variant 'Load Port' for port_of_loading supported by the original use case and baselined specification.",
    }

    # TXT Exploratory Non-Baseline Aliases (POL, POD, Total Containers)
    txt_si_012 = (
        "CARGO MEMORANDUM (EXPLORATORY ALIASES)\n"
        "-------------------------------------\n"
        "Shipper: PACIFIC SYNTHETIC LOGISTICS PTE LTD\n"
        "Consignee: ATLANTIC IMPORTS & TRADING GMBH\n"
        "Notify Party: MARITIME CUSTOMS BROKERS INC\n"
        "POL: SINGAPORE\n"
        "POD: ROTTERDAM\n"
        "Total Containers: 4\n"
        "Total Gross Weight: 22000 KG\n"
    )
    (TXT_DIR / "txt_si_012_exploratory_aliases.txt").write_text(txt_si_012, encoding="utf-8")
    fixtures_meta["txt_si_012_exploratory_aliases"] = {
        "file": "txt/txt_si_012_exploratory_aliases.txt",
        "format": "txt",
        "role": "SI",
        "scenario": "PROPOSED / EXPLORATORY — NOT A BASELINE ACCEPTANCE EXPECTATION",
        "is_baseline_acceptance": False,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["exploratory", "non_baseline_aliases"],
        "rationale": "Exploratory fixture testing shorthand acronyms (POL, POD). Marked explicitly as PROPOSED / EXPLORATORY — NOT A BASELINE ACCEPTANCE EXPECTATION.",
    }

    # TXT Multiline Organization Blocks (with explicit notify party)
    txt_si_006 = (
        "SHIPPING INSTRUCTION\n"
        "SHIPPER:\n"
        "PACIFIC SYNTHETIC LOGISTICS PTE LTD\n"
        "SUITE 400, 128 HARBOR WAY\n"
        "SINGAPORE 049318\n\n"
        "CONSIGNEE:\n"
        "ATLANTIC IMPORTS & TRADING GMBH\n"
        "INDUSTRIESTRASSE 12\n"
        "20457 HAMBURG, GERMANY\n\n"
        "NOTIFY PARTY:\n"
        "MARITIME NOTIFY SERVICES LTD\n"
        "100 SHIPPING PLAZA, SINGAPORE 049319\n\n"
        "PORT OF LOADING: SINGAPORE\n"
        "PORT OF DISCHARGE: ROTTERDAM\n"
        "CONTAINER COUNT: 4\n"
        "GROSS WEIGHT: 22000 KG\n"
    )
    (TXT_DIR / "txt_si_006_multiline_orgs.txt").write_text(txt_si_006, encoding="utf-8")
    fixtures_meta["txt_si_006_multiline_orgs"] = {
        "file": "txt/txt_si_006_multiline_orgs.txt",
        "format": "txt",
        "role": "SI",
        "scenario": "multiline_organizations",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD\nSUITE 400, 128 HARBOR WAY\nSINGAPORE 049318",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH\nINDUSTRIESTRASSE 12\n20457 HAMBURG, GERMANY",
            "notify_party": "MARITIME NOTIFY SERVICES LTD\n100 SHIPPING PLAZA, SINGAPORE 049319",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-TXT-001", "multiline_address"],
    }

    # TXT Exploratory Literal "SAME AS CONSIGNEE" (No automatic dereferencing)
    txt_si_013 = (
        "SHIPPING INSTRUCTION\n"
        "SHIPPER: PACIFIC SYNTHETIC LOGISTICS PTE LTD\n"
        "CONSIGNEE: ATLANTIC IMPORTS & TRADING GMBH\n"
        "NOTIFY PARTY: SAME AS CONSIGNEE\n"
        "PORT OF LOADING: SINGAPORE\n"
        "PORT OF DISCHARGE: ROTTERDAM\n"
        "CONTAINER COUNT: 4\n"
        "GROSS WEIGHT: 22000 KG\n"
    )
    (TXT_DIR / "txt_si_013_exploratory_same_as_consignee.txt").write_text(txt_si_013, encoding="utf-8")
    fixtures_meta["txt_si_013_exploratory_same_as_consignee"] = {
        "file": "txt/txt_si_013_exploratory_same_as_consignee.txt",
        "format": "txt",
        "role": "SI",
        "scenario": "PROPOSED / EXPLORATORY — NOT A BASELINE ACCEPTANCE EXPECTATION",
        "is_baseline_acceptance": False,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "SAME AS CONSIGNEE",  # Literal raw text, NOT automatically dereferenced
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["exploratory", "raw_literal_same_as_consignee"],
        "rationale": "Exploratory fixture testing literal 'SAME AS CONSIGNEE'. Does not assert automatic dereferencing. Marked as PROPOSED / EXPLORATORY — NOT A BASELINE ACCEPTANCE EXPECTATION.",
    }

    # PAIR-004: Missing Field (notify_party missing)
    txt_si_007 = (
        "SHIPPING INSTRUCTION\n"
        "SHIPPER: PACIFIC SYNTHETIC LOGISTICS PTE LTD\n"
        "CONSIGNEE: ATLANTIC IMPORTS & TRADING GMBH\n"
        "PORT OF LOADING: SINGAPORE\n"
        "PORT OF DISCHARGE: ROTTERDAM\n"
        "CONTAINER COUNT: 4\n"
        "GROSS WEIGHT: 22000 KG\n"
    )
    (TXT_DIR / "txt_si_007_missing_field.txt").write_text(txt_si_007, encoding="utf-8")
    fixtures_meta["txt_si_007_missing_field"] = {
        "file": "txt/txt_si_007_missing_field.txt",
        "format": "txt",
        "role": "SI",
        "scenario": "missing_required_field",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": None,
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": ["notify_party"],
        "conflicting_fields": [],
        "pair_id": "PAIR-004",
        "tags": ["HITL-RSN-004", "missing_required_value"],
    }
    pairs_meta["PAIR-004"] = {
        "si_fixture": "txt_si_007_missing_field",
        "bl_fixture": "txt_bl_001_clean_match",
        "scenario": "unresolved_missing_field",
        "expected_mismatches": None,
        "mismatch_detected": None,
        "expected_hitl_reason": "missing_required_value",
        "rationale": "SI is missing notify_party. Reliability gate routes to NEEDS_REVIEW.",
    }

    # PAIR-005: Conflicting candidate values in SI
    txt_si_008 = (
        "SHIPPING INSTRUCTION\n"
        "SHIPPER: PACIFIC SYNTHETIC LOGISTICS PTE LTD\n"
        "CONSIGNEE: ATLANTIC IMPORTS & TRADING GMBH\n"
        "NOTIFY PARTY: MARITIME CUSTOMS BROKERS INC\n"
        "PORT OF LOADING: SINGAPORE\n"
        "PORT OF DISCHARGE: ROTTERDAM\n"
        "CONTAINER COUNT: 4\n"
        "ESTIMATED GROSS WEIGHT: 24500 KG\n"
        "FINAL CERTIFIED GROSS WEIGHT: 28000 KG\n"
    )
    (TXT_DIR / "txt_si_008_conflicting_candidates.txt").write_text(txt_si_008, encoding="utf-8")
    fixtures_meta["txt_si_008_conflicting_candidates"] = {
        "file": "txt/txt_si_008_conflicting_candidates.txt",
        "format": "txt",
        "role": "SI",
        "scenario": "conflicting_candidate_values",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": None,
        },
        "missing_fields": [],
        "conflicting_fields": ["gross_weight_kg"],
        "pair_id": "PAIR-005",
        "tags": ["HITL-RSN-006", "conflicting_candidate_values"],
    }
    pairs_meta["PAIR-005"] = {
        "si_fixture": "txt_si_008_conflicting_candidates",
        "bl_fixture": "txt_bl_001_clean_match",
        "scenario": "conflicting_candidates",
        "expected_mismatches": None,
        "mismatch_detected": None,
        "expected_hitl_reason": "conflicting_candidate_values",
        "rationale": "SI provides conflicting gross weight candidates (24,500 vs 28,000 KG). Escalates to review.",
    }

    # Short valid TXT (with explicit notify party)
    txt_si_009 = (
        "SI 901: Shpr: SYNTHETIC CHEM | Cnee: ALPHA IMPORTS | "
        "Notif: MARITIME NOTIFY CORP | POL: SINGAPORE | POD: ROTTERDAM | Cont: 2 | Wt: 44000 KG\n"
    )
    (TXT_DIR / "txt_si_009_short_valid.txt").write_text(txt_si_009, encoding="utf-8")
    fixtures_meta["txt_si_009_short_valid"] = {
        "file": "txt/txt_si_009_short_valid.txt",
        "format": "txt",
        "role": "SI",
        "scenario": "short_valid_content",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "SYNTHETIC CHEM",
            "consignee": "ALPHA IMPORTS",
            "notify_party": "MARITIME NOTIFY CORP",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 2,
            "gross_weight_kg": "44000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-USAB-001", "qualitative_usability"],
    }

    # Long unusable / garbled TXT
    txt_si_010 = (
        "NOTICE OF CARRIAGE AND TERMS OF CONSIGNMENT\n"
        + "All operations subject to standard standard standard rules...\n" * 150
        + "XYZ ??? ### %%% &&& [INVALID UNUSABLE CARRIAGE FRAGMENT]\n"
    )
    (TXT_DIR / "txt_si_010_long_unusable.txt").write_text(txt_si_010, encoding="utf-8")
    fixtures_meta["txt_si_010_long_unusable"] = {
        "file": "txt/txt_si_010_long_unusable.txt",
        "format": "txt",
        "role": "SI",
        "scenario": "long_unusable_content",
        "is_baseline_acceptance": True,
        "expected_fields": {},
        "missing_fields": [
            "shipper",
            "consignee",
            "notify_party",
            "port_of_loading",
            "port_of_discharge",
            "container_count",
            "gross_weight_kg",
        ],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-USAB-002", "unusable_document"],
    }

    # PAIR-006: Exact Unit Conversion (SI: 22 MT vs BL: 22000 KG)
    txt_si_011 = txt_si_001.replace("GROSS WEIGHT: 22000 KG", "GROSS WEIGHT: 22 MT")
    (TXT_DIR / "txt_si_011_unit_mt.txt").write_text(txt_si_011, encoding="utf-8")
    fixtures_meta["txt_si_011_unit_mt"] = {
        "file": "txt/txt_si_011_unit_mt.txt",
        "format": "txt",
        "role": "SI",
        "scenario": "unit_conversion_mt",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": "PAIR-006",
        "tags": ["UT-NORM-004", "unit_conversion"],
    }
    pairs_meta["PAIR-006"] = {
        "si_fixture": "txt_si_011_unit_mt",
        "bl_fixture": "txt_bl_001_clean_match",
        "scenario": "exact_unit_conversion",
        "expected_mismatches": [],
        "mismatch_detected": False,
        "rationale": "Exact unit conversion: SI specifies 22 MT (22 * 1000 = 22,000 KG) and BL specifies 22,000 KG. Normalized equality matches with zero mismatch.",
    }

    # ==========================================================================
    # 2. DOCX FIXTURES (python-docx)
    # ==========================================================================
    # Paragraph-based SI
    doc_si_1 = docx.Document()
    doc_si_1.add_heading("SHIPPING INSTRUCTION", level=1)
    doc_si_1.add_paragraph("Shipper: PACIFIC SYNTHETIC LOGISTICS PTE LTD")
    doc_si_1.add_paragraph("Consignee: ATLANTIC IMPORTS & TRADING GMBH")
    doc_si_1.add_paragraph("Notify Party: MARITIME CUSTOMS BROKERS INC")
    doc_si_1.add_paragraph("Port of Loading: SINGAPORE")
    doc_si_1.add_paragraph("Port of Discharge: ROTTERDAM")
    doc_si_1.add_paragraph("Total Containers: 4")
    doc_si_1.add_paragraph("Gross Weight: 22000 KG")
    doc_si_1.save(DOCX_DIR / "docx_si_001_paragraph.docx")
    fixtures_meta["docx_si_001_paragraph"] = {
        "file": "docx/docx_si_001_paragraph.docx",
        "format": "docx",
        "role": "SI",
        "scenario": "clean_paragraph_docx",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": "PAIR-DOCX-001",
        "tags": ["PAR-DOCX-001", "docx_paragraph"],
    }

    # Table-based BL
    doc_bl_1 = docx.Document()
    doc_bl_1.add_heading("DRAFT BILL OF LADING", level=1)
    table_bl = doc_bl_1.add_table(rows=7, cols=2)
    rows_data = [
        ("Shipper", "PACIFIC SYNTHETIC LOGISTICS PTE LTD"),
        ("Consignee", "ATLANTIC IMPORTS & TRADING GMBH"),
        ("Notify Party", "MARITIME CUSTOMS BROKERS INC"),
        ("Port of Loading", "SINGAPORE"),
        ("Port of Discharge", "ROTTERDAM"),
        ("Container Count", "4"),
        ("Gross Weight", "22000 KG"),
    ]
    for idx, (field_lbl, val) in enumerate(rows_data):
        table_bl.cell(idx, 0).text = field_lbl
        table_bl.cell(idx, 1).text = val
    doc_bl_1.save(DOCX_DIR / "docx_bl_001_table.docx")
    fixtures_meta["docx_bl_001_table"] = {
        "file": "docx/docx_bl_001_table.docx",
        "format": "docx",
        "role": "BL",
        "scenario": "clean_table_docx",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": "PAIR-DOCX-001",
        "tags": ["PAR-DOCX-001", "docx_table"],
    }
    pairs_meta["PAIR-DOCX-001"] = {
        "si_fixture": "docx_si_001_paragraph",
        "bl_fixture": "docx_bl_001_table",
        "scenario": "clean_docx_pair_match",
        "expected_mismatches": [],
        "mismatch_detected": False,
        "rationale": "Cross-format DOCX pair (paragraph SI vs table BL) with exact 7-field match.",
    }

    # DOCX Multiline Cell (with explicit notify party)
    doc_multi = docx.Document()
    doc_multi.add_heading("SHIPPING INSTRUCTION", level=1)
    t_multi = doc_multi.add_table(rows=7, cols=2)
    m_data = [
        ("Shipper", "PACIFIC SYNTHETIC LOGISTICS\n128 HARBOR WAY\nSINGAPORE"),
        ("Consignee", "ATLANTIC IMPORTS GMBH\nINDUSTRIESTR 12\nHAMBURG"),
        ("Notify Party", "MARITIME NOTIFY SERVICES\n100 SHIPPING PLAZA\nSINGAPORE"),
        ("Port of Loading", "SINGAPORE"),
        ("Port of Discharge", "ROTTERDAM"),
        ("Container Count", "4"),
        ("Gross Weight", "22000 KG"),
    ]
    for idx, (lbl, val) in enumerate(m_data):
        t_multi.cell(idx, 0).text = lbl
        t_multi.cell(idx, 1).text = val
    doc_multi.save(DOCX_DIR / "docx_si_003_multiline_cell.docx")
    fixtures_meta["docx_si_003_multiline_cell"] = {
        "file": "docx/docx_si_003_multiline_cell.docx",
        "format": "docx",
        "role": "SI",
        "scenario": "multiline_cell_table",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS\n128 HARBOR WAY\nSINGAPORE",
            "consignee": "ATLANTIC IMPORTS GMBH\nINDUSTRIESTR 12\nHAMBURG",
            "notify_party": "MARITIME NOTIFY SERVICES\n100 SHIPPING PLAZA\nSINGAPORE",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-DOCX-001", "docx_multiline"],
    }

    # DOCX Missing Field (missing port_of_discharge)
    doc_missing = docx.Document()
    doc_missing.add_heading("SHIPPING INSTRUCTION", level=1)
    t_missing = doc_missing.add_table(rows=6, cols=2)
    miss_data = [
        ("Shipper", "PACIFIC SYNTHETIC LOGISTICS PTE LTD"),
        ("Consignee", "ATLANTIC IMPORTS & TRADING GMBH"),
        ("Notify Party", "MARITIME CUSTOMS BROKERS INC"),
        ("Port of Loading", "SINGAPORE"),
        ("Container Count", "4"),
        ("Gross Weight", "22000 KG"),
    ]
    for idx, (lbl, val) in enumerate(miss_data):
        t_missing.cell(idx, 0).text = lbl
        t_missing.cell(idx, 1).text = val
    doc_missing.save(DOCX_DIR / "docx_si_004_missing_field.docx")
    fixtures_meta["docx_si_004_missing_field"] = {
        "file": "docx/docx_si_004_missing_field.docx",
        "format": "docx",
        "role": "SI",
        "scenario": "missing_required_field",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": None,
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": ["port_of_discharge"],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-DOCX-001", "missing_value"],
    }

    # DOCX Conflicting Values
    doc_conflict = docx.Document()
    doc_conflict.add_heading("SHIPPING INSTRUCTION", level=1)
    doc_conflict.add_paragraph("Summary: Booking for 4 full containers (FCL).")
    t_conflict = doc_conflict.add_table(rows=7, cols=2)
    conf_data = [
        ("Shipper", "PACIFIC SYNTHETIC LOGISTICS PTE LTD"),
        ("Consignee", "ATLANTIC IMPORTS & TRADING GMBH"),
        ("Notify Party", "MARITIME CUSTOMS BROKERS INC"),
        ("Port of Loading", "SINGAPORE"),
        ("Port of Discharge", "ROTTERDAM"),
        ("Container Count", "6"),
        ("Gross Weight", "22000 KG"),
    ]
    for idx, (lbl, val) in enumerate(conf_data):
        t_conflict.cell(idx, 0).text = lbl
        t_conflict.cell(idx, 1).text = val
    doc_conflict.save(DOCX_DIR / "docx_si_005_conflicting_values.docx")
    fixtures_meta["docx_si_005_conflicting_values"] = {
        "file": "docx/docx_si_005_conflicting_values.docx",
        "format": "docx",
        "role": "SI",
        "scenario": "conflicting_candidate_values",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": None,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": ["container_count"],
        "pair_id": None,
        "tags": ["PAR-DOCX-001", "conflicting_candidate_values"],
    }

    # ==========================================================================
    # 3. VECTOR / TEXT PDF FIXTURES (Pure Standard Library)
    # ==========================================================================
    pdf_si_lines = [
        "SHIPPING INSTRUCTION DOCUMENT",
        "=============================",
        "SHIPPER: PACIFIC SYNTHETIC LOGISTICS PTE LTD",
        "CONSIGNEE: ATLANTIC IMPORTS & TRADING GMBH",
        "NOTIFY PARTY: MARITIME CUSTOMS BROKERS INC",
        "PORT OF LOADING: SINGAPORE",
        "PORT OF DISCHARGE: ROTTERDAM",
        "CONTAINER COUNT: 4",
        "GROSS WEIGHT: 22000 KG",
        "GOODS: SYNTHETIC RUBBER GRANULES",
    ]
    (PDF_DIR / "pdf_si_001_clean.pdf").write_bytes(create_vector_pdf(pdf_si_lines))
    fixtures_meta["pdf_si_001_clean"] = {
        "file": "pdf/pdf_si_001_clean.pdf",
        "format": "pdf",
        "role": "SI",
        "scenario": "vector_pdf_clean",
        "is_baseline_acceptance": True,
        "has_extractable_text": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": "PAIR-PDF-001",
        "tags": ["PAR-PDF-001", "vector_clean_si"],
    }

    pdf_bl_lines = [
        "DRAFT BILL OF LADING",
        "====================",
        "B/L NO: OOCL-SYN-882190",
        "SHIPPER: PACIFIC SYNTHETIC LOGISTICS PTE LTD",
        "CONSIGNEE: ATLANTIC IMPORTS & TRADING GMBH",
        "NOTIFY PARTY: MARITIME CUSTOMS BROKERS INC",
        "PORT OF LOADING: SINGAPORE",
        "PORT OF DISCHARGE: ROTTERDAM",
        "CONTAINER COUNT: 4",
        "GROSS WEIGHT: 22000 KG",
    ]
    (PDF_DIR / "pdf_bl_001_clean_match.pdf").write_bytes(create_vector_pdf(pdf_bl_lines))
    fixtures_meta["pdf_bl_001_clean_match"] = {
        "file": "pdf/pdf_bl_001_clean_match.pdf",
        "format": "pdf",
        "role": "BL",
        "scenario": "vector_pdf_clean_match",
        "is_baseline_acceptance": True,
        "has_extractable_text": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": "PAIR-PDF-001",
        "tags": ["PAR-PDF-001", "vector_clean_bl"],
    }
    pairs_meta["PAIR-PDF-001"] = {
        "si_fixture": "pdf_si_001_clean",
        "bl_fixture": "pdf_bl_001_clean_match",
        "scenario": "clean_vector_pdf_match",
        "expected_mismatches": [],
        "mismatch_detected": False,
        "rationale": "Vector PDF pair with extractable text layers matching 100%.",
    }

    # PDF Missing Consignee
    pdf_missing_lines = [
        "SHIPPING INSTRUCTION",
        "SHIPPER: PACIFIC SYNTHETIC LOGISTICS PTE LTD",
        "NOTIFY PARTY: MARITIME CUSTOMS BROKERS INC",
        "PORT OF LOADING: SINGAPORE",
        "PORT OF DISCHARGE: ROTTERDAM",
        "CONTAINER COUNT: 4",
        "GROSS WEIGHT: 22000 KG",
    ]
    (PDF_DIR / "pdf_si_003_missing_field.pdf").write_bytes(create_vector_pdf(pdf_missing_lines))
    fixtures_meta["pdf_si_003_missing_field"] = {
        "file": "pdf/pdf_si_003_missing_field.pdf",
        "format": "pdf",
        "role": "SI",
        "scenario": "missing_required_field",
        "is_baseline_acceptance": True,
        "has_extractable_text": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": None,
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": "22000",
        },
        "missing_fields": ["consignee"],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-PDF-001", "missing_consignee"],
    }

    # PDF Conflicting Gross Weight
    pdf_conflict_lines = [
        "SHIPPING INSTRUCTION",
        "SHIPPER: PACIFIC SYNTHETIC LOGISTICS PTE LTD",
        "CONSIGNEE: ATLANTIC IMPORTS & TRADING GMBH",
        "NOTIFY PARTY: MARITIME CUSTOMS BROKERS INC",
        "PORT OF LOADING: SINGAPORE",
        "PORT OF DISCHARGE: ROTTERDAM",
        "CONTAINER COUNT: 4",
        "NET WEIGHT: 18000 KG",
        "GROSS WEIGHT SPECIFICATION A: 22000 KG",
        "GROSS WEIGHT SPECIFICATION B: 26500 KG",
    ]
    (PDF_DIR / "pdf_si_004_conflicting_values.pdf").write_bytes(create_vector_pdf(pdf_conflict_lines))
    fixtures_meta["pdf_si_004_conflicting_values"] = {
        "file": "pdf/pdf_si_004_conflicting_values.pdf",
        "format": "pdf",
        "role": "SI",
        "scenario": "conflicting_candidate_values",
        "is_baseline_acceptance": True,
        "has_extractable_text": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 4,
            "gross_weight_kg": None,
        },
        "missing_fields": [],
        "conflicting_fields": ["gross_weight_kg"],
        "pair_id": None,
        "tags": ["PAR-PDF-001", "conflicting_weight"],
    }

    # ==========================================================================
    # 4. RASTER IMAGE-ONLY PDF FIXTURES (Pure Standard Library)
    # ==========================================================================
    # Clean raster image-only PDF with genuine visible text glyphs
    pdf_scan_bytes = create_raster_image_pdf(SCAN_SI_LINES, degraded=False)
    (SCANNED_DIR / "scan_si_001_readable.pdf").write_bytes(pdf_scan_bytes)

    fixtures_meta["scan_si_001_readable"] = {
        "file": "scanned/scan_si_001_readable.pdf",
        "format": "pdf_raster",
        "role": "SI",
        "scenario": "raster_image_only_pdf_zero_text_layer",
        "is_baseline_acceptance": True,
        "has_extractable_text": False,
        "has_visible_text_glyphs": True,
        "expected_fields": {
            "shipper": "MARITIME EXPORT CARGO CORP",
            "consignee": "NORDIC GLOBAL TRADING BV",
            "notify_party": "NORDIC GLOBAL TRADING BV",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 2,
            "gross_weight_kg": "16500",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-USAB-003", "OCR_INPUT", "zero_text_layer"],
        "rationale": "Raster image-only PDF containing genuine visible character glyphs for all seven mandatory shipping fields with zero extractable PDF text layer (pypdf extract_text returns empty string). Serves as offline input for OCR/Vision recovery tests.",
    }

    # Degraded raster image-only PDF with controlled scan noise
    pdf_degraded_bytes = create_raster_image_pdf(SCAN_SI_LINES, degraded=True)
    (SCANNED_DIR / "scan_si_002_degraded.pdf").write_bytes(pdf_degraded_bytes)

    fixtures_meta["scan_si_002_degraded"] = {
        "file": "scanned/scan_si_002_degraded.pdf",
        "format": "pdf_raster",
        "role": "SI",
        "scenario": "raster_image_only_pdf_degraded",
        "is_baseline_acceptance": True,
        "has_extractable_text": False,
        "has_visible_text_glyphs": True,
        "expected_fields": {
            "shipper": "MARITIME EXPORT CARGO CORP",
            "consignee": "NORDIC GLOBAL TRADING BV",
            "notify_party": "NORDIC GLOBAL TRADING BV",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 2,
            "gross_weight_kg": "16500",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-USAB-003", "OCR_INPUT_DEGRADED"],
        "rationale": "Degraded raster image-only PDF containing genuine visible character glyphs with controlled scan noise (roller streak, toner dust, paper grain) with zero extractable PDF text layer. Still meaningfully OCR-targetable.",
    }

    # ==========================================================================
    # 5. MALFORMED / CORRUPTED FIXTURES
    # ==========================================================================
    corrupt_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nstream\n[TRUNCATED_STREAM"
    (MALFORMED_DIR / "corrupt_stream.pdf").write_bytes(corrupt_pdf_bytes)
    fixtures_meta["corrupt_stream_pdf"] = {
        "file": "malformed/corrupt_stream.pdf",
        "format": "pdf_malformed",
        "role": "UNKNOWN",
        "scenario": "corrupted_pdf_stream",
        "is_baseline_acceptance": True,
        "is_corrupted": True,
        "expected_fields": {},
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-PDF-002", "stream_corruption", "HITL-RSN-002"],
    }

    corrupt_docx_bytes = b"PK\x03\x04\x14\x00[CORRUPTED_NON_ZIP_DOCX_HEADER_AND_GARBAGE]"
    (MALFORMED_DIR / "corrupt_structure.docx").write_bytes(corrupt_docx_bytes)
    fixtures_meta["corrupt_structure_docx"] = {
        "file": "malformed/corrupt_structure.docx",
        "format": "docx_malformed",
        "role": "UNKNOWN",
        "scenario": "corrupted_docx_structure",
        "is_baseline_acceptance": True,
        "is_corrupted": True,
        "expected_fields": {},
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-DOCX-001", "docx_corruption", "HITL-RSN-002"],
    }

    (MALFORMED_DIR / "empty_zero_bytes.pdf").write_bytes(b"")
    fixtures_meta["empty_zero_bytes_pdf"] = {
        "file": "malformed/empty_zero_bytes.pdf",
        "format": "pdf_empty",
        "role": "UNKNOWN",
        "scenario": "empty_zero_bytes",
        "is_baseline_acceptance": True,
        "is_corrupted": True,
        "expected_fields": {},
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-USAB-004", "empty_file"],
    }

    # ==========================================================================
    # 6. XLSX FIXTURES (openpyxl — Design Extension)
    # ==========================================================================
    wb_si = openpyxl.Workbook()
    ws_header = wb_si.active
    ws_header.title = "Shipment_Header"
    ws_header.append(["Field_Name", "Field_Value"])
    ws_header.append(["Shipper", "PACIFIC SYNTHETIC LOGISTICS PTE LTD"])
    ws_header.append(["Consignee", "ATLANTIC IMPORTS & TRADING GMBH"])
    ws_header.append(["Notify Party", "MARITIME CUSTOMS BROKERS INC"])
    ws_header.append(["Port of Loading", "SINGAPORE"])
    ws_header.append(["Port of Discharge", "ROTTERDAM"])

    ws_cargo = wb_si.create_sheet(title="Cargo_Details")
    ws_cargo.append(["Container_ID", "Type", "Gross_Weight_KG"])
    ws_cargo.append(["MSCU1029384", "40HC", 11000])
    ws_cargo.append(["MSCU1029385", "40HC", 11000])
    ws_cargo.append(["TOTAL_CONTAINERS", "2", "TOTAL_WEIGHT"])
    ws_cargo.append(["SUMMARY", "2", 22000])

    wb_si.save(XLSX_DIR / "xlsx_si_001_clean.xlsx")
    fixtures_meta["xlsx_si_001_clean"] = {
        "file": "xlsx/xlsx_si_001_clean.xlsx",
        "format": "xlsx",
        "role": "SI",
        "scenario": "clean_multi_sheet_xlsx",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 2,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": "PAIR-XLSX-001",
        "tags": ["PAR-XLSX-001", "design_extension"],
    }

    wb_bl = openpyxl.Workbook()
    ws_bl = wb_bl.active
    ws_bl.title = "Draft_BL"
    ws_bl.append(["Property", "Value"])
    ws_bl.append(["Shipper", "PACIFIC SYNTHETIC LOGISTICS PTE LTD"])
    ws_bl.append(["Consignee", "ATLANTIC IMPORTS & TRADING GMBH"])
    ws_bl.append(["Notify Party", "MARITIME CUSTOMS BROKERS INC"])
    ws_bl.append(["Port of Loading", "SINGAPORE"])
    ws_bl.append(["Port of Discharge", "ROTTERDAM"])
    ws_bl.append(["Container Count", 2])
    ws_bl.append(["Gross Weight KG", 22000])
    wb_bl.save(XLSX_DIR / "xlsx_bl_001_clean_match.xlsx")
    fixtures_meta["xlsx_bl_001_clean_match"] = {
        "file": "xlsx/xlsx_bl_001_clean_match.xlsx",
        "format": "xlsx",
        "role": "BL",
        "scenario": "clean_xlsx_match",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": "SINGAPORE",
            "port_of_discharge": "ROTTERDAM",
            "container_count": 2,
            "gross_weight_kg": "22000",
        },
        "missing_fields": [],
        "conflicting_fields": [],
        "pair_id": "PAIR-XLSX-001",
        "tags": ["PAR-XLSX-001", "design_extension_match"],
    }
    pairs_meta["PAIR-XLSX-001"] = {
        "si_fixture": "xlsx_si_001_clean",
        "bl_fixture": "xlsx_bl_001_clean_match",
        "scenario": "clean_xlsx_pair_match",
        "expected_mismatches": [],
        "mismatch_detected": False,
        "rationale": "Excel spreadsheet SI matched against Excel Draft BL with 100% field equality.",
    }

    wb_miss = openpyxl.Workbook()
    ws_m = wb_miss.active
    ws_m.title = "Incomplete_SI"
    ws_m.append(["Field", "Value"])
    ws_m.append(["Shipper", "PACIFIC SYNTHETIC LOGISTICS PTE LTD"])
    ws_m.append(["Consignee", "ATLANTIC IMPORTS & TRADING GMBH"])
    ws_m.append(["Notify Party", "MARITIME CUSTOMS BROKERS INC"])
    ws_m.append(["Port of Discharge", "ROTTERDAM"])
    ws_m.append(["Container Count", 2])
    ws_m.append(["Gross Weight KG", 22000])
    wb_miss.save(XLSX_DIR / "xlsx_si_002_missing_field.xlsx")
    fixtures_meta["xlsx_si_002_missing_field"] = {
        "file": "xlsx/xlsx_si_002_missing_field.xlsx",
        "format": "xlsx",
        "role": "SI",
        "scenario": "missing_required_field",
        "is_baseline_acceptance": True,
        "expected_fields": {
            "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
            "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
            "notify_party": "MARITIME CUSTOMS BROKERS INC",
            "port_of_loading": None,
            "port_of_discharge": "ROTTERDAM",
            "container_count": 2,
            "gross_weight_kg": "22000",
        },
        "missing_fields": ["port_of_loading"],
        "conflicting_fields": [],
        "pair_id": None,
        "tags": ["PAR-XLSX-001", "missing_pol"],
    }

    # ==========================================================================
    # MANIFEST JSON CREATION
    # ==========================================================================
    manifest = {
        "manifest_version": "1.1",
        "total_documents": len(fixtures_meta),
        "total_pairs": len(pairs_meta),
        "format_distribution": {
            "txt": sum(1 for f in fixtures_meta.values() if f["format"] == "txt"),
            "docx": sum(1 for f in fixtures_meta.values() if f["format"] == "docx"),
            "pdf": sum(1 for f in fixtures_meta.values() if f["format"] == "pdf"),
            "pdf_raster": sum(1 for f in fixtures_meta.values() if f["format"] == "pdf_raster"),
            "xlsx": sum(1 for f in fixtures_meta.values() if f["format"] == "xlsx"),
            "malformed": sum(1 for f in fixtures_meta.values() if "malformed" in f["format"] or f.get("is_corrupted")),
        },
        "baseline_acceptance_count": sum(1 for f in fixtures_meta.values() if f.get("is_baseline_acceptance", True)),
        "exploratory_count": sum(1 for f in fixtures_meta.values() if not f.get("is_baseline_acceptance", True)),
        "governance_rules": {
            "default_discovery_filter": "is_baseline_acceptance == true",
            "exploratory_opt_in_required": True,
            "forbidden_as_implicit_baseline": [
                "POL",
                "POD",
                "Total Containers",
                "SAME AS CONSIGNEE dereferencing",
            ],
        },
        "pairs": pairs_meta,
        "documents": fixtures_meta,
    }

    manifest_path = BASE_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as fp:
        json.dump(manifest, fp, indent=2)

    print(f"Generated {len(fixtures_meta)} synthetic documents across {len(manifest['format_distribution'])} formats.")
    print("Format distribution:", manifest["format_distribution"])
    print(f"Baseline Acceptance fixtures: {manifest['baseline_acceptance_count']}")
    print(f"Exploratory fixtures: {manifest['exploratory_count']}")
    print(f"Defined {len(pairs_meta)} reusable verification pairs.")


if __name__ == "__main__":
    main()
