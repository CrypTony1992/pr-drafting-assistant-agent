# Product Requirements Document (PRD)

**Title:** Purchase Requisition Drafting Assistant
**Date:** 2026-09-21
**Owner:** Procurement Business Owner
**Solution Category:** AI Agent

---

## Product Purpose & Value Proposition

**Elevator Pitch:**
Requestors waste days completing purchase requisitions that buyers reject for policy violations or missing fields. This AI agent extracts all required PR data from supplier quotation PDFs, validates it against procurement policy, and delivers a fully drafted, compliant PR in minutes — with exceptions flagged and routed automatically.

**Business Need:**
Manual PR creation is error-prone. Requestors lack visibility into spend thresholds, approved supplier lists, and category routing rules, leading to non-compliant submissions that buyers must correct or reject. This creates rework on both sides and delays procurement cycles.

**Expected Value:**
- 99% policy-compliant PRs at first submission (up from current state with manual entry)
- Significant reduction in buyer time spent correcting incomplete or non-compliant PRs
- Procurement managers receive routed exception cases with full context, reducing investigation time

**Product Objectives (Prioritized):**
1. Achieve 99% policy-compliant PR submissions at first pass
2. Eliminate manual field extraction effort for requestors by parsing supplier quotation PDFs automatically
3. Ensure every exception (unapproved supplier, spend limit breach) is detected and routed with full context

---

## Business Metrics

| Metric | Baseline | Target | Timeline | Process / Capability | Source |
|--------|----------|--------|----------|----------------------|--------|
| Policy-compliant PRs at first submission | — | 99% | — | Purchase Requirements Processing / Self-Service Requisitioning | user |
| Manual rework from incorrect PRs | — | Significant reduction | — | Self-Service Requisitioning / Guided Buying | user |

---

## Requirements

### Must-Have Requirements

**REQ-01**: Supplier Quotation PDF Extraction

- **Problem to Solve**: Requestors manually re-type data from supplier quotation PDFs into the PR form, introducing errors and wasting time.
- **User Story**: As a requestor, I need the agent to extract all required PR fields from a supplier quotation PDF I upload, so that I do not have to re-enter data manually.
- **Acceptance Criteria**:
  - Given a supplier quotation PDF is uploaded, when the agent processes it, then all standard PR fields (item description, quantity, unit price, currency, supplier name, delivery date, payment terms) are extracted and presented for review.
  - Given an unreadable or incomplete PDF, when extraction fails for a field, then the agent asks the requestor for the missing value — one field at a time.
- **Maps to Objective**: Objective 2
- **Priority Rank**: 1

**REQ-02**: Policy Validation

- **Problem to Solve**: Requestors do not know procurement policy rules (spend thresholds, approved supplier list, category routing), leading to non-compliant PRs.
- **User Story**: As a requestor, I need the agent to validate my PR data against current procurement policy before submission, so that I am informed of any violations before the PR reaches a buyer.
- **Acceptance Criteria**:
  - Given extracted PR fields, when the agent validates, then it checks: field completeness, field format, attachment presence, quote validity, spend thresholds, approved supplier status, and category routing rules.
  - Given all fields pass validation, when validation is complete, then the agent proceeds to draft the PR.
  - Given a policy violation is detected, when validation is complete, then the agent flags the specific violation with a clear explanation and the applicable policy rule source.
- **Maps to Objective**: Objective 1
- **Priority Rank**: 2

**REQ-03**: PR Draft Presentation with Procurement Channel Recommendation

- **Problem to Solve**: Requestors do not know which procurement channel to use or how to justify their purchasing decision.
- **User Story**: As a requestor, I need the agent to present a fully drafted PR with a procurement channel recommendation and policy justification, so that I can review and confirm before submission.
- **Acceptance Criteria**:
  - Given validated PR data, when the PR draft is presented, then it includes: all PR fields, recommended procurement channel (e.g., catalog, spot-buy, contract), policy justification with source reference, and a complete decision trace.
  - Given the draft is presented, when the requestor reviews it, then explicit confirmation is required before the agent proceeds to submit.
  - Given the requestor requests changes, when they provide corrections, then the agent updates the draft and re-presents for confirmation.
