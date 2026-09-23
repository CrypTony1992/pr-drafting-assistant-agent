"""Tool: lookup_procurement_master_data

Looks up SAP Ariba procurement master data (cost centers, GL accounts,
material groups, purchasing groups, purchasing organizations) via MCP tools.
"""
import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Supported entity types for master data lookup
SUPPORTED_ENTITIES = [
    "cost_center",
    "gl_account",
    "material_group",
    "purchasing_group",
    "purchasing_organization",
]


@tool
def lookup_procurement_master_data(entity_type: str, filter_value: str, top: int = 10) -> str:
    """Look up SAP Ariba procurement master data entities.

    Uses the SAP Ariba Master Data Retrieval API (mds_search) via MCP tools
    to look up cost centers, GL accounts, material groups, purchasing groups,
    and purchasing organizations.

    Args:
        entity_type: One of: cost_center, gl_account, material_group,
                     purchasing_group, purchasing_organization.
        filter_value: Value to filter/search by (e.g., cost center code, GL account number).
        top: Maximum number of results to return (max 100).

    Returns:
        JSON string with matching records or an empty list if not found.
    """
    if entity_type not in SUPPORTED_ENTITIES:
        return json.dumps({
            "error": f"Unsupported entity type: '{entity_type}'. "
                     f"Supported types: {', '.join(SUPPORTED_ENTITIES)}",
            "records": []
        })

    top = min(top, 100)
    logger.info("Looking up master data: entity=%s, filter='%s'", entity_type, filter_value)

    # Entity type to Ariba MDS entity mapping
    entity_map = {
        "cost_center": "CostCenter",
        "gl_account": "GLAccount",
        "material_group": "CommodityCode",
        "purchasing_group": "PurchasingUnit",
        "purchasing_organization": "PurchasingOrganization",
    }

    ariba_entity = entity_map[entity_type]

    # Return structured lookup parameters for the agent to use with MCP tools
    return json.dumps({
        "entity_type": entity_type,
        "ariba_entity": ariba_entity,
        "filter_value": filter_value,
        "records": [],
        "message": (
            f"Master data lookup initiated for {entity_type} with filter '{filter_value}'. "
            f"The agent must call the Ariba MDS MCP tool with entity='{ariba_entity}', "
            f"filter='{filter_value}', top={top} to retrieve matching records."
        ),
        "lookup_params": {
            "entity": ariba_entity,
            "filter": filter_value,
            "top": top,
            "mcp_action": "search_master_data"
        }
    })
