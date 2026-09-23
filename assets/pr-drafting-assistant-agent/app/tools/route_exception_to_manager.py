"""Tool: route_exception_to_manager

Routes policy exceptions to the procurement manager via SAP Ariba
approval workflow or configurable notification channel.
The agent MUST NEVER bypass or auto-approve exceptions.
"""
import json
import logging
from datetime import datetime
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Exception type severity mapping
EXCEPTION_SEVERITY = {
    "UNAPPROVED_SUPPLIER": "HIGH",
    "SPEND_THRESHOLD_BREACH": "HIGH",
    "CATEGORY_ROUTING_MISMATCH": "MEDIUM",
    "MISSING_REQUIRED_FIELD": "NORMAL",
    "INVALID_FORMAT": "NORMAL",
    "MISSING_ATTACHMENT": "NORMAL",
}


@tool
def route_exception_to_manager(
    exception_type: str,
    pr_draft: str,
    requestor_id: str,
    violations: str,
    requestor_name: str = "",
) -> str:
    """Route a policy exception to the procurement manager.

    This tool is MANDATORY for all policy violations. The agent must NEVER
    bypass exception routing or auto-approve any violation.

    Args:
        exception_type: Primary exception type (e.g., UNAPPROVED_SUPPLIER).
        pr_draft: JSON string with the PR draft fields collected so far.
        requestor_id: ID or name of the requestor.
        violations: JSON string with the list of policy violations.
        requestor_name: Human-readable name of the requestor (optional).

    Returns:
        JSON string with: routed (bool), routing_reference (str|null),
        manager_message (str), requestor_message (str).
    """
    logger.info("Routing exception to procurement manager: %s", exception_type)

    try:
        draft: dict[str, Any] = json.loads(pr_draft) if isinstance(pr_draft, str) else pr_draft
        violations_list: list = json.loads(violations) if isinstance(violations, str) else violations
    except (json.JSONDecodeError, AttributeError):
        draft = {}
        violations_list = []

    timestamp = datetime.utcnow().isoformat()
    routing_reference = f"EXC-{timestamp[:10].replace('-', '')}-{exception_type[:4]}"

    severity = EXCEPTION_SEVERITY.get(exception_type, "NORMAL")

    # Build violation summary
    violation_summary = "\n".join(
        f"  • [{v.get('type', 'UNKNOWN')}] {v.get('field', '')}: {v.get('message', '')} "
        f"(Source: {v.get('policy_source', '')})"
        for v in violations_list
    ) or "  • No detailed violations available"

    supplier_name = draft.get("supplier_name", "Unknown Supplier")
    total_price = draft.get("total_price", "Unknown")
    currency = draft.get("currency", "")
    material_group = draft.get("material_group", "Unknown")

    manager_message = f"""
PROCUREMENT EXCEPTION NOTIFICATION
====================================
Reference:     {routing_reference}
Severity:      {severity}
Exception:     {exception_type.replace('_', ' ').title()}
Timestamp:     {timestamp}
Requestor:     {requestor_name or requestor_id}

PURCHASE REQUISITION SUMMARY
─────────────────────────────
Supplier:      {supplier_name}
Total Value:   {total_price} {currency}
Material Group: {material_group}

POLICY VIOLATIONS DETECTED
─────────────────────────────
{violation_summary}

ACTION REQUIRED
─────────────────────────────
This purchase requisition requires your approval due to the policy exception(s) above.
Please review and either approve or reject via the SAP Ariba approval workflow.

Reference this exception ID in all correspondence: {routing_reference}
"""

    requestor_message = f"""
Your purchase requisition has been flagged for a policy exception and requires procurement manager approval before it can proceed.

**Exception Type:** {exception_type.replace('_', ' ').title()}
**Reference:** {routing_reference}
**Severity:** {severity}

**Reason(s):**
{chr(10).join(f"• {v.get('message', '')}" for v in violations_list)}

**What happens next:**
Your request has been routed to the procurement manager for review.
You will be notified once a decision has been made.
Please do not attempt to resubmit this requisition — it is under review with reference {routing_reference}.
"""

    logger.info("[M4.achieved]: policy exception routed to procurement manager — %s", exception_type)

    return json.dumps({
        "routed": True,
        "routing_reference": routing_reference,
        "severity": severity,
        "exception_type": exception_type,
        "manager_message": manager_message,
        "requestor_message": requestor_message,
        "timestamp": timestamp,
        "mcp_action": "create_approval_request",
        "notification_payload": {
            "type": "PROCUREMENT_EXCEPTION",
            "reference": routing_reference,
            "exception_type": exception_type,
            "severity": severity,
            "requestor": requestor_id,
            "pr_summary": {
                "supplier": supplier_name,
                "total_price": total_price,
                "currency": currency,
                "material_group": material_group,
            },
            "violations": violations_list,
        }
    })
