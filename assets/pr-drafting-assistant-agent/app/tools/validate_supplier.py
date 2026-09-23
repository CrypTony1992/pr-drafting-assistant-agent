"""Tool: validate_supplier

Validates whether a supplier is in the SAP Ariba approved supplier list
using the Ariba Supplier Data Pagination API via MCP tools.
"""
import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def validate_supplier(supplier_name: str, erp_vendor_id: str = "") -> str:
    """Check if a supplier is in the SAP Ariba approved supplier list.

    Uses the SAP Ariba Supplier Data API (supplierdatapagination) via MCP tools.
    Returns approval status, supplier ID, and qualification status.

    Args:
        supplier_name: The supplier's name as it appears on the quotation.
        erp_vendor_id: Optional ERP vendor ID if known.

    Returns:
        JSON string with keys: approved (bool), supplier_id (str|null),
        qualification_status (str|null), message (str).
    """
    logger.info("Validating supplier: %s (ERP ID: %s)", supplier_name, erp_vendor_id or "N/A")

    # This tool is invoked by the agent which will use available MCP tools
    # (getVendors / getVendorExt from sap.aribas4:apiResource:supplierdatapagination:v4)
    # to look up the supplier. The agent passes supplier_name and erp_vendor_id
    # to the appropriate MCP tool and interprets the result.
    #
    # At runtime, the agent should call the MCP supplier lookup tool and
    # check the vendorStatus / qualificationStatus fields in the response.

    # Return a structured placeholder that the agent will replace with real MCP call results
    return json.dumps({
        "approved": False,
        "supplier_id": None,
        "qualification_status": None,
        "message": (
            f"Supplier lookup initiated for '{supplier_name}'. "
            "The agent must call the Ariba Supplier Data MCP tool to complete this validation. "
            f"Filter by vendorName='{supplier_name}'"
            + (f" or erpVendorId='{erp_vendor_id}'" if erp_vendor_id else "")
            + " and check vendorStatus and qualificationStatus in the response."
        ),
        "lookup_params": {
            "supplier_name": supplier_name,
            "erp_vendor_id": erp_vendor_id,
            "mcp_action": "getVendors",
            "filter_hint": f"vendorName contains '{supplier_name}'"
        }
    })
