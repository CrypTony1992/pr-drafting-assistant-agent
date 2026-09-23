# Specification: pr-drafting-assistant-agent

> **Guidelines**: Read all applicable guidelines before executing ANY tasks below:
> - [guidelines.md](../guidelines.md) — Universal execution rules
> - [guidelines-agent.md](../guidelines-agent.md) — Universal agent patterns
> - [guidelines-agent-python.md](../guidelines-agent-python.md) — Python implementation details
> - [guidelines-agent-skills.md](../guidelines-agent-skills.md) — Runtime skills patterns
> - [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) — MCP integration patterns

---

## Basic Setup

- [ ] Read `product-requirements-document.md` and `intent.md` thoroughly before starting
- [ ] Bootstrap agent code in `assets/pr-drafting-assistant-agent/` using the sap-agent-bootstrap instructions (invoke from inside `assets/pr-drafting-assistant-agent/`, use copy commands — do NOT create files manually)
- [ ] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

---

## Runtime Skills

- [ ] Create `assets/pr-drafting-assistant-agent/app/skills/policy-validation/SKILL.md` — step-by-step instructions for the agent to validate PR fields against procurement policy:
  - Completeness check: all required PR fields present (item description, quantity, unit price, currency, supplier name, delivery date, payment terms, cost center, GL account, material group)
  - Format check: numeric fields are numeric, dates are valid, currency codes are valid
  - Attachment check: supplier quotation PDF is attached
  - Spend threshold check: total line value does not exceed configured thresholds per category
  - Approved supplier check: supplier name/ID exists in the SAP Ariba approved supplier list
  - Category routing check: material group maps to the correct purchasing group and org
  - Exception detection: classify exception type (unapproved supplier / spend breach / missing attachment)
- [ ] Create `assets/pr-drafting-assistant-agent/app/skills/pr-extraction/SKILL.md` — step-by-step LLM prompt instructions for extracting PR fields from a supplier quotation PDF:
  - Fields to extract: supplier name, item description(s), quantity, unit price, currency, total price, delivery date, payment terms, validity date of quote
  - Return extracted fields as structured JSON
  - For each field that cannot be confidently extracted, return a null with the field name so the gap-filling dialogue can be triggered
- [ ] Create `assets/pr-drafting-assistant-agent/app/skills/pr-draft/SKILL.md` — instructions for assembling the final PR draft:
  - Merge extracted fields with requestor-supplied fields
  - Recommend procurement channel based on spend value and category (catalog / spot-buy / contract)
  - Provide policy justification and source reference for the recommendation
  - Format the full decision trace (fields extracted → validation results → channel recommendation → any flags)
  - Require explicit requestor confirmation before proceeding

---

## Project-Specific Tasks

## PDF Extraction Tool

- [ ] Implement `extract_pr_from_pdf` tool in `assets/pr-drafting-assistant-agent/app/tools/extract_pr_from_pdf.py`:
  - Accept base64-encoded PDF content or file path as input
  - Use LLM (via SAP Generative AI Hub) with the `pr-extraction` runtime skill to parse the PDF and extract PR fields
  - Return structured JSON with extracted fields and a list of missing/unextractable fields
  - Do NOT invent or default any field value — return null for fields that cannot be extracted

## Gap-Filling Dialogue Tool

- [ ] Implement `request_missing_field` tool in `assets/pr-drafting-assistant-agent/app/tools/request_missing_field.py`:
  - Accept a field name and optional context as input
  - Return a natural language question asking the requestor for the specific missing field
  - Ask one field at a time — never batch multiple missing fields in one question
  - Never invent or suggest a default value

## Supplier Validation Tool (MCP Path B)

- [ ] Implement `validate_supplier` tool in `assets/pr-drafting-assistant-agent/app/tools/validate_supplier.py`:
  - Call the SAP Ariba Supplier Data API (`sap.aribas4:apiResource:supplierdatapagination:v4`) via MCP to check if the supplier is in the approved supplier list
  - Use the vendor `getVendors` / `getVendorExt` operations filtered by supplier name or ERP vendor ID
  - Return: `{ "approved": bool, "supplier_id": str|null, "qualification_status": str|null }`
  - If supplier is not found or not qualified, mark as unapproved for exception routing

