"""Unit tests for submit_purchase_requisition tool."""
import json
import pytest
from datetime import date, timedelta


@pytest.fixture(autouse=True)
def setup_path(add_agent_to_path):
    pass


def _future_date(days=30) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _valid_pr_draft():
    return json.dumps({
        "pr_draft": {
            "supplier_name": "Acme Office Solutions",
            "supplier_id": "V-100045",
            "quote_reference": "QT-2024-00145",
            "items": [
                {
                    "item_description": "HP LaserJet Pro 400 Printer",
                    "quantity": 2,
                    "unit": "EA",
                    "unit_price": 249.99,
                    "total_price": 499.98,
                }
            ],
            "total_price": 499.98,
            "currency": "USD",
            "cost_center": "CC-1000",
            "gl_account": "400000",
            "material_group": "OFF-EQP",
            "purchasing_group": "PG001",
            "purchasing_organization": "1000",
            "delivery_date": _future_date(30),
            "payment_terms": "Net 30",
        },
        "channel_recommendation": "spot_buy",
        "awaiting_confirmation": True,
    })


def test_returns_json_string():
    from tools.submit_purchase_requisition import submit_purchase_requisition
    result = submit_purchase_requisition.invoke({
        "pr_draft": _valid_pr_draft(),
        "requestor_id": "EMP-001"
    })
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_result_has_success_and_odata_payload():
    from tools.submit_purchase_requisition import submit_purchase_requisition
    result = json.loads(submit_purchase_requisition.invoke({
        "pr_draft": _valid_pr_draft()
    }))
    assert "odata_payload" in result
    assert "mcp_action" in result
    assert result["mcp_action"] == "create_purchase_requisition"


def test_odata_payload_has_pr_type():
    from tools.submit_purchase_requisition import submit_purchase_requisition
    result = json.loads(submit_purchase_requisition.invoke({
        "pr_draft": _valid_pr_draft()
    }))
    payload = result["odata_payload"]
    assert payload["PurchaseRequisitionType"] == "NB"


def test_odata_payload_has_line_items():
    from tools.submit_purchase_requisition import submit_purchase_requisition
    result = json.loads(submit_purchase_requisition.invoke({
        "pr_draft": _valid_pr_draft()
    }))
    items = result["odata_payload"]["to_PurchaseReqnItem"]["results"]
    assert len(items) >= 1
    item = items[0]
    assert "PurchaseRequisitionItemText" in item
    assert "RequestedQuantity" in item
    assert "MaterialGroup" in item


def test_odata_payload_has_account_assignment():
    from tools.submit_purchase_requisition import submit_purchase_requisition
    result = json.loads(submit_purchase_requisition.invoke({
        "pr_draft": _valid_pr_draft()
    }))
    items = result["odata_payload"]["to_PurchaseReqnItem"]["results"]
    item = items[0]
    acct = item["to_PurchaseReqnAccount"]["results"][0]
    assert "CostCenter" in acct
    assert "GLAccount" in acct


def test_invalid_json_returns_error():
    from tools.submit_purchase_requisition import submit_purchase_requisition
    result = json.loads(submit_purchase_requisition.invoke({
        "pr_draft": "not valid json"
    }))
    assert result["success"] is False
    assert "error" in result


def test_handle_submission_result_success():
    from tools.submit_purchase_requisition import handle_submission_result
    mock_response = {"d": {"PurchaseRequisition": "PR-2025-00145"}}
    result = json.loads(handle_submission_result(mock_response))
    assert result["success"] is True
    assert result["pr_number"] == "PR-2025-00145"
    assert result["error"] is None


def test_handle_submission_result_failure():
    from tools.submit_purchase_requisition import handle_submission_result
    mock_response = {"error": {"message": {"value": "Validation failed: missing material group"}}}
    result = json.loads(handle_submission_result(mock_response))
    assert result["success"] is False
    assert "Validation failed" in result["error"]
