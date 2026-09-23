# Purchase Requisition Drafting Assistant

AI-powered PR drafting agent integrated with SAP Ariba and SAP S/4HANA.

## Business challenge

Requestors struggle to create accurate purchase requisitions, leading to high rates of policy violations, missing fields, and buyer corrections. An AI agent is needed that extracts all required PR fields from supplier quotation PDFs and user input, validates completeness and policy compliance, drafts a fully formed PR with procurement channel recommendation, and routes exceptions to the procurement manager — so requestors complete accurate requests in minutes and buyers receive compliant PRs from the start.

## Business Goals & Success Criteria

| Metric | Baseline | Target | Timeline | Process / Capability | Source |
|--------|----------|--------|----------|----------------------|--------|
| Policy-compliant PRs at first submission | — | 99% | — | Purchase Requirements Processing / Self-Service Requisitioning | user |
| Manual rework from incorrect PRs | — | Significant reduction | — | Self-Service Requisitioning / Guided Buying | user |

## Key Milestones

1. **Quotation Ingestion** — Requestor uploads a supplier quotation PDF and the agent successfully extracts all required PR fields.
2. **Policy Validation** — Agent validates extracted data against field completeness rules, spend thresholds, approved supplier list, and category routing rules.
3. **PR Draft Presented** — Agent presents a fully drafted PR with procurement channel recommendation and policy justification; requestor confirms or corrects.
4. **Exception Routing** — If a policy exception is detected (unapproved supplier, spend limit breach), the exception is flagged and routed to the procurement manager.
5. **PR Submitted to Ariba** — Confirmed, validated PR is submitted to SAP Ariba for processing.

## Business Architecture (RBA)

### End-to-End Process

Source to Pay for Indirect Products and Services

### Process Hierarchy

```
Source to Pay for Indirect Products and Services
└── Manage Suppliers and Collaboration (indirect)
    └── Manage suppliers and networked collaboration (indirect)
        └── Manage supplier information
└── Procure to Receipt (indirect)
    └── Purchase products and services (indirect)
        └── Manage purchasing requisitions
```

### Summary

The PR drafting assistant maps to the Source to Pay E2E process, spanning supplier validation (approved supplier status, supplier data management) and purchase requisition management (self-service requisitioning, guided buying, policy enforcement, and exception routing).

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | MCP Server Version | Gap? | Notes / assumptions |
|------------------------|-------------------------|------------|-------------------|--------------------|------|---------------------|
| Create and submit purchase requisition in S/4HANA | SAP S/4HANA Cloud — Purchase Requirements Processing, Self-Service Requisitioning | `sap.s4:apiResource:API_PURCHASEREQ_PROCESS_SRV:v1` | — | — | No | OData API available; no MCP server found — agent calls API directly |
| Validate approved supplier status | SAP Ariba SLP — Supplier Data Management, Supplier Qualification | `sap.aribas4:apiResource:supplierdatapagination:v4` | — | — | No | Supplier data API available |
| Retrieve procurement master data (cost center, GL, category) | SAP Ariba — Master Data Retrieval API | `sap.aribabuyer:apiResource:mds_search:v1` | — | — | No | REST API available |
| Extract PR fields from supplier quotation PDF | None (standard SAP) | — | — | — | **Yes** | Requires custom AI/LLM extraction layer in the agent |
| Enforce spend thresholds and category routing policy | None (standard SAP UI rule engine exposed to agent) | — | — | — | **Yes** | Policy rules must be configured and consumed by the agent |
| Route exceptions to procurement manager | SAP Ariba workflow / notification | — | — | — | Maybe | Standard Ariba approval workflows exist; agent must trigger them via API |

### Key findings

- SAP S/4HANA OData APIs fully cover PR creation and submission; no MCP server layer is available, so the agent must call these APIs directly.
- Supplier validation data is accessible via SAP Ariba Supplier Data API; approved supplier checks can be performed at runtime.
- The core gap is AI-driven PDF extraction and policy rule enforcement — both require custom agent logic.
- SAP Ariba Guided Buying and Self-Service Requisitioning handle the standard UI flow; the agent augments this by pre-filling and validating before submission.
- Exception routing can leverage standard Ariba approval workflows, triggered by the agent via API calls.
- No MCP servers were found for any of the relevant APIs; the agent will use direct OData/REST calls.

## Recommendations

### AI Agent for PR Drafting and Policy Compliance

#### Executive Summary

Python AI agent that drafts compliant PRs from quotation PDFs and enforces procurement policy end-to-end.

#### Recommended Solution

A pro-code Python AI agent (A2A protocol) that: (1) accepts a supplier quotation PDF and requestor input, (2) uses an LLM to extract all required PR fields, (3) validates fields against SAP Ariba master data and configurable policy rules (spend thresholds, approved supplier list, category routing), (4) presents a fully drafted PR with channel recommendation and policy justification for requestor confirmation, (5) submits the confirmed PR to SAP S/4HANA via OData API, and (6) routes policy exceptions to the procurement manager via SAP Ariba approval workflows.

#### Recommended solution category

AI Agent

#### Intent fit
92%
