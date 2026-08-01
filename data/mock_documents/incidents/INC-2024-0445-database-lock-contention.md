---
title: INC-2024-0445: Database Lock Contention on Settlement DB
department: payments
document_type: incident
access_level: internal
created_date: 2024-05-30
author: Database Reliability Team
tags: [payment-failure, database, lock, settlement]
---

## Incident Summary

On 30 May 2024, lock contention on the settlement ledger table caused payment posting delays.
Real-time balance updates for premium banking customers lagged up to 18 minutes. While
authorizations succeeded, settlement confirmation failures triggered false "payment failed"
notifications in the mobile app.

## Timeline

- **16:00 UTC** — Lock wait events exceeded threshold on `SETTLEMENT_LEDGER`.
- **16:22 UTC** — Mobile app push notifications for failed payments spiked (false positives).
- **17:05 UTC** — Long-running analytics query killed; locks released.
- **17:18 UTC** — Notification queue drained; balances reconciled.

## Impact

- **Duration:** 1 hour 18 minutes
- **False failure notifications:** 8,900
- **Actual unsettled transactions:** 0 (delayed only)

## Root Cause

Ad-hoc analytics query on production settlement DB without read-uncommitted isolation held
shared locks during peak settlement window. Combined with index rebuild job overlap,
exclusive lock requests from payment posting service timed out.

## Remediation

Read replicas mandatory for analytics; query governor enforced; index maintenance windows
aligned with low settlement volume periods.

## Document Governance

"INC-2024-0445: Database Lock Contention on Settlement DB" is an official Commercial Bank incident owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: payment-failure, database, lock, settlement. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this incident during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2024-05-30. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.
