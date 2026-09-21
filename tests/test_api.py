import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "SDOC Shipping Document Verification Engine"
    assert "total_audited_emails" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_get_single_audit_ok():
    response = client.get("/audit/email_001")
    assert response.status_code == 200
    data = response.json()
    assert data["email_id"] == "email_001"
    assert data["category"] == "document_comparison"
    assert data["mismatch_detected"] is False
    assert data["result_summary"] == "No mismatch detected"


def test_get_single_audit_mismatch():
    response = client.get("/audit/email_025")
    assert response.status_code == 200
    data = response.json()
    assert data["email_id"] == "email_025"
    assert data["mismatch_detected"] is True
    assert any(d["field"] == "container_count" for d in data["discrepancies"])


def test_dynamic_verify_endpoint():
    req = {
        "email_id": "test_verification",
        "si_text": "Shipper: APRIL FAR EAST LTD\nConsignee: MOORIM SP CO., LTD\nNotify: UAB NOVAKOPA\nPort of Loading: PORT KLANG (MYPKG)\nPort of Discharge: CALLAO (PECLL)\nContainer Count: Three (3) Containers\nGross Weight: 25 MT",
        "bl_text": "Shipper: APRIL FAR EAST LIMITED\nConsignee: MOORIM SP CO., LTD.\nNotify Party: UAB NOVAKOPA\nLoad Port: PORT KLANG (MYPKG)\nDischarge Port: CALLAO (PECLL)\nTotal Containers: 4 x 40 HC\nG.W.: 25,000 KG",
    }
    response = client.post("/verify", json=req)
    assert response.status_code == 200
    data = response.json()
    assert data["mismatch_detected"] is True
    assert len(data["discrepancies"]) == 1
    assert data["discrepancies"][0]["field"] == "container_count"
    assert data["discrepancies"][0]["si_value"] == 3
    assert data["discrepancies"][0]["bl_value"] == 4
