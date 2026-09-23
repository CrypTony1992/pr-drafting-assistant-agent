"""Unit tests for extract_pr_from_pdf tool."""
import json
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def setup_path(add_agent_to_path):
    pass


SAMPLE_QUOTATION_TEXT = """
SUPPLIER QUOTATION
==================
Supplier: Acme Office Solutions Ltd.
Address: 123 Main Street, London, UK
Quote Reference: QT-2024-00145
Quote Date: 2025-01-15
Valid Until: 2025-03-15

Contact: Jane Smith
Email: jsmith@acme.com

LINE ITEMS:
Item 1: HP LaserJet Pro 400 Printer
Quantity: 5 EA
Unit Price: USD 249.99
Total: USD 1,249.95

Delivery Date: 2025-03-01
Payment Terms: Net 30

Total Amount: USD 1,249.95
"""

MOCK_EXTRACTION_RESPONSE = json.dumps({
    "supplier_name": "Acme Office Solutions Ltd.",
    "supplier_address": "123 Main Street, London, UK",
    "items": [
        {
            "item_description": "HP LaserJet Pro 400 Printer",
            "quantity": 5,
            "unit": "EA",
            "unit_price": 249.99,
            "currency": "USD",
            "total_price": 1249.95,
        }
    ],
    "delivery_date": "2025-03-01",
    "payment_terms": "Net 30",
    "quote_validity_date": "2025-03-15",
    "quote_reference": "QT-2024-00145",
    "contact_name": "Jane Smith",
    "contact_email": "jsmith@acme.com",
    "missing_fields": ["cost_center", "gl_account", "material_group", "purchasing_group", "purchasing_organization"],
    "extraction_confidence": "high",
    "extraction_notes": "",
})


def _make_mock_llm_response(content: str):
    mock_response = MagicMock()
    mock_response.content = content
    return mock_response


def test_successful_extraction_returns_json():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _make_mock_llm_response(MOCK_EXTRACTION_RESPONSE)

    with patch("tools.extract_pr_from_pdf.ChatLiteLLM", return_value=mock_llm), \
         patch("load_skill_resources.load", return_value="skill content"):
        from tools.extract_pr_from_pdf import extract_pr_from_pdf
        result = extract_pr_from_pdf.invoke({"pdf_content": SAMPLE_QUOTATION_TEXT})

    assert isinstance(result, str)
    parsed = json.loads(result)
    assert "supplier_name" in parsed
    assert parsed["supplier_name"] == "Acme Office Solutions Ltd."


def test_missing_fields_always_includes_internal_fields():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _make_mock_llm_response(MOCK_EXTRACTION_RESPONSE)

    with patch("tools.extract_pr_from_pdf.ChatLiteLLM", return_value=mock_llm), \
         patch("load_skill_resources.load", return_value="skill content"):
        from tools.extract_pr_from_pdf import extract_pr_from_pdf
        result = json.loads(extract_pr_from_pdf.invoke({"pdf_content": SAMPLE_QUOTATION_TEXT}))

    missing = result.get("missing_fields", [])
    assert "cost_center" in missing
    assert "gl_account" in missing
    assert "material_group" in missing


def test_invalid_json_from_llm_returns_fallback():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _make_mock_llm_response("not valid json response from LLM")

    with patch("tools.extract_pr_from_pdf.ChatLiteLLM", return_value=mock_llm), \
         patch("load_skill_resources.load", return_value="skill content"):
        from tools.extract_pr_from_pdf import extract_pr_from_pdf
        result = json.loads(extract_pr_from_pdf.invoke({"pdf_content": SAMPLE_QUOTATION_TEXT}))

    assert "missing_fields" in result
    assert result["extraction_confidence"] == "low"


def test_extraction_with_markdown_codeblock():
    """LLM sometimes wraps JSON in markdown code blocks."""
    wrapped = f"```json\n{MOCK_EXTRACTION_RESPONSE}\n```"
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _make_mock_llm_response(wrapped)

    with patch("tools.extract_pr_from_pdf.ChatLiteLLM", return_value=mock_llm), \
         patch("load_skill_resources.load", return_value="skill content"):
        from tools.extract_pr_from_pdf import extract_pr_from_pdf
        result = json.loads(extract_pr_from_pdf.invoke({"pdf_content": SAMPLE_QUOTATION_TEXT}))

    assert "supplier_name" in result


def test_extraction_error_returns_safe_fallback():
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("Connection error")

    with patch("tools.extract_pr_from_pdf.ChatLiteLLM", return_value=mock_llm), \
         patch("load_skill_resources.load", return_value="skill content"):
        from tools.extract_pr_from_pdf import extract_pr_from_pdf
        result = json.loads(extract_pr_from_pdf.invoke({"pdf_content": SAMPLE_QUOTATION_TEXT}))

    assert "error" in result
    assert "missing_fields" in result
