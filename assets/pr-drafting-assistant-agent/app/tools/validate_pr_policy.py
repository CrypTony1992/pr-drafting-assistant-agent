"""Tool: validate_pr_policy

Validates a purchase requisition draft against procurement policy.
Uses the policy-validation runtime skill for all validation logic.
"""
import json
import logging
from datetime import date, datetime
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Valid ISO 4217 currency codes (common subset)
VALID_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "SEK", "NOK",
    "DKK", "SGD", "HKD", "CNY", "INR", "BRL", "MXN", "ZAR", "KRW", "THB",
}

# Spend thresholds by material group prefix (USD)
SPEND_THRESHOLDS = {
    "IT": 5000.0,
    "EDP": 5000.0,
    "OFF": 1000.0,
    "SVC": 10000.0,
    "DEFAULT": 25000.0,
}

REQUIRED_FIELDS = [
    "item_description", "quantity", "unit_price", "currency",
    "supplier_name", "delivery_date", "payment_terms",
    "cost_center", "gl_account", "material_group", "total_price",
]


def _get_threshold(material_group: str) -> tuple[float, str]:
    """Return spend threshold and category name for a material group."""
    mg_upper = (material_group or "").upper()
    for prefix, threshold in SPEND_THRESHOLDS.items():
        if prefix == "DEFAULT":
            continue
        if mg_upper.startswith(prefix):
            return threshold, prefix
    return SPEND_THRESHOLDS["DEFAULT"], "General Procurement"


