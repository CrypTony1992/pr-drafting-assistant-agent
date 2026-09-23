---
name: pr-draft
description: Instructions for assembling a final purchase requisition draft with procurement channel recommendation, policy justification, and complete decision trace. Requires explicit requestor confirmation before submission.
---

# PR Draft Assembly Skill

Use this skill when assembling the final purchase requisition draft after all fields have been validated and all policy checks have passed.

## When to Use This Skill

Load this skill before calling the `assemble_pr_draft` tool. Only invoke this skill after:
1. All required fields have been collected (no nulls remaining)
2. `validate_supplier` has returned `approved: true`
3. `lookup_procurement_master_data` has resolved all master data fields
4. `validate_pr_policy` has returned `valid: true`

## Step 1: Merge All Fields

Merge fields from all sources into a single PR record:
- Fields extracted from the quotation PDF (via `extract_pr_from_pdf`)
- Fields provided by the requestor during gap-filling dialogue
- Fields resolved from SAP master data (via `lookup_procurement_master_data`)
- Supplier validation result (via `validate_supplier`)

Final merged record must include ALL required fields from the policy-validation skill.

## Step 2: Determine Procurement Channel

Based on the `material_group` and `total_price`, recommend one of three procurement channels:

| Condition | Channel | Description |
|-----------|---------|-------------|
| Item available in catalog AND total_price ≤ catalog threshold | **Catalog Purchase** | Order from company's approved e-catalog |
| Approved supplier AND total_price ≤ spot-buy threshold | **Spot Buy** | Direct purchase from approved supplier |
| total_price > contract threshold OR strategic category | **Contract Purchase** | Must reference an existing contract; escalate if none exists |

Thresholds (USD equivalent):
- Catalog threshold: USD 1,000
- Spot-buy threshold: USD 25,000
- Contract threshold: USD 25,000

## Step 3: Build Policy Justification

For each recommendation, provide:
- The rule that was applied (e.g., "Spend < USD 25,000 with approved supplier → Spot Buy eligible")
- The policy reference (e.g., "PR Policy §4.1 – Procurement Channel Selection")
- The supplier's qualification status

## Step 4: Build Decision Trace

The decision trace must document every step:

```
DECISION TRACE
==============
1. PDF Extraction
   - Fields extracted: [list]
   - Fields requiring requestor input: [list]
   - Extraction confidence: [level]

2. Gap-Filling
   - Fields collected from requestor: [list with values]

3. Master Data Resolution
   - Cost center [code]: resolved ✓
   - GL account [number]: resolved ✓
   - Material group [code]: resolved ✓

4. Supplier Validation
   - Supplier: [name]
   - Status: Approved ✓ / Not Approved ✗
   - Qualification: [status]

5. Policy Validation
   - Completeness: Pass ✓
   - Format checks: Pass ✓
   - Attachment: Present ✓
   - Spend threshold: [amount] vs [limit] → Pass ✓
   - Approved supplier: Pass ✓
   - Category routing: Pass ✓

6. Channel Recommendation
   - Recommended: [channel]
   - Justification: [rule applied]
   - Policy source: [reference]
```

## Step 5: Format the PR Summary for Requestor Confirmation

Present the draft in a clear, human-readable format:

```
PURCHASE REQUISITION DRAFT
==========================
Requestor: [name / derived from context]
Date: [today]

SUPPLIER INFORMATION
Supplier Name: [name]
Supplier ID: [id if available]
Quote Reference: [ref]
Quote Validity: [date]

LINE ITEMS
----------------------------------------------------------
# | Description         | Qty | Unit | Unit Price | Total
----------------------------------------------------------
1 | [item_description]  | [q] | [u]  | [price]    | [total]
----------------------------------------------------------
                                        TOTAL: [sum] [currency]

ACCOUNTING
Cost Center: [code]
GL Account: [number]
Material Group: [code]

LOGISTICS
Delivery Date: [date]
Payment Terms: [terms]

PROCUREMENT RECOMMENDATION
Channel: [Catalog / Spot Buy / Contract Purchase]
Justification: [policy rule]
Policy Reference: [source]

⚠️  WARNINGS (if any): [list warnings]

POLICY STATUS: ✅ ALL CHECKS PASSED

Please review the above purchase requisition draft.
Type CONFIRM to submit to SAP S/4HANA, or describe any corrections needed.
```

## Step 6: Await Explicit Confirmation

**CRITICAL**: After presenting the draft, the agent MUST:
1. Stop and wait for the requestor's explicit response
2. Only proceed to `submit_purchase_requisition` if the requestor types "CONFIRM" or clearly confirms
3. If the requestor requests corrections: update the draft and re-present it (return to Step 1 with corrections applied)
4. NEVER auto-submit or infer confirmation from silence or ambiguous responses

## Output Format

Return a JSON object:
```json
{
  "pr_draft": {
    "supplier_name": "string",
    "supplier_id": "string or null",
    "quote_reference": "string or null",
    "items": [...],
    "total_price": number,
    "currency": "string",
    "cost_center": "string",
    "gl_account": "string",
    "material_group": "string",
    "delivery_date": "YYYY-MM-DD",
    "payment_terms": "string"
  },
  "channel_recommendation": "catalog | spot_buy | contract",
  "policy_justification": "string",
  "policy_source": "string",
  "decision_trace": "string (formatted markdown)",
  "human_readable_summary": "string (formatted for display to requestor)",
  "awaiting_confirmation": true
}
```
