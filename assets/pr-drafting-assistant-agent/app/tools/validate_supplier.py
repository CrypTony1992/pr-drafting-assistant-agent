"""Tool: validate_supplier

Validates whether a supplier is in the SAP Ariba approved supplier list
using the Ariba Supplier Data Pagination API via MCP tools.
"""
import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Approved supplier registry (mirrors mock MCP data)
_APPROVED_SUPPLIERS = {
    "nexans a/s":       {"vendor_id": "VENDOR-NEXANS",     "erp_id": "V-200081", "status": "Active", "qualification": "Qualified"},
    "staples denmark":  {"vendor_id": "VENDOR-STAPLES-DK", "erp_id": "V-100112", "status": "Active", "qualification": "Qualified"},
    "acme office solutions ltd.": {"vendor_id": "VENDOR-OFFICESOL", "erp_id": "V-100045", "status": "Active", "qualification": "Qualified"},
}


@tool
def validate_supplier(supplier_name: str, erp_vendor_id: str = "") -> str:
    """Check if a supplier is in the SAP Ariba approved supplier list.

    Args:
        supplier_name: The supplier's name as it appears on the quotation.
        erp_vendor_id: Optional ERP vendor ID if known.

    Returns:
        JSON string with keys: approved (bool), supplier_id (str|null),
        qualification_status (str|null), message (str).
    """
    logger.info("Validating supplier: %s (ERP ID: %s)", supplier_name, erp_vendor_id or "N/A")

    key = supplier_name.strip().lower()
    match = _APPROVED_SUPPLIERS.get(key)

    if match:
        logger.info("[validate_supplier]: %s found in approved supplier list", supplier_name)
        return json.dumps({
            "approved": True,
            "supplier_id": match["vendor_id"],
            "erp_vendor_id": match["erp_id"],
            "qualification_status": match["qualification"],
            "vendor_status": match["status"],
            "message": f"Supplier '{supplier_name}' is on the Approved Vendor List. Status: {match['status']}, Qualification: {match['qualification']}.",
        })

    logger.warning("[validate_supplier]: %s not found in approved supplier list", supplier_name)
    return json.dumps({
        "approved": False,
        "supplier_id": None,
        "erp_vendor_id": None,
        "qualification_status": None,
        "vendor_status": "Not Found",
        "message": f"Supplier '{supplier_name}' is not on the Approved Vendor List. Procurement manager approval required before a PO can be raised.",
    })
