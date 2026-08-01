---
title: INC-2025-0311: Load Balancer Misconfiguration — ACH Payments
department: payments
document_type: incident
access_level: internal
created_date: 2025-03-11
author: Network Operations
tags: [payment-failure, load-balancer, ach, network]
---

## Incident Summary

On 11 March 2025, a change to F5 load balancer pool weights during datacenter maintenance
routed 70% of ACH settlement traffic to a single degraded backend node. Batch settlement
jobs timed out; corporate clients reported delayed payroll transfers. Payment failure in
this context means settlement could not complete within SLA windows.

## Timeline

- **01:00 UTC** — Planned maintenance window started for DC2 network gear.
- **01:45 UTC** — ACH batch job failure alerts; 45% of batches in RETRY state.
- **02:10 UTC** — Load balancer config reviewed; asymmetric routing discovered.
- **02:35 UTC** — Weights restored; backlog processing initiated.
- **05:20 UTC** — All batches cleared; SLA breach notifications sent to 12 corporate clients.

## Impact

- **Duration:** 3 hours 35 minutes to clear backlog
- **Delayed ACH transfers:** USD 840M aggregate value (timing delay only)
- **SLA breaches:** 12 corporate tier-1 clients

## Root Cause

Load balancer pool member health check interval increased during maintenance script run,
but weight redistribution logic did not account for one member in soft-degraded state.
Traffic concentration caused connection exhaustion on single settlement adapter instance—
related to but distinct from application-level connection pool issues (see INC-2024-0847).

## Remediation

1. Load balancer changes require dual approval for payment pools.
2. Automated pre-change validation script for pool symmetry.
3. ACH batch retry logic enhanced with exponential backoff.

## Classification

Payment failure due to infrastructure misconfiguration; logged for annual root cause
aggregation under "network/routing" category.

## Document Governance

"INC-2025-0311: Load Balancer Misconfiguration — ACH Payments" is an official Commercial Bank incident owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: payment-failure, load-balancer, ach, network. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this incident during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2025-03-11. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.
