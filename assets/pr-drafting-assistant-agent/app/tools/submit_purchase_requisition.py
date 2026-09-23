"""Tool: submit_purchase_requisition

Submits a validated, confirmed purchase requisition to SAP S/4HANA
via the Purchase Requisition OData API through MCP tools.
"""
import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def submit_purchase_requisition(pr_draft: str, requestor_id: str = "") -> str:
    """Submit a confirmed purchase requisition to SAP S/4HANA.

    Uses the SAP S/4HANA Purchase Requisition OData API
    (API_PURCHASEREQ_PROCESS_SRV) via MCP tools to create the PR.

    This tool MUST only be called after explicit requestor confirmation.
    Never call this tool without the requestor having confirmed the PR draft.

    Args:
        pr_draft: JSON string with the validated and confirmed PR draft
                  (from assemble_pr_draft tool).
        requestor_id: Optional requestor employee ID for the PR header.

    Returns:
        JSON string with: success (bool), pr_number (str|null), error (str|null).
    """
    logger.info("Submitting purchase requisition to SAP S/4HANA")

    try:
        draft: dict[str, Any] = json.loads(pr_draft) if isinstance(pr_draft, str) else pr_draft
    except json.JSONDecodeError as e:
        logger.warning("[M5.missed]: PR submission failed — invalid JSON: %s", e)
        return json.dumps({"success": False, "pr_number": None, "error": f"Invalid PR draft JSON: {e}"})

    # Extract pr_draft from nested structure if needed
    if "pr_draft" in draft:
        pr_data = draft["pr_draft"]
    else:
        pr_data = draft

    # Build the OData payload for A_PurchaseRequisitionHeader (POST)
    # Field mapping based on API_PURCHASEREQ_PROCESS_SRV schema
    items = pr_data.get("items", [
        {
            "item_description": pr_data.get("item_description"),
            "quantity": pr_data.get("quantity"),
            "unit_price": pr_data.get("unit_price"),
            "unit": pr_data.get("unit", "EA"),
        }
    ])

    odata_payload = {
        "PurchaseRequisitionType": "NB",
        "PurchasingOrganization": pr_data.get("purchasing_organization", ""),
        "PurchasingGroup": pr_data.get("purchasing_group", ""),
        "to_PurchaseReqnItem": {
            "results": [
                {
                    "PurchaseRequisitionItemText": str(item.get("item_description", ""))[:40],
                    "RequestedQuantity": str(item.get("quantity", 1)),
                    "PurchaseRequisitionQuantityUnit": str(item.get("unit", "EA")),
                    "NetPriceAmount": str(item.get("unit_price", 0)),
                    "NetPriceCurrency": pr_data.get("currency", "USD"),
                    "MaterialGroup": pr_data.get("material_group", ""),
                    "DeliveryDate": pr_data.get("delivery_date", ""),
                    "PaymentTerms": pr_data.get("payment_terms", ""),
                    "to_PurchaseReqnAccount": {
                        "results": [
                            {
                                "CostCenter": pr_data.get("cost_center", ""),
                                "GLAccount": pr_data.get("gl_account", ""),
                            }
                        ]
                    }
                }
                for item in items
            ]
        }
    }

    # The agent will use the S/4HANA MCP tool to POST this payload to
    # A_PurchaseRequisitionHeader entity set. We return the structured payload
    # so the agent can pass it to the MCP tool.
    return json.dumps({
        "success": False,
        "pr_number": None,
        "error": None,
        "message": (
            "PR payload prepared. The agent must call the S/4HANA Purchase Requisition MCP tool "
            "to POST to A_PurchaseRequisitionHeader entity set with the payload below."
        ),
        "odata_payload": odata_payload,
        "mcp_action": "create_purchase_requisition",
        "entity_set": "A_PurchaseRequisitionHeader",
        "http_method": "POST",
        "requestor_id": requestor_id,
    })


def handle_submission_result(mcp_response: dict) -> str:
    """Process the MCP tool response from the S/4HANA API call.

    Call this after the MCP tool returns to generate the final PR submission result.

    Args:
        mcp_response: The raw response from the MCP tool call.

    Returns:
        JSON string with success, pr_number, and error fields.
    """
    try:
        # Try to extract the PR number from common S/4HANA OData response structures
        pr_number = None

        # Path 1: Standard OData v2 d.PurchaseRequisition
        if "d" in mcp_response:
            d = mcp_response["d"]
            pr_number = (
                d.get("PurchaseRequisition")
                or d.get("PurchaseRequisitionNumber")
                or d.get("Requisition")
            )

        # Path 2: Direct field on response
        if not pr_number:
            pr_number = (
                mcp_response.get("PurchaseRequisition")
                or mcp_response.get("pr_number")
                or mcp_response.get("id")
            )

        if pr_number:
            logger.info("[M5.achieved]: PR submitted successfully — PR number %s", pr_number)
            return json.dumps({"success": True, "pr_number": str(pr_number), "error": None})
        else:
            error_msg = (
                mcp_response.get("error", {}).get("message", {}).get("value")
                or mcp_response.get("error")
                or "PR number not found in response"
            )
            logger.warning("[M5.missed]: PR submission failed — %s", error_msg)
            return json.dumps({"success": False, "pr_number": None, "error": str(error_msg)})

    except Exception as e:
        logger.warning("[M5.missed]: PR submission failed — response processing error: %s", e)
        return json.dumps({"success": False, "pr_number": None, "error": str(e)})
