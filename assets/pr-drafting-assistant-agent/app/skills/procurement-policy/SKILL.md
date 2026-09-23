---
name: procurement-policy
description: Authoritative machine-readable reference for Vestas procurement policy VWS-PROC-002 v3.1. Covers approval thresholds, required PR fields, supplier qualification, procurement channels, quotation requirements, and prohibited practices.
---

# Vestas Procurement Policy — VWS-PROC-002 v3.1

**Policy Reference:** VWS-PROC-002  
**Version:** 3.1  
**Effective Date:** 1 January 2025  
**Policy Owner:** Chief Procurement Officer, Global Supply Chain  
**Approved By:** Group CFO

---

## §3 Approval Authority Thresholds

All PR values are in EUR. Multi-currency PRs must be converted using the Vestas internal monthly exchange rate published by Group Treasury.

| Tier | Threshold (EUR) | Approving Authority | Turnaround Target |
|------|----------------|---------------------|-------------------|
| Tier 1 | Under €5,000 | Requester (self-approved) | Same business day |
| Tier 2 | €5,000 – €49,999 | Direct Line Manager | 2 business days |
| Tier 3 | €50,000 – €249,999 | Finance Director (business unit) | 3 business days |
| Tier 4 | €250,000 and above | Chief Procurement Officer | 5 business days |

Approval is determined by the **aggregate value** of the entire PR, not individual line items.

**Delegation:** Approvers may delegate in writing during absences of 5+ business days. Delegation must be registered in Ariba before it takes effect. Verbal or email-only delegation is not valid.

---

## §4 Required PR Fields (12 mandatory fields)

Every PR submitted through SAP Ariba must include all 12 of the following fields. A PR with any field missing or invalid will be automatically rejected.

| # | Field | Notes |
|---|-------|-------|
| 1 | `supplier_name` | Must match the Approved Vendor List (§5) |
| 2 | `quote_reference` | Quote number or reference ID from the supplier document |
| 3 | `item_description` | Specific description; "miscellaneous" is not acceptable |
| 4 | `quantity` + `unit` | Numeric value with unit of measure |
| 5 | `unit_price` | Price per unit excluding VAT, in stated currency |
| 6 | `total_price` | Total order value excluding VAT; requester must confirm |
| 7 | `currency` | ISO 4217 code (EUR, DKK, USD, GBP, etc.) |
| 8 | `delivery_date` | Must be a future date, realistic given supplier lead times |
| 9 | `cost_center` | Valid, active Vestas cost centre code |
| 10 | `gl_account` | Correct General Ledger account code |
| 11 | `business_justification` | One clear sentence explaining the business need |
| 12 | `requesting_department` + `contact_name` | Department name and full name of the requester |

---

## §5 Supplier Qualification and Approved Vendor List (AVL)

- PRs may only be raised against suppliers on the **Approved Vendor List (AVL)**, accessible within SAP Ariba.
- New supplier onboarding requires a Supplier Onboarding Request in Ariba at least **15 business days** before the first purchase.
- Procurement may suspend or remove a supplier from the AVL at any time for non-performance, ethics violations, insolvency, or failure to maintain required certifications.

---

## §6 Procurement Channels

| Scenario | Required Channel |
|----------|----------------|
| Standard goods and services (all values) | SAP Ariba — Guided Buying |
| CAPEX projects | CAPEX request via Finance; separate CAPEX PR in Ariba |
| Emergency operational spend (unplanned, production-critical) | Emergency PO → Line Manager verbal approval then Ariba PR same day |
| Pre-approved catalogue items under €5,000 | Ariba Catalogue (self-service) |
| Direct supplier engagement without PR | **Not permitted under any circumstance** |

Emergency purchases must be flagged "EMERGENCY" in the PR title. Emergency status does not waive approval thresholds.

---

## §7 Quotation Requirements

### Number of quotes required (§7.1)

| PR Value | Minimum Quotations |
|----------|-------------------|
| Under €5,000 | 1 quote (verbal or written) |
| €5,000 – €49,999 | 2 written quotes |
| €50,000 and above | 3 written quotes, or documented Single-Source Justification (SSJ) |

All quotations must be **dated within the preceding 90 calendar days**. Quotations older than 90 days are not accepted.

### Single-Source Justification (§7.2)

If fewer than the required number of quotes are available, attach a signed SSJ form. Acceptable grounds: sole-supplier market position, technical compatibility, or documented supplier failure to respond after three attempts.

### Additional attachments required where applicable (§7.3)

- Signed statement of work or service agreement (services over €10,000)
- CAPEX approval form (all capital expenditure)
- Import licence or customs documentation (cross-border physical goods)

---

## §9 Prohibition of Split Purchasing

Split purchasing — dividing a single procurement requirement across multiple PRs to stay below an approval threshold — is **strictly prohibited**.

- Where Procurement or Finance identifies related PRs that together exceed a threshold, they will be consolidated and re-routed to the correct approval level.
- Genuinely recurring purchases must use a blanket/framework purchase order at the full anticipated **annual value**. The annual value determines the approval level.

---

## Approval Routing Logic (for agent use)

Given a PR total in EUR, route as follows:

```
if total_eur < 5000:
    approver = "Requester (self-approved)"
    tier = "Tier 1"
elif total_eur < 50000:
    approver = "Direct Line Manager"
    tier = "Tier 2"
elif total_eur < 250000:
    approver = "Finance Director"
    tier = "Tier 3"
else:
    approver = "Chief Procurement Officer"
    tier = "Tier 4"
```

Always cite policy section **VWS-PROC-002 §3.1** when communicating approval routing to the requestor.

---

## Quotation Age Check (for agent use)

When `quote_reference` is present and a quotation date can be extracted:
- If the quotation date is more than 90 days before today → raise a `WARNING` (not a hard violation)
- Message: "Quotation [ref] is dated more than 90 days ago. Please confirm the quote is still valid or obtain a refreshed quote. (VWS-PROC-002 §7.1)"
