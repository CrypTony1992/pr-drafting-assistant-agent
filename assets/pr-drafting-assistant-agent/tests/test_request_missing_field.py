"""Unit tests for request_missing_field tool."""
import pytest


@pytest.fixture(autouse=True)
def setup_path(add_agent_to_path):
    pass


def test_known_field_returns_question():
    from tools.request_missing_field import request_missing_field
    result = request_missing_field.invoke({"field_name": "cost_center"})
    assert isinstance(result, str)
    assert len(result) > 10
    # Should ask about cost center
    assert "cost center" in result.lower() or "cost" in result.lower()


def test_unknown_field_returns_generic_question():
    from tools.request_missing_field import request_missing_field
    result = request_missing_field.invoke({"field_name": "custom_field_xyz"})
    assert isinstance(result, str)
    assert "custom" in result.lower() or "field" in result.lower()


def test_context_appended_to_question():
    from tools.request_missing_field import request_missing_field
    result = request_missing_field.invoke({
        "field_name": "gl_account",
        "context": "needed for accounting assignment"
    })
    assert isinstance(result, str)
    assert "needed for accounting assignment" in result


def test_each_field_has_specific_question():
    from tools.request_missing_field import request_missing_field
    fields = ["supplier_name", "quantity", "unit_price", "currency", "delivery_date",
              "payment_terms", "cost_center", "gl_account", "material_group"]
    for field in fields:
        result = request_missing_field.invoke({"field_name": field})
        assert isinstance(result, str)
        assert len(result) > 5, f"Question too short for field: {field}"


def test_returns_single_string_not_list():
    """Tool must return a single question, never a list of questions."""
    from tools.request_missing_field import request_missing_field
    result = request_missing_field.invoke({"field_name": "delivery_date"})
    assert isinstance(result, str)
    assert not isinstance(result, list)
