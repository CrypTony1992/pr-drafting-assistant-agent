"""Tool: assemble_pr_draft

Assembles the final PR draft with procurement channel recommendation,
policy justification, and complete decision trace.
Requires explicit requestor confirmation before submission.
"""
import json
import logging
from datetime import date
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Procurement channel thresholds in EUR (VWS-PROC-002 §6)
CATALOG_THRESHOLD = 5_000.0   # pre-approved catalogue items under €5,000
SPOT_BUY_THRESHOLD = 49_999.0  # standard spot buy up to Tier 2 ceiling

# Material group prefixes mapped to strategic categories
STRATEGIC_CATEGORIES = {"SVC", "CONS"}


def _determine_channel(total_price: float, material_group: str, is_catalog_item: bool = False) -> tuple[str, str, str]:
    """Determine the appropriate procurement channel."""
    mg_upper = (material_group or "").upper()

    # Check for strategic/services category
    is_strategic = any(mg_upper.startswith(cat) for cat in STRATEGIC_CATEGORIES)

    if is_catalog_item and total_price <= CATALOG_THRESHOLD:
        return (
            "catalog",
            f"Item available in catalog and total spend ({total_price:.2f}) ≤ EUR {CATALOG_THRESHOLD:,.0f} catalog threshold → Ariba Catalogue eligible",
            "VWS-PROC-002 §6 – Procurement Channels"
        )
    elif not is_strategic and total_price <= SPOT_BUY_THRESHOLD:
        return (
            "spot_buy",
            f"Approved supplier confirmed and total spend ({total_price:.2f}) ≤ EUR {SPOT_BUY_THRESHOLD:,.0f} → SAP Ariba Guided Buying (Spot Buy)",
            "VWS-PROC-002 §6 – Procurement Channels"
        )
    else:
        reason = (f"Total spend ({total_price:.2f}) > EUR {SPOT_BUY_THRESHOLD:,.0f} — requires Finance Director or CPO approval"
                  if not is_strategic else f"Material group '{material_group}' is a strategic/services category")
        return (
            "contract",
            f"{reason} → SAP Ariba Guided Buying (Contract Purchase required)",
            "VWS-PROC-002 §6 – Procurement Channels"
        )


