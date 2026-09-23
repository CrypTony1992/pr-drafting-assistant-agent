"""Unit tests for route_exception_to_manager tool."""
import json
import pytest


@pytest.fixture(autouse=True)
def setup_path(add_agent_to_path):
    pass


def _sample_pr_draft():
    return json.dumps({
        "supplier_name": "Unknown Vendor Corp",
        "total_price": 50000.0,
        "currency": "USD",
        "material_group": "IT-EDP",
    })


def _sample_violations(exception_type="UNAPPROVED_SUPPLIER"):
    return json.dumps([{
        "type": exception_type,
        "field": "supplier_name",
        "message": f"Test violation for {exception_type}",
        "policy_source": "PR Policy §5.1"
    }])


def test_returns_json_string():
    from tools.route_exception_to_manager import route_exception_to_manager
    result = route_exception_to_manager.invoke({
        "exception_type": "UNAPPROVED_SUPPLIER",
        "pr_draft": _sample_pr_draft(),
        "requestor_id": "EMP-001",
        "violations": _sample_violations(),
    })
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_routed_is_true():
    from tools.route_exception_to_manager import route_exception_to_manager
    result = json.loads(route_exception_to_manager.invoke({
        "exception_type": "UNAPPROVED_SUPPLIER",
        "pr_draft": _sample_pr_draft(),
        "requestor_id": "EMP-001",
        "violations": _sample_violations(),
    }))
    assert result["routed"] is True


def test_routing_reference_present():
    from tools.route_exception_to_manager import route_exception_to_manager
    result = json.loads(route_exception_to_manager.invoke({
        "exception_type": "UNAPPROVED_SUPPLIER",
        "pr_draft": _sample_pr_draft(),
        "requestor_id": "EMP-001",
        "violations": _sample_violations(),
    }))
    assert result["routing_reference"] is not None
    assert len(result["routing_reference"]) > 0


def test_manager_message_contains_exception_info():
    from tools.route_exception_to_manager import route_exception_to_manager
    result = json.loads(route_exception_to_manager.invoke({
        "exception_type": "SPEND_THRESHOLD_BREACH",
        "pr_draft": _sample_pr_draft(),
        "requestor_id": "EMP-001",
        "violations": _sample_violations("SPEND_THRESHOLD_BREACH"),
    }))
    manager_msg = result["manager_message"]
    assert "SPEND" in manager_msg or "Spend" in manager_msg


def test_requestor_message_is_helpful():
    from tools.route_exception_to_manager import route_exception_to_manager
    result = json.loads(route_exception_to_manager.invoke({
        "exception_type": "UNAPPROVED_SUPPLIER",
        "pr_draft": _sample_pr_draft(),
        "requestor_id": "EMP-001",
        "violations": _sample_violations(),
    }))
    req_msg = result["requestor_message"]
    assert len(req_msg) > 50  # meaningful message
    # Should tell requestor not to resubmit
    assert "submit" in req_msg.lower() or "review" in req_msg.lower()


def test_all_exception_types_route_successfully():
    from tools.route_exception_to_manager import route_exception_to_manager, EXCEPTION_SEVERITY
    for exc_type in EXCEPTION_SEVERITY.keys():
        result = json.loads(route_exception_to_manager.invoke({
            "exception_type": exc_type,
            "pr_draft": _sample_pr_draft(),
            "requestor_id": "EMP-001",
            "violations": _sample_violations(exc_type),
        }))
        assert result["routed"] is True, f"Expected routed=True for {exc_type}"


def test_notification_payload_present():
    from tools.route_exception_to_manager import route_exception_to_manager
    result = json.loads(route_exception_to_manager.invoke({
        "exception_type": "CATEGORY_ROUTING_MISMATCH",
        "pr_draft": _sample_pr_draft(),
        "requestor_id": "EMP-002",
        "violations": _sample_violations("CATEGORY_ROUTING_MISMATCH"),
        "requestor_name": "Jane Smith",
    }))
    assert "notification_payload" in result
    payload = result["notification_payload"]
    assert payload["type"] == "PROCUREMENT_EXCEPTION"
    assert payload["exception_type"] == "CATEGORY_ROUTING_MISMATCH"
