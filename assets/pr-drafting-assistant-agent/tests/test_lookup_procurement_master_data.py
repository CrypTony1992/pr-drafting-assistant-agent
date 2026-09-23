"""Unit tests for lookup_procurement_master_data tool."""
import json
import pytest


@pytest.fixture(autouse=True)
def setup_path(add_agent_to_path):
    pass


def test_returns_json_string():
    from tools.lookup_procurement_master_data import lookup_procurement_master_data
    result = lookup_procurement_master_data.invoke({"entity_type": "cost_center", "filter_value": "CC-1000"})
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_cost_center_lookup():
    from tools.lookup_procurement_master_data import lookup_procurement_master_data
    result = json.loads(lookup_procurement_master_data.invoke({
        "entity_type": "cost_center",
        "filter_value": "CC-1000"
    }))
    assert result["entity_type"] == "cost_center"
    assert result["ariba_entity"] == "CostCenter"
    assert "lookup_params" in result


def test_gl_account_lookup():
    from tools.lookup_procurement_master_data import lookup_procurement_master_data
    result = json.loads(lookup_procurement_master_data.invoke({
        "entity_type": "gl_account",
        "filter_value": "400000"
    }))
    assert result["entity_type"] == "gl_account"
    assert result["ariba_entity"] == "GLAccount"


def test_material_group_lookup():
    from tools.lookup_procurement_master_data import lookup_procurement_master_data
    result = json.loads(lookup_procurement_master_data.invoke({
        "entity_type": "material_group",
        "filter_value": "OFF-EQP"
    }))
    assert result["entity_type"] == "material_group"
    assert result["ariba_entity"] == "CommodityCode"


def test_unsupported_entity_type_returns_error():
    from tools.lookup_procurement_master_data import lookup_procurement_master_data
    result = json.loads(lookup_procurement_master_data.invoke({
        "entity_type": "unsupported_entity",
        "filter_value": "anything"
    }))
    assert "error" in result
    assert result["records"] == []


def test_top_capped_at_100():
    from tools.lookup_procurement_master_data import lookup_procurement_master_data
    result = json.loads(lookup_procurement_master_data.invoke({
        "entity_type": "purchasing_group",
        "filter_value": "PG001",
        "top": 999
    }))
    assert result["lookup_params"]["top"] == 100


def test_all_supported_entity_types():
    from tools.lookup_procurement_master_data import lookup_procurement_master_data, SUPPORTED_ENTITIES
    for entity_type in SUPPORTED_ENTITIES:
        result = json.loads(lookup_procurement_master_data.invoke({
            "entity_type": entity_type,
            "filter_value": "test"
        }))
        assert "error" not in result, f"Unexpected error for entity type: {entity_type}"