## Master Data Lookup Tool (MCP Path B)

- [ ] Implement `lookup_procurement_master_data` tool in `assets/pr-drafting-assistant-agent/app/tools/lookup_procurement_master_data.py`:
  - Call the SAP Ariba Master Data Retrieval API (`sap.aribabuyer:apiResource:mds_search:v1`) via MCP
  - Support lookups for: cost centers, GL accounts, material groups, purchasing groups, purchasing organizations
  - Accept entity name and filter criteria as inputs
  - Return matching records or an empty list if not found

## Policy Validation Tool

- [ ] Implement `validate_pr_policy` tool in `assets/pr-drafting-assistant-agent/app/tools/validate_pr_policy.py`:
  - Load the `policy-validation` runtime skill
  - Run all validation checks using extracted PR fields and results from `validate_supplier` and `lookup_procurement_master_data`
  - Return: `{ "valid": bool, "violations": [ { "type": str, "field": str, "message": str, "policy_source": str } ], "warnings": [] }`
  - Violation types: `UNAPPROVED_SUPPLIER`, `SPEND_THRESHOLD_BREACH`, `MISSING_REQUIRED_FIELD`, `INVALID_FORMAT`, `MISSING_ATTACHMENT`, `CATEGORY_ROUTING_MISMATCH`

## PR Draft Assembly Tool

- [ ] Implement `assemble_pr_draft` tool in `assets/pr-drafting-assistant-agent/app/tools/assemble_pr_draft.py`:
  - Load the `pr-draft` runtime skill
  - Accept all validated PR fields as input
  - Generate full PR draft including: all fields, procurement channel recommendation (catalog/spot-buy/contract), policy justification with source reference, complete decision trace
  - Return structured PR draft as JSON and a formatted human-readable summary for requestor confirmation

## Purchase Requisition Submission Tool (MCP Path B)

- [ ] Implement `submit_purchase_requisition` tool in `assets/pr-drafting-assistant-agent/app/tools/submit_purchase_requisition.py`:
  - Call the SAP S/4HANA Purchase Requisition OData API (`sap.s4:apiResource:API_PURCHASEREQ_PROCESS_SRV:v1`) via MCP
  - Use the `A_PurchaseRequisitionHeader` entity set (POST) to create the PR with nested items and account assignments
  - Map all validated PR fields to the correct OData properties (see `api-specs/purchase-requisition.edmx`)
  - Return: `{ "success": bool, "pr_number": str|null, "error": str|null }`
  - On failure: return the error verbatim, do not retry automatically

## Exception Routing Tool

- [ ] Implement `route_exception_to_manager` tool in `assets/pr-drafting-assistant-agent/app/tools/route_exception_to_manager.py`:
  - Accept exception type, PR draft, requestor identity, and violation details as input
  - Notify the procurement manager via SAP Ariba approval workflow or configurable notification channel
  - Notify the requestor that their request is pending manager review
  - Return: `{ "routed": bool, "routing_reference": str|null }`
  - The agent must NEVER bypass or auto-approve exceptions — routing is mandatory for all policy violations

## Agent Orchestration

- [ ] Implement the main agent prompt in `assets/pr-drafting-assistant-agent/app/agent.py`:
  - System prompt must instruct the agent to follow this flow:
    1. Accept PDF upload and requestor buying need description
    2. Call `extract_pr_from_pdf` to extract PR fields
    3. For each null/missing field, call `request_missing_field` and wait for requestor response — one field at a time
    4. Call `validate_supplier` and `lookup_procurement_master_data` for master data verification
    5. Call `validate_pr_policy` with all fields and master data results
    6. If policy violations exist: call `route_exception_to_manager`, inform requestor, stop
    7. If validation passes: call `assemble_pr_draft` and present draft to requestor for confirmation
    8. Wait for explicit requestor confirmation before proceeding (never auto-submit)
    9. On confirmation: call `submit_purchase_requisition`
    10. Return PR number and confirmation to requestor
  - Guardrail: the agent must NEVER invent, default, or assume any business data field
  - Guardrail: the agent must NEVER submit a PR without explicit requestor confirmation
  - Guardrail: the agent must NEVER bypass exception routing for policy violations

