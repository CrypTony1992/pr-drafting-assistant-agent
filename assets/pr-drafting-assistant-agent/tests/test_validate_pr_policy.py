"""Unit tests for validate_pr_policy tool."""
import json
import pytest
from datetime import date, timedelta


@pytest.fixture(autouse=True)
def setup_path(add_agent_to_path):
    pass


def _future_date(days=30) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _valid_pr_fields(overrides=None):
    fields = {
        "item_description": "HP LaserJet Pro 400 Printer",
        "quantity": 2,
        "unit_price": 249.99,
        "currency": "USD",
        "supplier_name": "Acme Office Solutions",
        "delivery_date": _future_date(30),
        "payment_terms": "Net 30",
        "cost_center": "CC-1000",
        "gl_account": "400000",
        "material_group": "OFF-EQP",
        "total_price": 499.98,
    }
    if overrides:
        fields.update(overrides)
    return json.dumps(fields)


def _approved_supplier():
    return json.dumps({"approved": True, "supplier_id": "V-100045", "qualification_status": "Qualified"})


def _unapproved_supplier():
    return json.dumps({"approved": False, "supplier_id": None, "qualification_status": None})


def _empty_master_data():
    return json.dumps({"records": []})


def _valid_master_data():
    return json.dumps({"records": [{"id": "OFF-EQP", "purchasingGroup": "PG001"}]})


def test_valid_pr_passes():
    from tools.validate_pr_policy import validate_pr_policy
    result = json.loads(validate_pr_policy.invoke({
        "pr_fields": _valid_pr_fields(),
        "supplier_validation_result": _approved_supplier(),
        "master_data_results": _valid_master_data(),
        "has_pdf_attachment": True,
    }))
    assert result["valid"] is True
    assert result["violations"] == []


def test_missing_required_field_fails():
    from tools.validate_pr_policy import validate_pr_policy
    fields = json.loads(_valid_pr_fields())
    del fields["cost_center"]
    result = json.loads(validate_pr_policy.invoke({
        "pr_fields": json.dumps(fields),
        "supplier_validation_result": _approved_supplier(),
        "master_data_results": _valid_master_data(),
        "has_pdf_attachment": True,
    }))
    assert result["valid"] is False
    types = [v["type"] for v in result["violations"]]
    assert "MISSING_REQUIRED_FIELD" in types


def test_unapproved_supplier_fails():
    from tools.validate_pr_policy import validate_pr_policy
    result = json.loads(validate_pr_policy.invoke({
        "pr_fields": _valid_pr_fields(),
        "supplier_validation_result": _unapproved_supplier(),
        "master_data_results": _valid_master_data(),
        "has_pdf_attachment": True,
    }))
    assert result["valid"] is False
    types = [v["type"] for v in result["violations"]]
    assert "UNAPPROVED_SUPPLIER" in types


def test_spend_threshold_breach():
    from tools.validate_pr_policy import validate_pr_policy
    # OFF category threshold is 1000 USD
    fields = _valid_pr_fields({"total_price": 2000.0, "quantity": 8, "unit_price": 250.0})
    result = json.loads(validate_pr_policy.invoke({
        "pr_fields": fields,
        "supplier_validation_result": _approved_supplier(),
        "master_data_results": _valid_master_data(),
        "has_pdf_attachment": True,
    }))
    assert result["valid"] is False
    types = [v["type"] for v in result["violations"]]
    assert "SPEND_THRESHOLD_BREACH" in types


def test_missing_attachment_fails():
    from tools.validate_pr_policy import validate_pr_policy
    result = json.loads(validate_pr_policy.invoke({
        "pr_fields": _valid_pr_fields(),
        "supplier_validation_result": _approved_supplier(),
        "master_data_results": _valid_master_data(),
        "has_pdf_attachment": False,
    }))
    assert result["valid"] is False
    types = [v["type"] for v in result["violations"]]
    assert "MISSING_ATTACHMENT" in types


def test_invalid_currency_fails():
    from tools.validate_pr_policy import validate_pr_policy
    result = json.loads(validate_pr_policy.invoke({
        "pr_fields": _valid_pr_fields({"currency": "XYZ"}),
        "supplier_validation_result": _approved_supplier(),
        "master_data_results": _valid_master_data(),
        "has_pdf_attachment": True,
    }))
    assert result["valid"] is False
    types = [v["type"] for v in result["violations"]]
    assert "INVALID_FORMAT" in types


def test_past_delivery_date_fails():
    from tools.validate_pr_policy import validate_pr_policy
    result = json.loads(validate_pr_policy.invoke({
        "pr_fields": _valid_pr_fields({"delivery_date": "2020-01-01"}),
        "supplier_validation_result": _approved_supplier(),
        "master_data_results": _valid_master_data(),
        "has_pdf_attachment": True,
    }))
    assert result["valid"] is False
    types = [v["type"] for v in result["violations"]]
    assert "INVALID_FORMAT" in types


def test_category_routing_mismatch_with_no_master_data():
    from tools.validate_pr_policy import validate_pr_policy
    result = json.loads(validate_pr_policy.invoke({
        "pr_fields": _valid_pr_fields(),
        "supplier_validation_result": _approved_supplier(),
        "master_data_results": _empty_master_data(),
        "has_pdf_attachment": True,
    }))
    assert result["valid"] is False
    types = [v["type"] for v in result["violations"]]
    assert "CATEGORY_ROUTING_MISMATCH" in types


def test_violations_have_policy_source():
    from tools.validate_pr_policy import validate_pr_policy
    fields = json.loads(_valid_pr_fields())
    del fields["gl_account"]
    result = json.loads(validate_pr_policy.invoke({
        "pr_fields": json.dumps(fields),
        "supplier_validation_result": _approved_supplier(),
        "master_data_results": _valid_master_data(),
        "has_pdf_attachment": True,
    }))
    for v in result["violations"]:
        assert "policy_source" in v
        assert len(v["policy_source"]) > 0


def test_result_structure():
    from tools.validate_pr_policy import validate_pr_policy
    result = json.loads(validate_pr_policy.invoke({
        "pr_fields": _valid_pr_fields(),
        "supplier_validation_result": _approved_supplier(),
        "master_data_results": _valid_master_data(),
        "has_pdf_attachment": True,
    }))
    assert "valid" in result
    assert "violations" in result
    assert "warnings" in result
    assert isinstance(result["violations"], list)
    assert isinstance(result["warnings"], list)
