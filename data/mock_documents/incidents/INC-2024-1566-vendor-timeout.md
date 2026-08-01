---
title: INC-2024-1566: Third-Party Fraud Vendor Timeout
department: payments
document_type: incident
access_level: internal
created_date: 2024-11-08
author: Payments Operations
tags: [payment-failure, vendor, timeout, fraud]
---

## Incident Summary

On 8 November 2024 between 14:00 and 16:35 UTC, the real-time fraud scoring vendor
(FraudShield) experienced regional degradation. Commercial Bank's payment flow requires
synchronous fraud checks for transactions above USD 500. Requests queued beyond the
3-second SLA, causing widespread payment failures and cart abandonment across e-commerce
merchant integrations.

## Timeline

- **14:02 UTC** — Fraud check latency p99 rose from 200ms to 12s.
- **14:15 UTC** — Payment failure rate hit 18%; incident bridge opened.
- **14:50 UTC** — Vendor confirmed DDoS on their EU-West endpoint.
- **15:30 UTC** — Temporary bypass approved for transactions under USD 2,000 (risk accepted).
- **16:35 UTC** — Vendor restored; bypass disabled; manual review queue cleared within 4h.

## Impact

- **Duration:** 2 hours 33 minutes full degradation; partial mitigation after 90 minutes
- **Failed payments:** 22,100
- **Manual fraud reviews post-incident:** 1,847 transactions

## Root Cause

Primary root cause was third-party vendor SLA breach during DDoS attack. Contributing factor:
Commercial Bank had no async fallback path—fraud check was blocking on critical payment path
with insufficient timeout tuning (hard 3s vs vendor p99 of 800ms under normal load).

## Remediation

1. Implemented async fraud scoring for non-high-risk segments.
2. Negotiated improved SLA with penalty clauses.
3. Added secondary vendor for failover (pilot in Q1 2025).

## Related Documents

See architecture doc ARCH-PAY-002 for updated fraud integration design and runbook
RB-PAY-007 for vendor failover procedure.

## Document Governance

"INC-2024-1566: Third-Party Fraud Vendor Timeout" is an official Commercial Bank incident owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: payment-failure, vendor, timeout, fraud. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this incident during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2024-11-08. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.