## MCP Translation Files

- [ ] Invoke the `mcp-translation-file` skill for each downloaded API spec in `api-specs/`:
  - `purchase-requisition.edmx` → ORD ID: `sap.s4:apiResource:API_PURCHASEREQ_PROCESS_SRV:v1`, type: `edmx`
  - After generating translation files, invoke `setup-solution` to register the MCP assets in `solution.yaml` and `asset.yaml`
- [ ] For the Ariba Supplier Data API and Master Data API (no spec files downloaded — these are REST APIs accessed via MCP path B):
  - Add them to `asset.yaml` under `requires` using their ORD IDs: `sap.aribas4:apiResource:supplierdatapagination:v4` and `sap.aribabuyer:apiResource:mds_search:v1`

## Mock Configuration

- [ ] Generate `mcp-mock.json` using the `mcp-mock-config` skill after MCP translation files are generated
  - Include mock responses for: PR creation success/failure, supplier approved/unapproved, master data lookup results, exception routing confirmation

---

## Business Instrumentation

- [ ] Implement business step instrumentation for all 5 milestones from the PRD:
  - `M1`: `[M1.achieved]: supplier quotation PDF processed, all PR fields extracted` / `[M1.missed]: PDF extraction incomplete`
  - `M2`: `[M2.achieved]: all PR fields validated, no policy violations detected` / `[M2.missed]: policy validation failed — [violation type]`
  - `M3`: `[M3.achieved]: PR draft presented to requestor with channel recommendation` / `[M3.missed]: PR draft could not be generated`
  - `M4`: `[M4.achieved]: policy exception routed to procurement manager — [exception type]` / `[M4.missed]: exception routing failed`
  - `M5`: `[M5.achieved]: PR submitted successfully — PR number [id]` / `[M5.missed]: PR submission failed — [error]`
- [ ] Add OpenTelemetry custom spans for each milestone using the pattern in `guidelines-agent-python.md`
- [ ] Verify `bootstrap(app)` is called after `app = server.build()` in `main.py`

---

## MCP Tool Integration

- [ ] Verify `api-discovery-results.md` exists with ORD IDs for all three APIs
- [ ] Invoke `mcp-translation-file` skill for `purchase-requisition.edmx`
- [ ] Invoke `setup-solution` to create/register MCP assets
- [ ] Wire MCP tool loading in `agent.py` using `get_mcp_tools()` from the `mcp_tools` module
- [ ] Add MCP server dependencies to `asset.yaml` under `requires` for all three APIs
- [ ] Generate `mcp-mock.json` using `mcp-mock-config` skill

---

## Testing

- [ ] `conftest.py` sets `IBD_TESTING=true` only
- [ ] Write unit tests in `assets/pr-drafting-assistant-agent/tests/` — one per tool:
  - `test_extract_pr_from_pdf.py` — mock LLM, test extraction and null field detection
  - `test_request_missing_field.py` — test one-field-at-a-time dialogue
  - `test_validate_supplier.py` — mock Ariba API, test approved/unapproved scenarios
  - `test_lookup_procurement_master_data.py` — mock Ariba MDS API, test cost center and GL lookup
  - `test_validate_pr_policy.py` — test all violation types (unapproved supplier, spend breach, missing fields, etc.)
  - `test_assemble_pr_draft.py` — test draft assembly with channel recommendation and decision trace
  - `test_submit_purchase_requisition.py` — mock S/4HANA OData API, test success and failure paths
  - `test_route_exception_to_manager.py` — mock notification, test routing for each exception type
- [ ] Write one integration test `test_end_to_end.py` — simulate full flow: PDF upload → extraction → gap-fill → validation → draft → confirmation → submission
- [ ] Run `pytest` from `assets/pr-drafting-assistant-agent/` (no args) — if coverage < 70%, add tests
- [ ] Verify `assets/pr-drafting-assistant-agent/app/agent.py` has exactly 9 decorated functions (run `grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/pr-drafting-assistant-agent/app/agent.py` and confirm 9)
- [ ] Run `pytest` again to generate final `test_report.json`
- [ ] Verify `test_report.json` exists in `assets/pr-drafting-assistant-agent/`
