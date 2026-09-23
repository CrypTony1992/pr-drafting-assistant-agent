"""Tool: request_missing_field

Returns a natural language question asking the requestor for a specific missing PR field.
Always asks ONE field at a time — never batches multiple questions.
Never invents or suggests a default value.
"""
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Human-friendly labels and questions for each PR field
_FIELD_QUESTIONS = {
    "supplier_name": "What is the full legal name of the supplier?",
    "item_description": "Please provide a description of the item(s) you want to purchase.",
    "quantity": "How many units are you requesting?",
    "unit_price": "What is the unit price for this item? Please include the currency (e.g., USD 249.99).",
    "currency": "What currency is the pricing in? (e.g., USD, EUR, GBP)",
    "total_price": "What is the total price for this purchase requisition? Please include the currency.",
    "delivery_date": "What is the required delivery date? (Please provide in YYYY-MM-DD format, e.g., 2025-03-15)",
    "payment_terms": "What are the payment terms agreed with the supplier? (e.g., Net 30, Net 60)",
    "cost_center": "What is the cost center code for this purchase? (This is an internal accounting code, e.g., CC-1234)",
    "gl_account": "What GL account number should be charged for this purchase? (e.g., 400000)",
    "material_group": "What is the material group or commodity code for this purchase? (e.g., IT-EDP, OFF-SUP, SVC-CONS)",
    "purchasing_group": "What purchasing group should handle this requisition? (e.g., PG001)",
    "purchasing_organization": "What purchasing organization does this requisition belong to? (e.g., 1000)",
    "quote_reference": "What is the supplier's quotation reference number from the quote document?",
    "quote_validity_date": "What is the validity date of the supplier's quotation? (YYYY-MM-DD format)",
    "contact_name": "What is the name of the contact person at the supplier?",
    "contact_email": "What is the email address of the supplier contact?",
}

_DEFAULT_QUESTION = "Could you please provide the value for the field '{field}'?"


@tool
def request_missing_field(field_name: str, context: str = "") -> str:
    """Ask the requestor for a single missing PR field.

    This tool asks ONE question at a time. Never batches multiple missing fields.
    Never invents or suggests a default value.

    Args:
        field_name: The name of the missing field to ask about.
        context: Optional context about why this field is needed (shown to user).

    Returns:
        A natural language question string to present to the requestor.
    """
    question = _FIELD_QUESTIONS.get(
        field_name,
        _DEFAULT_QUESTION.format(field=field_name.replace("_", " ").title())
    )

    if context:
        question = f"{question}\n\n_Context: {context}_"

    logger.info("Requesting missing field from requestor: %s", field_name)
    return question
