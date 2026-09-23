---
name: policy-validation
description: Step-by-step instructions for validating PR fields against procurement policy — completeness, format, attachments, spend thresholds, approved supplier status, and category routing rules.
---

# Policy Validation Skill

Use this skill when validating a purchase requisition draft against procurement policy before presenting it to the requestor or submitting it to SAP S/4HANA.

## When to Use This Skill

Load this skill whenever the agent needs to perform policy validation on a complete (or nearly complete) set of PR fields. All checks must be run in order. Do not stop at the first violation — collect ALL violations before returning results.

## Required PR Fields

The following fields are REQUIRED for a valid PR. Absence of any field is a `MISSING_REQUIRED_FIELD` violation:

| Field | Description |
|-------|-------------|
| `item_description` | Short text describing what is being purchased |
| `quantity` | Numeric quantity of the item(s) |
| `unit_price` | Price per unit (numeric) |
| `currency` | ISO 4217 currency code (e.g. USD, EUR, GBP) |
| `supplier_name` | Name of the supplier as it appears on the quotation |
| `delivery_date` | Requested delivery date (ISO 8601 format: YYYY-MM-DD) |
| `payment_terms` | Payment terms string (e.g. "Net 30", "Net 60") |
| `cost_center` | Valid cost center code from SAP master data |
| `gl_account` | Valid GL account number from SAP master data |
| `material_group` | Material group / commodity code |
| `total_price` | Total price (quantity × unit_price; numeric) |

## Step 1: Completeness Check

For each required field listed above:
- If the field is null, empty, or missing → add a `MISSING_REQUIRED_FIELD` violation
- Violation format: `{ "type": "MISSING_REQUIRED_FIELD", "field": "<field_name>", "message": "Required field '<field_name>' is missing", "policy_source": "PR Policy §2.1 – Required Fields" }`

## Step 2: Format Checks

Run these format validations:

| Field | Check | Violation Type |
|-------|-------|----------------|
| `quantity` | Must be a positive number > 0 | `INVALID_FORMAT` |
| `unit_price` | Must be a positive number > 0 | `INVALID_FORMAT` |
| `total_price` | Must equal quantity × unit_price (tolerance: ±0.01) | `INVALID_FORMAT` |
| `currency` | Must be a valid 3-letter ISO 4217 code | `INVALID_FORMAT` |
| `delivery_date` | Must be a valid future date in YYYY-MM-DD format | `INVALID_FORMAT` |
| `payment_terms` | Must not be empty; must contain a number (e.g. "Net 30") | `INVALID_FORMAT` |

Violation format: `{ "type": "INVALID_FORMAT", "field": "<field_name>", "message": "<description of format error>", "policy_source": "PR Policy §2.2 – Data Formats" }`

## Step 3: Attachment Check

- If no supplier quotation PDF has been provided → add a `MISSING_ATTACHMENT` violation
- Violation: `{ "type": "MISSING_ATTACHMENT", "field": "quotation_pdf", "message": "Supplier quotation PDF is required for all purchase requisitions", "policy_source": "PR Policy §3.1 – Supporting Documents" }`

## Step 4: Spend Threshold Check

Apply the following thresholds by `material_group` category:

| Category | Threshold | Procurement Channel Required |
|----------|-----------|------------------------------|
| IT Equipment (`material_group` starts with "IT" or "EDP") | USD 5,000 | Contract / Preferred Supplier |
| Office Supplies (`material_group` starts with "OFF") | USD 1,000 | Catalog |
| Professional Services (`material_group` starts with "SVC") | USD 10,000 | Contract + Manager Approval |
| General Procurement (all others) | USD 25,000 | Spot Buy up to threshold; Contract above |

If `total_price` (converted to USD if needed) exceeds the threshold for the category:
- Add a `SPEND_THRESHOLD_BREACH` violation
- Violation: `{ "type": "SPEND_THRESHOLD_BREACH", "field": "total_price", "message": "Total spend of <amount> <currency> exceeds the <category> threshold of USD <limit>. Manager approval required.", "policy_source": "PR Policy §4.2 – Spend Thresholds" }`

## Step 5: Approved Supplier Check

Use the result from `validate_supplier`:
- If `approved == false` or supplier not found → add an `UNAPPROVED_SUPPLIER` violation
- Violation: `{ "type": "UNAPPROVED_SUPPLIER", "field": "supplier_name", "message": "Supplier '<name>' is not in the approved supplier list. Procurement manager approval required.", "policy_source": "PR Policy §5.1 – Approved Supplier Program" }`
- If `qualification_status` is not "Qualified" or "Active" → also add this violation

## Step 6: Category Routing Check

Use the `material_group` and the lookup from `lookup_procurement_master_data` to verify the purchasing group assignment:
- If the material group does not map to a valid purchasing group → add a `CATEGORY_ROUTING_MISMATCH` violation
- Violation: `{ "type": "CATEGORY_ROUTING_MISMATCH", "field": "material_group", "message": "Material group '<mg>' does not map to a valid purchasing group in master data.", "policy_source": "PR Policy §6.1 – Category Management" }`

## Step 7: Quote Validity Check

If `quote_validity_date` is available:
- If the quote has expired (validity date < today) → add a warning (not a hard violation):
  `{ "type": "WARNING", "field": "quote_validity_date", "message": "Supplier quotation may have expired on <date>. Confirm quote is still valid.", "policy_source": "PR Policy §3.2 – Quote Currency" }`

## Output Format

Return a JSON object:
```json
{
  "valid": true | false,
  "violations": [
    {
      "type": "VIOLATION_TYPE",
      "field": "field_name",
      "message": "Human-readable message",
      "policy_source": "Policy reference"
    }
  ],
  "warnings": [
    {
      "type": "WARNING",
      "field": "field_name",
      "message": "Human-readable message",
      "policy_source": "Policy reference"
    }
  ]
}
```

`valid` is `true` only when `violations` is empty. Warnings do not affect validity.

## Exception Routing Decision Table

| Violation Type | Route To | Urgency |
|----------------|----------|---------|
| `UNAPPROVED_SUPPLIER` | Procurement Manager | High |
| `SPEND_THRESHOLD_BREACH` | Procurement Manager | High |
| `MISSING_REQUIRED_FIELD` | Requestor (ask for field) | Normal |
| `INVALID_FORMAT` | Requestor (ask to correct) | Normal |
| `MISSING_ATTACHMENT` | Requestor (ask for PDF) | Normal |
| `CATEGORY_ROUTING_MISMATCH` | Procurement Manager | Medium |

If any High-urgency violation exists, route the entire PR to the procurement manager — do not ask the requestor to fix other issues first.
