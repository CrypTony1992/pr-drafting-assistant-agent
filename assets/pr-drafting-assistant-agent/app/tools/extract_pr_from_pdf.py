"""Tool: extract_pr_from_pdf

Extracts PR fields from a supplier quotation PDF using an LLM.
Fields that cannot be confidently extracted are returned as null — never invented.
"""
import base64
import json
import logging
import os

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def extract_pr_from_pdf(pdf_content: str, filename: str = "quotation.pdf") -> str:
    """Extract purchase requisition fields from a supplier quotation PDF.

    Args:
        pdf_content: Base64-encoded PDF content OR plain text content of the quotation.
        filename: Original filename of the PDF (used for logging).

    Returns:
        JSON string with extracted fields and a list of missing/unextractable fields.
        Fields that cannot be extracted are set to null — never invented or defaulted.
    """
    from pathlib import Path
    from langchain_litellm import ChatLiteLLM
    from langchain_core.messages import HumanMessage, SystemMessage

    logger.info("[M1]: Starting PDF extraction for file: %s", filename)

    # Load the extraction skill instructions directly from disk
    _skill_path = Path(__file__).parent.parent / "skills" / "pr-extraction" / "SKILL.md"
    skill_content = _skill_path.read_text(encoding="utf-8")

    # Decode base64 if needed; otherwise treat as plain text
    try:
        decoded = base64.b64decode(pdf_content).decode("utf-8", errors="replace")
        doc_text = decoded
    except Exception:
        doc_text = pdf_content

    llm = ChatLiteLLM(
        model=os.environ.get("AICORE_LLM_MODEL", "sap/anthropic--claude-4.5-sonnet"),
        temperature=0.0,
    )

    system_msg = SystemMessage(content=skill_content)
    human_msg = HumanMessage(
        content=(
            "Please extract all purchase requisition fields from the following supplier quotation document. "
            "Follow the extraction instructions exactly. Return ONLY valid JSON.\n\n"
            "=== DOCUMENT ===\n"
            f"{doc_text}\n"
            "=== END DOCUMENT ===\n\n"
            "IMPORTANT: Return null for any field you cannot extract with high confidence. "
            "Always include cost_center, gl_account, material_group, purchasing_group, and "
            "purchasing_organization in missing_fields — these are never in a supplier quotation."
        )
    )

    try:
        response = llm.invoke([system_msg, human_msg])
        raw = response.content.strip()

        # Strip markdown code blocks if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        extracted = json.loads(raw)
        logger.info("[M1.achieved]: supplier quotation PDF processed, all PR fields extracted")
        return json.dumps(extracted)

    except json.JSONDecodeError as e:
        logger.warning("[M1.missed]: PDF extraction incomplete — JSON parse error: %s", e)
        return json.dumps({
            "supplier_name": None,
            "supplier_address": None,
            "items": [],
            "delivery_date": None,
            "payment_terms": None,
            "quote_validity_date": None,
            "quote_reference": None,
            "contact_name": None,
            "contact_email": None,
            "missing_fields": [
                "supplier_name", "item_description", "quantity", "unit_price",
                "currency", "total_price", "delivery_date", "payment_terms",
                "cost_center", "gl_account", "material_group",
                "purchasing_group", "purchasing_organization"
            ],
            "extraction_confidence": "low",
            "extraction_notes": f"LLM returned non-JSON response. Raw: {raw[:200]}",
            "error": str(e)
        })
    except Exception as e:
        logger.warning("[M1.missed]: PDF extraction incomplete — unexpected error: %s", e)
        return json.dumps({
            "error": str(e),
            "missing_fields": [
                "supplier_name", "item_description", "quantity", "unit_price",
                "currency", "total_price", "delivery_date", "payment_terms",
                "cost_center", "gl_account", "material_group"
            ],
            "extraction_confidence": "low"
        })