- **Maps to Objective**: Objectives 1 & 2
- **Priority Rank**: 3

**REQ-04**: Exception Detection and Procurement Manager Routing

- **Problem to Solve**: Policy exceptions (unapproved suppliers, spend limit breaches) currently pass through undetected or are caught late by buyers.
- **User Story**: As a procurement manager, I need to receive a routed exception notification with full context when a PR violates policy, so that I can review and approve or reject the exception efficiently.
- **Acceptance Criteria**:
  - Given an unapproved supplier is detected, when the agent flags the exception, then the PR is not submitted to Ariba and the exception is routed to the procurement manager with: supplier name, reason for non-approval, requested item, and requestor identity.
  - Given a spend threshold breach is detected, when the agent flags the exception, then the routing includes: spend amount, applicable threshold, category, and requestor details.
  - Given any policy exception, when routed, then the requestor is notified that their request is pending manager review.
- **Maps to Objective**: Objective 3
- **Priority Rank**: 4

**REQ-05**: Ariba Submission of Confirmed PR

- **Problem to Solve**: After confirmation, requestors still have to manually enter the PR into SAP Ariba, duplicating effort.
- **User Story**: As a requestor, I need the confirmed PR to be submitted automatically to SAP Ariba, so that I do not have to re-enter data into the system.
- **Acceptance Criteria**:
  - Given the requestor confirms the PR draft, when the agent submits, then the PR is created in SAP S/4HANA and/or SAP Ariba via OData API with all required fields populated.
  - Given a submission failure, when the API returns an error, then the agent notifies the requestor with the error details and retains the draft for manual follow-up.
- **Maps to Objective**: Objective 2
- **Priority Rank**: 5

**REQ-06**: Gap-Filling Dialogue for Missing Information

- **Problem to Solve**: Not all required PR fields can be extracted from the quotation PDF; some must come from the requestor.
- **User Story**: As a requestor, I need the agent to ask me for missing information one gap at a time, so that the process is clear and I am never overwhelmed.
- **Acceptance Criteria**:
  - Given a required field cannot be extracted from the PDF, when the agent detects the gap, then it asks the requestor for that single field before proceeding.
  - Given the requestor provides the missing value, when it is supplied, then the agent continues extraction and validation without repeating already-answered questions.
  - The agent must never invent or default business data (e.g., cost center, GL account, supplier ID).
- **Maps to Objective**: Objectives 1 & 2
- **Priority Rank**: 6

---

## Solution Architecture

**Architecture Overview:**
A pro-code Python AI agent (A2A protocol) deployed on SAP BTP. The agent receives requestor inputs and PDF uploads, uses an LLM for extraction and reasoning, calls SAP Ariba and SAP S/4HANA APIs for validation and submission, and applies a configurable policy rule set for compliance checks.

**Key Components:**

- **PR Drafting Agent**: Python A2A agent — orchestrates extraction, validation, drafting, confirmation, and submission.
- **LLM / Extraction Engine**: GPT-4o via SAP Generative AI Hub — parses PDF content, fills PR fields, reasons over policy rules.
- **SAP S/4HANA OData API**: Purchase Requisition API (`API_PURCHASEREQ_PROCESS_SRV`) — creates and submits the confirmed PR.
- **SAP Ariba Supplier Data API**: Supplier Data API with Pagination (`supplierdatapagination`) — validates approved supplier status.
- **SAP Ariba Master Data API**: Master Data Retrieval API (`mds_search`) — retrieves cost centers, GL accounts, categories.
- **Policy Rule Store**: Configurable rule set (spend thresholds, approved supplier list, category routing rules) consumed by the agent at validation time.
- **Exception Notification**: SAP Ariba approval workflow or email notification — routes flagged exceptions to procurement manager.

**Integration Points:**

- SAP S/4HANA Cloud: PR creation via OData (write), read-only master data retrieval
- SAP Ariba: Supplier status check (read), master data lookup (read), exception routing (write/notify)
- SAP Generative AI Hub: LLM inference for PDF extraction and reasoning

---

## Automation & Agent Behaviour

**Automation Level:** Autonomous agent with human-in-the-loop confirmation gate

