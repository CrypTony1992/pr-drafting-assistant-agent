"""Unit tests for assemble_pr_draft tool."""
import json
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def setup_path(add_agent_to_path):
    pass


def _future_date(days=30) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _mock_load(path):
    return "Mock skill content"


def _valid_inputs():
    return {
        "validated_fields": json.dumps({
            "supplier_name": "Acme Office Solutions",
            "item_description": "HP LaserJet Pro 400 Printer",
            "quantity": 2,
            "unit_price": 249.99,
            "currency": "USD",
            "total_price": 499.98,
            "delivery_date": _future_date(30),
            "payment_terms": "Net 30",
            "cost_center": "CC-1000",
            "gl_account": "400000",
            "material_group": "OFF-EQP",
            "purchasing_group": "PG001",
            "purchasing_organization": "1000",
            "quote_reference": "QT-2024-00145",
        }),
        "extraction_summary": json.dumps({
            "supplier_name": "Acme Office Solutions",
            "missing_fields": ["cost_center", "gl_account", "material_group"],
            "extraction_confidence": "high",
        }),
        "requestor_supplied_fields": json.dumps({
            "cost_center": "CC-1000",
            "gl_account": "400000",
            "material_group": "OFF-EQP",
        }),
        "supplier_validation": json.dumps({
            "approved": True,
            "supplier_id": "V-100045",
            "qualification_status": "Qualified",
        }),
        "master_data": json.dumps({"records": [{"id": "OFF-EQP", "purchasingGroup": "PG001"}]}),
        "policy_validation": json.dumps({"valid": True, "violations": [], "warnings": []}),
        "is_catalog_item": False,
    }


def test_successful_draft_assembly():
    from tools.assemble_pr_draft import assemble_pr_draft
    with patch("load_skill_resources.load", side_effect=_mock_load):
        result = json.loads(assemble_pr_draft.invoke(_valid_inputs()))
    assert "pr_draft" in result
    assert "channel_recommendation" in result
    assert "policy_justification" in result
    assert "decision_trace" in result
    assert "human_readable_summary" in result
    assert result["awaiting_confirmation"] is True


def test_channel_recommendation_spot_buy():
    from tools.assemble_pr_draft import assemble_pr_draft
    with patch("load_skill_resources.load", side_effect=_mock_load):
        result = json.loads(assemble_pr_draft.invoke(_valid_inputs()))
    assert result["channel_recommendation"] == "spot_buy"


def test_channel_recommendation_catalog():
    from tools.assemble_pr_draft import assemble_pr_draft
    inputs = _valid_inputs()
    fields = json.loads(inputs["validated_fields"])
    fields["total_price"] = 50.0
    fields["quantity"] = 1
    fields["unit_price"] = 50.0
    inputs["validated_fields"] = json.dumps(fields)
    inputs["is_catalog_item"] = True
    with patch("load_skill_resources.load", side_effect=_mock_load):
        result = json.loads(assemble_pr_draft.invoke(inputs))
    assert result["channel_recommendation"] == "catalog"


def test_channel_recommendation_contract_high_spend():
    from tools.assemble_pr_draft import assemble_pr_draft
    inputs = _valid_inputs()
    fields = json.loads(inputs["validated_fields"])
    fields["total_price"] = 50000.0
    fields["quantity"] = 200
    fields["unit_price"] = 250.0
    inputs["validated_fields"] = json.dumps(fields)
    with patch("load_skill_resources.load", side_effect=_mock_load):
        result = json.loads(assemble_pr_draft.invoke(inputs))
    assert result["channel_recommendation"] == "contract"


def test_pr_draft_has_required_fields():
    from tools.assemble_pr_draft import assemble_pr_draft
    with patch("load_skill_resources.load", side_effect=_mock_load):
        result = json.loads(assemble_pr_draft.invoke(_valid_inputs()))
    draft = result["pr_draft"]
    assert draft["supplier_name"] == "Acme Office Solutions"
    assert draft["cost_center"] == "CC-1000"
    assert draft["gl_account"] == "400000"
    assert draft["currency"] == "USD"


def test_fails_when_policy_not_valid():
    from tools.assemble_pr_draft import assemble_pr_draft
    inputs = _valid_inputs()
    inputs["policy_validation"] = json.dumps({
        "valid": False,
        "violations": [{"type": "UNAPPROVED_SUPPLIER", "field": "supplier_name", "message": "Not approved", "policy_source": "Policy §5.1"}],
        "warnings": []
    })
    with patch("load_skill_resources.load", side_effect=_mock_load):
        result = json.loads(assemble_pr_draft.invoke(inputs))
    assert "error" in result


def test_awaiting_confirmation_always_true():
    from tools.assemble_pr_draft import assemble_pr_draft
    with patch("load_skill_resources.load", side_effect=_mock_load):
        result = json.loads(assemble_pr_draft.invoke(_valid_inputs()))
    assert result["awaiting_confirmation"] is True


def test_decision_trace_contains_key_sections():
    from tools.assemble_pr_draft import assemble_pr_draft
    with patch("load_skill_resources.load", side_effect=_mock_load):
        result = json.loads(assemble_pr_draft.invoke(_valid_inputs()))
    trace = result["decision_trace"]
    assert "PDF Extraction" in trace
    assert "Supplier Validation" in trace
    assert "Policy Validation" in trace
    assert "Channel Recommendation" in trace


def test_human_readable_summary_contains_confirm_prompt():
    from tools.assemble_pr_draft import assemble_pr_draft
    with patch("load_skill_resources.load", side_effect=_mock_load):
        result = json.loads(assemble_pr_draft.invoke(_valid_inputs()))
    summary = result["human_readable_summary"]
    assert "CONFIRM" in summary
