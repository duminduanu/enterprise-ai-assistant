---
title: INC-2024-0891: ATM Network Link to Payment Core Degraded
department: platform
document_type: incident
access_level: internal
created_date: 2024-07-12
author: ATM Operations
tags: [payment-failure, atm, network, degradation]
---

## Incident Summary

Degraded MPLS link between the ATM switch and payment core caused intermittent authorization
timeouts at 340 ATM locations across the Midlands region. Cash withdrawal success rate
dropped to 72% for 4 hours. Card-present payment failures at ATM-attached POS terminals
were also reported. This incident is classified as a payment failure on the card-present
channel due to authorization timeout rather than issuer decline.

## Timeline

- **08:10 UTC** — ATM monitoring detected elevated host disconnect rate on MPLS circuit CB-AT M-04.
- **08:35 UTC** — Carrier confirmed fiber cut near Birmingham exchange; ETA repair 6 hours.
- **09:00 UTC** — Automatic failover to backup MPLS link; latency increased from 18ms to 890ms.
- **09:15 UTC** — Payment core ISO 8583 timeout (2.5s) exceeded on 28% of ATM auth requests.
- **12:20 UTC** — Primary circuit restored; success rate recovered by 12:45 UTC.

## Impact

- **Duration:** 4 hours 35 minutes degraded service
- **Failed ATM transactions:** 19,400 (withdrawals and balance inquiries)
- **POS at ATM locations affected:** 85 convenience store terminals

## Root Cause

Primary root cause was carrier fiber cut on primary MPLS path. Contributing factor: backup
link latency exceeded ISO 8583 timeout budget configured for ATM channel. Failover design
assumed backup latency under 400ms; actual backup path routed via secondary carrier with
higher hop count during partial regional outage.

## Remediation

1. ATM channel timeout budget reviewed; adaptive timeout for failover mode (max 4.0s, IC approved).
2. Secondary carrier diversity contract signed for ATM MPLS pairs.
3. Quarterly failover drill including latency validation under load.

## Related Patterns

Network degradation as payment failure root cause is distinct from application connection pool
issues but produces identical customer symptom (declined/timeout). Operations teams should
verify network path before deep-diving application pools.

## Document Governance

"INC-2024-0891: ATM Network Link to Payment Core Degraded" is an official Commercial Bank incident owned by the platform organization. This record is indexed in the enterprise knowledge base with metadata tags: payment-failure, atm, network, degradation. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.
