---
title: INC-2025-0042: Redis Cache Failure — Mobile Payments
department: payments
document_type: incident
access_level: internal
created_date: 2025-01-15
author: Mobile Platform Team
tags: [payment-failure, cache, redis, mobile]
---

## Incident Summary

On 15 January 2025, a misconfigured Redis Cluster failover in the mobile payments region
caused session token and payment intent cache corruption. Users experienced "Payment session
expired" errors and duplicate tap-to-pay prompts. The incident lasted 1 hour 12 minutes
during lunch-hour peak in the UK market.

## Timeline

- **12:04 UTC** — Redis node `redis-pay-mobile-02` marked failed; automatic failover triggered.
- **12:11 UTC** — Mobile payment error rate exceeded 25%.
- **12:28 UTC** — Engineers identified split-brain during failover; cache keys inconsistent.
- **12:56 UTC** — Cache flushed; services restarted with read-from-primary enforced.
- **13:16 UTC** — Metrics normalized; customer comms published.

## Impact

- **Duration:** 1 hour 12 minutes
- **Affected users:** ~89,000 mobile sessions
- **Failed payment attempts:** 11,300
- **Duplicate charge reports:** 23 (all reversed within 2h)

## Root Cause

Redis Cluster failover occurred during a network partition. The cache layer stored ephemeral
payment intent IDs without sufficient TTL overlap handling. When stale cache entries were
served post-failover, payment state machine rejected valid sessions. Cache failure as root
cause classified under infrastructure resilience gap.

## Remediation

1. Payment intent cache moved to strongly consistent store for critical path.
2. Redis failover drills added to monthly calendar.
3. Idempotency keys enforced on all mobile payment endpoints.

## Pattern Note

Cache-related payment failures increased 40% YoY across the industry. This incident aligns
with recurring theme: ephemeral state in distributed cache without graceful degradation path.

## Document Governance

"INC-2025-0042: Redis Cache Failure — Mobile Payments" is an official Commercial Bank incident owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: payment-failure, cache, redis, mobile. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this incident during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2025-01-15. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.
