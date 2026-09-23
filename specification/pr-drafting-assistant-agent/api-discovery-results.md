# API Discovery Results

## APIs Used in This Solution

| API Name | ORD ID | Type | Spec File |
|---|---|---|---|
| Purchase Requisition (S/4HANA) | `sap.s4:apiResource:API_PURCHASEREQ_PROCESS_SRV:v1` | OData EDMX | `api-specs/purchase-requisition.edmx` |
| Supplier Data API With Pagination (Ariba) | `sap.aribas4:apiResource:supplierdatapagination:v4` | REST OpenAPI | — (no spec saved; use MCP path B) |
| Master Data Retrieval API for Procurement (Ariba) | `sap.aribabuyer:apiResource:mds_search:v1` | REST OpenAPI | — (no spec saved; use MCP path B) |

## Notes

- The Purchase Requisition EDMX spec is saved at `api-specs/purchase-requisition.edmx` and will be processed by the `mcp-translation-file` skill to generate an MCP server translation.
- The Ariba Supplier Data and Master Data APIs are accessed via direct MCP path B (ORD IDs registered in `asset.yaml` under `requires`).
- No MCP servers were found for any of these APIs via `get_mcp` lookup — all integration goes through generated MCP translation files or direct OData/REST calls via the agent gateway.
