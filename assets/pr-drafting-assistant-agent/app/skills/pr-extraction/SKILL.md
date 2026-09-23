---
name: pr-extraction
description: Step-by-step LLM prompt instructions for extracting PR fields from a supplier quotation PDF. Returns structured JSON with extracted fields and a list of nulls for unextractable fields.
---

# PR Extraction Skill

Use this skill when the agent needs to extract purchase requisition fields from a supplier quotation PDF.

## When to Use This Skill

Load this skill before calling the `extract_pr_from_pdf` tool. The LLM will use these instructions as its extraction prompt.

## Fields to Extract

Extract the following fields from the quotation document. For each field that cannot be confidently extracted, return `null` — do NOT guess or infer:

| Field | Description | Example |
|-------|-------------|---------|
| `supplier_name` | Legal name of the supplier/vendor | "Acme Office Solutions Ltd." |
| `supplier_address` | Supplier's address if present | "123 Main St, London, UK" |
| `item_description` | Description of each line item | "HP LaserJet Pro 400 Printer" |
| `quantity` | Numeric quantity per line item | 5 |
| `unit` | Unit of measure | "EA", "BOX", "KG" |
| `unit_price` | Price per unit (numeric only, no currency symbol) | 249.99 |
| `currency` | ISO 4217 currency code (infer from symbol if needed: $ → USD, € → EUR, £ → GBP) | "USD" |
| `total_price` | Total price for the line (quantity × unit_price) | 1249.95 |
| `delivery_date` | Requested or promised delivery date (convert to YYYY-MM-DD) | "2025-03-15" |
| `payment_terms` | Payment terms string | "Net 30", "2/10 Net 30" |
| `quote_validity_date` | Date until which the quote is valid (convert to YYYY-MM-DD) | "2025-02-28" |
| `quote_reference` | Supplier's quotation reference number | "QT-2024-00145" |
| `contact_name` | Supplier contact person name | "Jane Smith" |
| `contact_email` | Supplier contact email | "jsmith@acme.com" |

## Extraction Instructions

1. Read the entire document carefully before extracting any field
2. For numeric fields (`quantity`, `unit_price`, `total_price`): return only the numeric value, strip currency symbols, thousand separators, and units
3. For date fields: convert all date formats to ISO 8601 (YYYY-MM-DD). If only month/year is given, use the last day of the month
4. For `currency`: infer from context — currency symbol in the document, supplier country, or explicitly stated currency
5. If multiple line items exist: return an array of items, each with their own `item_description`, `quantity`, `unit`, `unit_price`, and `total_price`
6. For fields that span multiple lines or are split across the document, concatenate intelligently
7. **CRITICAL: Return `null` for any field you cannot extract with high confidence — do NOT hallucinate or guess**

## Output Format

Return a JSON object:

```json
{
  "supplier_name": "string or null",
  "supplier_address": "string or null",
  "items": [
    {
      "item_description": "string or null",
      "quantity": number or null,
      "unit": "string or null",
      "unit_price": number or null,
      "currency": "string or null",
      "total_price": number or null
    }
  ],
  "delivery_date": "YYYY-MM-DD or null",
  "payment_terms": "string or null",
  "quote_validity_date": "YYYY-MM-DD or null",
  "quote_reference": "string or null",
  "contact_name": "string or null",
  "contact_email": "string or null",
  "missing_fields": ["list of field names that are null or could not be extracted"],
  "extraction_confidence": "high | medium | low",
  "extraction_notes": "any notes about ambiguous or uncertain fields"
}
```

## Confidence Levels

- **high**: All key fields extracted cleanly with no ambiguity
- **medium**: Most fields extracted; 1-2 fields are uncertain or required inference
- **low**: Several fields missing or uncertain; significant gap-filling will be required

## Post-Extraction: Fields NOT in the Quotation

The following PR fields will NEVER appear in a supplier quotation — they must always be requested from the requestor:

- `cost_center` — internal accounting code
- `gl_account` — internal GL account number
- `material_group` — procurement category code
- `purchasing_group` — procurement team responsible
- `purchasing_organization` — buying org

These must always be added to `missing_fields` regardless of what the document contains.
