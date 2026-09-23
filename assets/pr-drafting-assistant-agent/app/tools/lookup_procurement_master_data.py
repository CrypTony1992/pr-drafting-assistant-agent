"""Tool: lookup_procurement_master_data

Looks up SAP Ariba procurement master data (cost centers, GL accounts,
material groups) and returns resolved records.
"""
import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Master data registry (mirrors mock MCP data)
_COST_CENTERS = {
    "cc-ves-emea-1042": {"id": "CC-VES-EMEA-1042", "name": "Offshore Operations EMEA", "company_code": "1042", "active": True},
    "cc-1000":          {"id": "CC-1000",           "name": "Corporate IT",             "company_code": "1000", "active": True},
}

_GL_ACCOUNTS = {
    "6200-0010": {"id": "6200-0010", "name": "Materials & Components — Offshore", "account_type": "Expense", "active": True},
    "6200-0020": {"id": "6200-0020", "name": "Office Supplies Expense",           "account_type": "Expense", "active": True},
    "400000":    {"id": "400000",    "name": "Office Supplies Expense",           "account_type": "Expense", "active": True},
}

_MATERIAL_GROUPS = {
    "elec-cable": {"id": "ELEC-CABLE", "name": "Electrical Cable & Wiring",        "purchasing_group": "PG-OFFSHORE", "purchasing_org": "1000", "active": True},
    "off-sup":    {"id": "OFF-SUP",    "name": "Office Supplies & Consumables",     "purchasing_group": "PG001",       "purchasing_org": "1000", "active": True},
    "off-eqp":    {"id": "OFF-EQP",    "name": "Office Equipment",                  "purchasing_group": "PG001",       "purchasing_org": "1000", "active": True},
    "it-edp":     {"id": "IT-EDP",     "name": "IT & Electronic Data Processing",   "purchasing_group": "PG-IT",       "purchasing_org": "1000", "active": True},
}

SUPPORTED_ENTITIES = ["cost_center", "gl_account", "material_group", "purchasing_group", "purchasing_organization"]


@tool
def lookup_procurement_master_data(entity_type: str, filter_value: str, top: int = 10) -> str:
    """Look up SAP Ariba procurement master data entities.

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
            "error": f"Unsupported entity type: '{entity_type}'. Supported: {', '.join(SUPPORTED_ENTITIES)}",
            "records": []
        })

    logger.info("Looking up master data: entity=%s, filter='%s'", entity_type, filter_value)

    key = filter_value.strip().lower()

    if entity_type == "cost_center":
        record = _COST_CENTERS.get(key)
    elif entity_type == "gl_account":
        record = _GL_ACCOUNTS.get(key)
    elif entity_type == "material_group":
        record = _MATERIAL_GROUPS.get(key)
    else:
        record = None

    if record:
        return json.dumps({"entity_type": entity_type, "filter_value": filter_value, "records": [record]})

    return json.dumps({
        "entity_type": entity_type,
        "filter_value": filter_value,
        "records": [],
        "message": f"No master data record found for {entity_type} '{filter_value}'.",
    })
