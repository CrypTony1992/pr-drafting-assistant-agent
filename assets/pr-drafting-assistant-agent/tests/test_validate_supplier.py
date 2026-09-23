"""Unit tests for validate_supplier tool."""
import json
import pytest


@pytest.fixture(autouse=True)
def setup_path(add_agent_to_path):
    pass


def test_returns_json_string():
    from tools.validate_supplier import validate_supplier
    result = validate_supplier.invoke({"supplier_name": "Acme Office Solutions"})
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_result_has_required_keys():
    from tools.validate_supplier import validate_supplier
    result = json.loads(validate_supplier.invoke({"supplier_name": "Test Supplier"}))
    assert "approved" in result
    assert "supplier_id" in result
    assert "qualification_status" in result
    assert "message" in result


def test_approved_is_bool():
    from tools.validate_supplier import validate_supplier
    result = json.loads(validate_supplier.invoke({"supplier_name": "Test Supplier"}))
    assert isinstance(result["approved"], bool)


def test_with_erp_vendor_id():
    from tools.validate_supplier import validate_supplier
    result = json.loads(validate_supplier.invoke({
        "supplier_name": "Acme Corp",
        "erp_vendor_id": "V-100045"
    }))
    assert "V-100045" in result.get("message", "") or result.get("lookup_params", {}).get("erp_vendor_id") == "V-100045"


def test_lookup_params_present():
    from tools.validate_supplier import validate_supplier
    result = json.loads(validate_supplier.invoke({"supplier_name": "GlobalTech Inc"}))
    assert "lookup_params" in result
    params = result["lookup_params"]
    assert params["supplier_name"] == "GlobalTech Inc"
    assert params["mcp_action"] == "getVendors"


def test_supplier_name_in_message():
    from tools.validate_supplier import validate_supplier
    result = json.loads(validate_supplier.invoke({"supplier_name": "SpecificVendor Ltd"}))
    assert "SpecificVendor Ltd" in result.get("message", "") or \
           "SpecificVendor Ltd" in result.get("lookup_params", {}).get("filter_hint", "")