**Actions the system performs without human approval:**
- Extract PR fields from uploaded PDF
- Validate fields against policy rules and SAP master data
- Detect policy violations and classify exception type
- Generate PR draft with procurement channel recommendation and decision trace

**Actions that require human review or approval:**
- Final PR submission to SAP Ariba (requires explicit requestor confirmation)
- Policy exception resolution (requires procurement manager approval)

**Model or engine used:** GPT-4o via SAP Generative AI Hub

**Knowledge & data sources accessed:**
- Supplier quotation PDF (uploaded by requestor)
- SAP Ariba supplier master data (approved supplier status)
- SAP Ariba procurement master data (cost centers, GL accounts, categories)
- Policy rule store (spend thresholds, category routing, approval limits)

**Tools or connectors invoked:**
- `API_PURCHASEREQ_PROCESS_SRV` (SAP S/4HANA OData): create purchase requisition — write
- `supplierdatapagination` (SAP Ariba REST): validate approved supplier status — read-only
- `mds_search` (SAP Ariba REST): retrieve procurement master data — read-only
- SAP Ariba exception routing / notification: trigger manager review workflow — write

**Guardrails & fail-safes:**
- The agent must never invent or default any business data field (cost center, GL account, supplier ID, price)
- If a required field cannot be extracted and the requestor does not supply it, the agent must halt and explain — never proceed with incomplete data
- All policy exceptions must be routed to the procurement manager; the agent must never bypass or auto-approve exceptions
- If the SAP API submission fails, the agent retains the confirmed draft and notifies the requestor — no silent failures
- Confidence below threshold on PDF extraction routes to a gap-filling dialogue, not a silent default

---

## Agent Extensibility & Instrumentation

**Agent Extensibility:**
- The agent is designed with extension points to support future capabilities without core changes
- Extensible policy rule store: new spend thresholds, supplier lists, and category routing rules can be added without code changes
- Additional data sources (e.g., contract compliance, budget availability checks) can be integrated as new tools
- Exception routing logic can be extended to support additional escalation paths (e.g., CFO approval for high-value PRs)

**Business Step Instrumentation:**
All key business steps emit structured log statements following the pattern `[MILESTONE_ID].[achieved|missed]: [description]` to support OpenTelemetry observability in production.

---

## Milestones

### M1: Quotation Ingestion

- **Description**: Requestor uploads a supplier quotation PDF and the agent successfully extracts all required PR fields.
- **Achieved when**: All standard PR fields are extracted from the PDF (with or without requestor gap-filling) and are ready for validation.
- **Log on achievement**: `M1.achieved: supplier quotation PDF processed, all PR fields extracted`
- **Log on miss**: `M1.missed: PDF extraction incomplete or document unreadable after requestor gap-filling`

### M2: Policy Validation

- **Description**: Agent validates all extracted PR fields against completeness rules, spend thresholds, approved supplier status, and category routing rules.
- **Achieved when**: All validation checks pass with no policy violations detected.
- **Log on achievement**: `M2.achieved: all PR fields validated, no policy violations detected`
- **Log on miss**: `M2.missed: policy validation failed — [violation type] detected`

### M3: PR Draft Presented

- **Description**: Agent presents a fully drafted PR with procurement channel recommendation and policy justification to the requestor for confirmation.
- **Achieved when**: The requestor receives and reviews the PR draft with decision trace.
- **Log on achievement**: `M3.achieved: PR draft presented to requestor with channel recommendation`
- **Log on miss**: `M3.missed: PR draft could not be generated — [reason]`

### M4: Exception Routed

- **Description**: A policy exception is detected and routed to the procurement manager with full context.
- **Achieved when**: The exception notification is delivered to the procurement manager and the requestor is informed of the pending review.
- **Log on achievement**: `M4.achieved: policy exception routed to procurement manager — [exception type]`
- **Log on miss**: `M4.missed: exception routing failed — [reason]`

### M5: PR Submitted to Ariba

- **Description**: Confirmed, validated PR is submitted to SAP Ariba / SAP S/4HANA via API.
- **Achieved when**: The PR is successfully created in the system and a PR number is returned.
- **Log on achievement**: `M5.achieved: PR submitted successfully — PR number [id]`
- **Log on miss**: `M5.missed: PR submission failed — [api error or reason]`
