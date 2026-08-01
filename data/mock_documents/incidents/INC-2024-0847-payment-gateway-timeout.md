---
title: INC-2024-0847: Payment Gateway Timeout Outage
department: payments
document_type: incident
access_level: internal
created_date: 2024-03-18
author: Payments SRE Team
tags: [payment-failure, outage, gateway, connection-pool]
---

## Incident Summary

On 18 March 2024 between 02:14 and 04:52 UTC, Commercial Bank's retail payment
gateway experienced elevated latency and intermittent transaction failures. Approximately
14,200 card authorization requests failed with HTTP 504 Gateway Timeout errors. Mobile
banking and merchant portal channels were affected. No funds were duplicated and no PCI
data exposure occurred.

## Timeline

- **02:14 UTC** — PagerDuty alert: p95 latency on `payment-gateway-prod` exceeded 8s.
- **02:31 UTC** — Incident bridge opened; severity set to SEV-2.
- **03:05 UTC** — On-call engineer identified JDBC connection pool saturation on auth service.
- **03:40 UTC** — Pool max connections increased from 80 to 120; stale connections cleared.
- **04:52 UTC** — Error rate returned to baseline; incident resolved.

## Impact

- **Duration:** 2 hours 38 minutes
- **Failed transactions:** 14,200 (0.9% of daily volume)
- **Customer complaints:** 387 via contact center
- **Revenue impact:** Estimated USD 420,000 in delayed authorizations

## Root Cause

A scheduled batch reconciliation job on the shared Oracle cluster held long-running locks,
causing connection pool exhaustion on `card-auth-service`. The pool default of 80 connections
was insufficient during peak APAC traffic overlap with batch window. Connection wait timeouts
cascaded to the API gateway.

## Remediation

1. Separated batch workload to read replica (change CHG-2024-1182).
2. Increased connection pool ceiling with dynamic scaling alerts.
3. Added circuit breaker on gateway → auth service path.
4. Updated runbook RB-PAY-003 with pool diagnostics checklist.

## Recurring Theme

Connection pool misconfiguration has appeared in three prior payment incidents (INC-2023-0912,
INC-2024-0110). Capacity reviews now mandatory before batch schedule changes.

## Document Governance

"INC-2024-0847: Payment Gateway Timeout Outage" is an official Commercial Bank incident owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: payment-failure, outage, gateway, connection-pool. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this incident during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2024-03-18. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.