@tool
def assemble_pr_draft(
    validated_fields: str,
    extraction_summary: str,
    requestor_supplied_fields: str,
    supplier_validation: str,
    master_data: str,
    policy_validation: str,
    is_catalog_item: bool = False,
) -> str:
    """Assemble the final PR draft after all validations pass.

    Args:
        validated_fields: JSON string with all validated PR fields.
        extraction_summary: JSON string summarising what was extracted from the PDF.
        requestor_supplied_fields: JSON string of fields provided by requestor during gap-filling.
        supplier_validation: JSON string from validate_supplier.
        master_data: JSON string from lookup_procurement_master_data.
        policy_validation: JSON string from validate_pr_policy (must have valid=true).
        is_catalog_item: Whether this item is available in the company catalog.

    Returns:
        JSON string with pr_draft, channel_recommendation, policy_justification,
        decision_trace, human_readable_summary, and awaiting_confirmation=true.
    """
    logger.info("Assembling final PR draft")

    try:
        fields: dict[str, Any] = json.loads(validated_fields) if isinstance(validated_fields, str) else validated_fields
        extraction: dict = json.loads(extraction_summary) if isinstance(extraction_summary, str) else extraction_summary
        requestor_fields: dict = json.loads(requestor_supplied_fields) if isinstance(requestor_supplied_fields, str) else requestor_supplied_fields
        supplier: dict = json.loads(supplier_validation) if isinstance(supplier_validation, str) else supplier_validation
        md: dict = json.loads(master_data) if isinstance(master_data, str) else master_data
        policy: dict = json.loads(policy_validation) if isinstance(policy_validation, str) else policy_validation
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning("[M3.missed]: PR draft could not be generated — JSON parse error: %s", e)
        return json.dumps({"error": f"Failed to parse input fields: {e}"})

    # Verify policy passed
    if not policy.get("valid", False):
        logger.warning("[M3.missed]: PR draft could not be generated — policy validation not passed")
        return json.dumps({
            "error": "Cannot assemble PR draft: policy validation has not passed. "
                     "Resolve all violations before calling assemble_pr_draft.",
            "violations": policy.get("violations", [])
        })

    # Determine procurement channel
    total_price = float(fields.get("total_price", 0))
    material_group = str(fields.get("material_group", ""))
    channel, justification, policy_source = _determine_channel(total_price, material_group, is_catalog_item)

    # Build the structured PR draft
    pr_draft = {
        "supplier_name": fields.get("supplier_name"),
        "supplier_id": supplier.get("supplier_id"),
        "quote_reference": fields.get("quote_reference"),
        "quote_validity_date": fields.get("quote_validity_date"),
        "items": fields.get("items", [
            {
                "item_description": fields.get("item_description"),
                "quantity": fields.get("quantity"),
                "unit": fields.get("unit", "EA"),
                "unit_price": fields.get("unit_price"),
                "total_price": fields.get("total_price"),
            }
        ]),
        "total_price": total_price,
        "currency": fields.get("currency"),
        "cost_center": fields.get("cost_center"),
        "gl_account": fields.get("gl_account"),
        "material_group": material_group,
        "purchasing_group": fields.get("purchasing_group"),
        "purchasing_organization": fields.get("purchasing_organization"),
        "delivery_date": fields.get("delivery_date"),
        "payment_terms": fields.get("payment_terms"),
    }

    # Build decision trace
    pdf_fields = [k for k, v in extraction.items() if v is not None and k != "missing_fields"]
    missing_from_pdf = extraction.get("missing_fields", [])
    requestor_provided = list(requestor_fields.keys()) if requestor_fields else []

    cost_center_resolved = "✓" if fields.get("cost_center") else "✗"
    gl_resolved = "✓" if fields.get("gl_account") else "✗"
    mg_resolved = "✓" if material_group else "✗"
    supplier_status = "✓ Approved" if supplier.get("approved") else "✗ Not Approved"
    qual_status = supplier.get("qualification_status", "Unknown")

    today = date.today().isoformat()

    decision_trace = f"""DECISION TRACE
==============
Generated: {today}

1. PDF Extraction
   - Fields extracted: {', '.join(pdf_fields) if pdf_fields else 'None'}
   - Fields requiring requestor input: {', '.join(missing_from_pdf) if missing_from_pdf else 'None'}
   - Extraction confidence: {extraction.get('extraction_confidence', 'unknown')}

2. Gap-Filling
   - Fields collected from requestor: {', '.join(f"{k}={v}" for k, v in requestor_fields.items()) if requestor_fields else 'None required'}

3. Master Data Resolution
   - Cost center [{fields.get('cost_center', 'N/A')}]: resolved {cost_center_resolved}
   - GL account [{fields.get('gl_account', 'N/A')}]: resolved {gl_resolved}
   - Material group [{material_group or 'N/A'}]: resolved {mg_resolved}

4. Supplier Validation
   - Supplier: {fields.get('supplier_name', 'Unknown')}
   - Status: {supplier_status}
   - Qualification: {qual_status}

5. Policy Validation
   - Completeness: Pass ✓
   - Format checks: Pass ✓
   - Attachment: Present ✓
   - Spend threshold: {total_price:.2f} {fields.get('currency', '')} → Pass ✓
   - Approved supplier: Pass ✓
   - Category routing: Pass ✓
   - Warnings: {len(policy.get('warnings', []))} warning(s)

6. Channel Recommendation
   - Recommended: {channel.replace('_', ' ').title()}
   - Justification: {justification}
   - Policy source: {policy_source}
"""

    # Build human-readable summary
    items = pr_draft.get("items", [])
    item_lines = []
    for i, item in enumerate(items, 1):
        item_lines.append(
            f"{i:2} | {str(item.get('item_description', '')):<35} | "
            f"{str(item.get('quantity', '')):<5} | {str(item.get('unit', 'EA')):<5} | "
            f"{str(item.get('unit_price', '')):<10} | {str(item.get('total_price', ''))}"
        )
    items_table = "\n".join(item_lines) if item_lines else "  1 | (see description above)"

    warning_lines = ""
    if policy.get("warnings"):
        warning_lines = "\n⚠️  WARNINGS:\n" + "\n".join(f"  - {w['message']}" for w in policy["warnings"])

    channel_display = {
        "catalog": "📦 Catalog Purchase",
        "spot_buy": "🛒 Spot Buy",
        "contract": "📋 Contract Purchase",
    }.get(channel, channel.replace("_", " ").title())

    human_readable = f"""
PURCHASE REQUISITION DRAFT
==========================
Date: {today}

SUPPLIER INFORMATION
────────────────────────────────────────
Supplier Name:    {pr_draft.get('supplier_name', 'N/A')}
Supplier ID:      {pr_draft.get('supplier_id') or 'Pending master data'}
Quote Reference:  {pr_draft.get('quote_reference') or 'N/A'}
Quote Validity:   {pr_draft.get('quote_validity_date') or 'N/A'}

LINE ITEMS
────────────────────────────────────────────────────────────────
 # | Description                         | Qty   | Unit  | Unit Price  | Total
────────────────────────────────────────────────────────────────
{items_table}
────────────────────────────────────────────────────────────────
                                                   TOTAL: {total_price:.2f} {pr_draft.get('currency', '')}

ACCOUNTING
────────────────────────────────────────
Cost Center:          {pr_draft.get('cost_center', 'N/A')}
GL Account:           {pr_draft.get('gl_account', 'N/A')}
Material Group:       {pr_draft.get('material_group', 'N/A')}
Purchasing Group:     {pr_draft.get('purchasing_group') or 'N/A'}
Purchasing Org:       {pr_draft.get('purchasing_organization') or 'N/A'}

LOGISTICS
────────────────────────────────────────
Delivery Date:    {pr_draft.get('delivery_date', 'N/A')}
Payment Terms:    {pr_draft.get('payment_terms', 'N/A')}

PROCUREMENT RECOMMENDATION
────────────────────────────────────────
Channel:          {channel_display}
Justification:    {justification}
Policy Reference: {policy_source}
{warning_lines}

POLICY STATUS: ✅ ALL CHECKS PASSED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Please review the purchase requisition draft above carefully.
Type **CONFIRM** to submit to SAP S/4HANA, or describe any corrections needed.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    logger.info("[M3.achieved]: PR draft presented to requestor with channel recommendation")

    return json.dumps({
        "pr_draft": pr_draft,
        "channel_recommendation": channel,
        "policy_justification": justification,
        "policy_source": policy_source,
        "decision_trace": decision_trace,
        "human_readable_summary": human_readable,
        "awaiting_confirmation": True,
    })
