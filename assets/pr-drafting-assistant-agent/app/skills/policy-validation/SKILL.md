---
name: policy-validation
description: Step-by-step instructions for validating PR fields against procurement policy — completeness, format, attachments, spend thresholds, approved supplier status, and category routing rules.
---

# Policy Validation Skill

Use this skill when validating a purchase requisition draft against procurement policy before presenting it to the requestor or submitting it to SAP S/4HANA.

## When to Use This Skill

Load this skill whenever the agent needs to perform policy validation on a complete (or nearly complete) set of PR fields. All checks must be run in order. Do not stop at the first violation — collect ALL violations before returning results.

## Required PR Fields

The following **12 fields** are REQUIRED for a valid PR (VWS-PROC-002 §4.1). Absence of any field is a `MISSING_REQUIRED_FIELD` violation:

| Field | Description |
|-------|-------------|
| `item_description` | Specific description of what is being purchased; "miscellaneous" is not acceptable |
| `quantity` | Numeric quantity with unit of measure |
| `unit_price` | Price per unit excluding VAT, in stated currency |
| `currency` | ISO 4217 currency code (EUR, DKK, USD, GBP, etc.) |
| `supplier_name` | Name matching the Approved Vendor List (AVL) |
| `quote_reference` | Quote number or reference ID from the supplier document |
| `delivery_date` | Requested delivery date (ISO 8601 format: YYYY-MM-DD); must be a future date |
| `cost_center` | Valid, active Vestas cost centre code |
| `gl_account` | Correct General Ledger account code |
| `total_price` | Total order value excluding VAT (quantity × unit_price; numeric) |
| `business_justification` | One clear sentence explaining the business need |
| `requesting_department` | Department name and full name of the requester |

## Step 1: Completeness Check

For each required field listed above:
- If the field is null, empty, or missing → add a `MISSING_REQUIRED_FIELD` violation
- Violation format: `{ "type": "MISSING_REQUIRED_FIELD", "field": "<field_name>", "message": "Required field '<field_name>' is missing", "policy_source": "VWS-PROC-002 §4.1 – Mandatory PR Fields" }`

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

Violation format: `{ "type": "INVALID_FORMAT", "field": "<field_name>", "message": "<description of format error>", "policy_source": "VWS-PROC-002 §4.1 – Data Formats" }`

## Step 3: Attachment Check

- If no supplier quotation PDF has been provided → add a `MISSING_ATTACHMENT` violation
- Violation: `{ "type": "MISSING_ATTACHMENT", "field": "quotation_pdf", "message": "Supplier quotation PDF is required for all purchase requisitions", "policy_source": "VWS-PROC-002 §7.1 – Quotation Requirements" }`

## Step 4: Approval Tier Routing

Apply the Vestas approval thresholds in EUR (VWS-PROC-002 §3.1). All multi-currency PRs must be converted to EUR using the Vestas internal monthly exchange rate.

| Tier | Threshold (EUR) | Approving Authority | Turnaround |
|------|----------------|---------------------|------------|
| Tier 1 | Under €5,000 | Requester (self-approved) | Same business day |
| Tier 2 | €5,000 – €49,999 | Direct Line Manager | 2 business days |
| Tier 3 | €50,000 – €249,999 | Finance Director (business unit) | 3 business days |
| Tier 4 | €250,000 and above | Chief Procurement Officer | 5 business days |

This is **routing information**, not a violation. Always include the resolved tier and approver in the validation result so the agent can communicate it clearly to the requestor.

## Step 5: Approved Supplier Check

Use the result from `validate_supplier`:
- If `approved == false` or supplier not found → add an `UNAPPROVED_SUPPLIER` violation
- Violation: `{ "type": "UNAPPROVED_SUPPLIER", "field": "supplier_name", "message": "Supplier '<name>' is not in the approved supplier list. Procurement manager approval required.", "policy_source": "VWS-PROC-002 §5.1 – Approved Vendor List" }`
- If `qualification_status` is not "Qualified" or "Active" → also add this violation

## Step 6: Category Routing Check

Use the `material_group` and the lookup from `lookup_procurement_master_data` to verify the purchasing group assignment:
- If the material group does not map to a valid purchasing group → add a `CATEGORY_ROUTING_MISMATCH` violation
- Violation: `{ "type": "CATEGORY_ROUTING_MISMATCH", "field": "material_group", "message": "Material group '<mg>' does not map to a valid purchasing group in master data.", "policy_source": "VWS-PROC-002 §6 – Procurement Channels" }`

## Step 7: Quote Validity Check

If `quote_validity_date` is available:
- If the quote has expired (validity date < today) → add a warning (not a hard violation):
  `{ "type": "WARNING", "field": "quote_validity_date", "message": "Supplier quotation may have expired on <date>. Confirm quote is still valid.", "policy_source": "VWS-PROC-002 §7.1 – Quotation Requirements" }`

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