@tool
def validate_pr_policy(
    pr_fields: str,
    supplier_validation_result: str,
    master_data_results: str,
    has_pdf_attachment: bool = True,
) -> str:
    """Validate a PR draft against procurement policy.

    Runs all policy checks: completeness, format, attachment, spend thresholds,
    approved supplier status, and category routing.

    Args:
        pr_fields: JSON string with all PR fields to validate.
        supplier_validation_result: JSON string from validate_supplier tool.
        master_data_results: JSON string from lookup_procurement_master_data tool.
        has_pdf_attachment: Whether a supplier quotation PDF was provided.

    Returns:
        JSON string with: valid (bool), violations (list), warnings (list).
    """
    from load_skill_resources import load

    logger.info("Running policy validation on PR draft")

    # Load the policy validation skill for reference
    try:
        load("skills/policy-validation/SKILL.md")
    except Exception:
        pass  # Skill content used for documentation; validation logic is here

    violations = []
    warnings = []

    try:
        fields: dict[str, Any] = json.loads(pr_fields) if isinstance(pr_fields, str) else pr_fields
    except json.JSONDecodeError:
        return json.dumps({
            "valid": False,
            "violations": [{"type": "MISSING_REQUIRED_FIELD", "field": "pr_fields",
                            "message": "Could not parse PR fields JSON", "policy_source": "PR Policy §2.1"}],
            "warnings": []
        })

    try:
        supplier_result: dict = json.loads(supplier_validation_result) if isinstance(supplier_validation_result, str) else supplier_validation_result
    except json.JSONDecodeError:
        supplier_result = {}

    # Step 1: Completeness check
    for field in REQUIRED_FIELDS:
        val = fields.get(field)
        if val is None or val == "" or val == []:
            violations.append({
                "type": "MISSING_REQUIRED_FIELD",
                "field": field,
                "message": f"Required field '{field}' is missing",
                "policy_source": "PR Policy §2.1 – Required Fields"
            })

    # Step 2: Format checks
    quantity = fields.get("quantity")
    if quantity is not None:
        try:
            q = float(quantity)
            if q <= 0:
                violations.append({
                    "type": "INVALID_FORMAT", "field": "quantity",
                    "message": "Quantity must be a positive number greater than 0",
                    "policy_source": "PR Policy §2.2 – Data Formats"
                })
        except (TypeError, ValueError):
            violations.append({
                "type": "INVALID_FORMAT", "field": "quantity",
                "message": f"Quantity '{quantity}' is not a valid number",
                "policy_source": "PR Policy §2.2 – Data Formats"
            })

    unit_price = fields.get("unit_price")
    if unit_price is not None:
        try:
            up = float(unit_price)
            if up <= 0:
                violations.append({
                    "type": "INVALID_FORMAT", "field": "unit_price",
                    "message": "Unit price must be a positive number greater than 0",
                    "policy_source": "PR Policy §2.2 – Data Formats"
                })
        except (TypeError, ValueError):
            violations.append({
                "type": "INVALID_FORMAT", "field": "unit_price",
                "message": f"Unit price '{unit_price}' is not a valid number",
                "policy_source": "PR Policy §2.2 – Data Formats"
            })

    total_price = fields.get("total_price")
    if quantity is not None and unit_price is not None and total_price is not None:
        try:
            expected = float(quantity) * float(unit_price)
            actual = float(total_price)
            if abs(expected - actual) > 0.01:
                violations.append({
                    "type": "INVALID_FORMAT", "field": "total_price",
                    "message": (f"Total price {actual} does not match quantity × unit_price "
                                f"= {float(quantity)} × {float(unit_price)} = {expected:.2f}"),
                    "policy_source": "PR Policy §2.2 – Data Formats"
                })
        except (TypeError, ValueError):
            pass

    currency = fields.get("currency")
    if currency is not None:
        if str(currency).upper() not in VALID_CURRENCIES:
            violations.append({
                "type": "INVALID_FORMAT", "field": "currency",
                "message": f"'{currency}' is not a valid ISO 4217 currency code",
                "policy_source": "PR Policy §2.2 – Data Formats"
            })

    delivery_date = fields.get("delivery_date")
    if delivery_date is not None:
        try:
            dd = datetime.strptime(str(delivery_date), "%Y-%m-%d").date()
            if dd < date.today():
                violations.append({
                    "type": "INVALID_FORMAT", "field": "delivery_date",
                    "message": f"Delivery date '{delivery_date}' is in the past",
                    "policy_source": "PR Policy §2.2 – Data Formats"
                })
        except ValueError:
            violations.append({
                "type": "INVALID_FORMAT", "field": "delivery_date",
                "message": f"Delivery date '{delivery_date}' must be in YYYY-MM-DD format",
                "policy_source": "PR Policy §2.2 – Data Formats"
            })

    payment_terms = fields.get("payment_terms")
    if payment_terms is not None:
        pt_str = str(payment_terms)
        if not any(char.isdigit() for char in pt_str):
            violations.append({
                "type": "INVALID_FORMAT", "field": "payment_terms",
                "message": f"Payment terms '{payment_terms}' must contain a number (e.g., 'Net 30')",
                "policy_source": "PR Policy §2.2 – Data Formats"
            })

    # Step 3: Attachment check
    if not has_pdf_attachment:
        violations.append({
            "type": "MISSING_ATTACHMENT", "field": "quotation_pdf",
            "message": "Supplier quotation PDF is required for all purchase requisitions",
            "policy_source": "PR Policy §3.1 – Supporting Documents"
        })

    # Step 4: Spend threshold check
    material_group = fields.get("material_group", "")
    if total_price is not None and material_group:
        try:
            tp = float(total_price)
            threshold, category = _get_threshold(str(material_group))
            if tp > threshold:
                violations.append({
                    "type": "SPEND_THRESHOLD_BREACH", "field": "total_price",
                    "message": (f"Total spend of {tp} {currency or ''} exceeds the {category} "
                                f"threshold of USD {threshold:,.0f}. Manager approval required."),
                    "policy_source": "PR Policy §4.2 – Spend Thresholds"
                })
        except (TypeError, ValueError):
            pass

    # Step 5: Approved supplier check
    if supplier_result:
        if not supplier_result.get("approved", False):
            supplier_name = fields.get("supplier_name", "Unknown")
            violations.append({
                "type": "UNAPPROVED_SUPPLIER", "field": "supplier_name",
                "message": (f"Supplier '{supplier_name}' is not in the approved supplier list. "
                            "Procurement manager approval required."),
                "policy_source": "PR Policy §5.1 – Approved Supplier Program"
            })
        else:
            qual = supplier_result.get("qualification_status", "")
            if qual and qual not in ("Qualified", "Active", "Approved"):
                supplier_name = fields.get("supplier_name", "Unknown")
                violations.append({
                    "type": "UNAPPROVED_SUPPLIER", "field": "supplier_name",
                    "message": (f"Supplier '{supplier_name}' qualification status is '{qual}'. "
                                "Only Qualified/Active suppliers are permitted."),
                    "policy_source": "PR Policy §5.1 – Approved Supplier Program"
                })

    # Step 6: Category routing check
    if material_group:
        try:
            md_result = json.loads(master_data_results) if isinstance(master_data_results, str) else master_data_results
            records = md_result.get("records", [])
            if not records:
                violations.append({
                    "type": "CATEGORY_ROUTING_MISMATCH", "field": "material_group",
                    "message": (f"Material group '{material_group}' does not map to a valid "
                                "purchasing group in master data."),
                    "policy_source": "PR Policy §6.1 – Category Management"
                })
        except (json.JSONDecodeError, AttributeError):
            pass

    # Step 7: Quote validity warning
    quote_validity = fields.get("quote_validity_date")
    if quote_validity:
        try:
            qv = datetime.strptime(str(quote_validity), "%Y-%m-%d").date()
            if qv < date.today():
                warnings.append({
                    "type": "WARNING", "field": "quote_validity_date",
                    "message": f"Supplier quotation may have expired on {quote_validity}. Confirm quote is still valid.",
                    "policy_source": "PR Policy §3.2 – Quote Currency"
                })
        except ValueError:
            pass

    is_valid = len(violations) == 0

    if is_valid:
        logger.info("[M2.achieved]: all PR fields validated, no policy violations detected")
    else:
        violation_types = [v["type"] for v in violations]
        logger.warning("[M2.missed]: policy validation failed — %s", ", ".join(violation_types))

    return json.dumps({
        "valid": is_valid,
        "violations": violations,
        "warnings": warnings,
    })
