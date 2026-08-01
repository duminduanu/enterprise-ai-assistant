---
title: INC-2024-1203: TLS Certificate Expiry on Payment API
department: payments
document_type: incident
access_level: internal
created_date: 2024-09-22
author: Platform Security Team
tags: [payment-failure, certificate, tls, outage]
---

## Incident Summary

On 22 September 2024 at 00:01 UTC, all outbound calls from the payment orchestration layer
to the external card processor failed TLS handshake validation. Customers attempting card
payments received a generic "Payment unavailable" message. The issue persisted for 47 minutes
until the expired intermediate certificate was replaced.

## Timeline

- **00:01 UTC** — Automated monitoring detected 100% failure on processor endpoint.
- **00:08 UTC** — SEV-1 declared; executive notification sent per policy POL-SEC-004.
- **00:19 UTC** — Certificate expiry on `processor-api.bank.internal` confirmed (expired 23:59 UTC prior day).
- **00:41 UTC** — New certificate deployed via Vault pipeline; services restarted.
- **00:48 UTC** — Success rate restored; SEV-1 downgraded.

## Impact

- **Duration:** 47 minutes
- **Failed payment attempts:** 6,840
- **Channels affected:** Web, mobile, IVR pay-by-phone
- **Regulatory:** Incident reported to central bank within 24h per compliance requirement

## Root Cause

The intermediate CA certificate for the payment processor integration was not enrolled in
the enterprise certificate inventory. The primary cert was renewed in July, but the intermediate
chain file loaded on `payment-orchestrator-prod` was stale. Certificate monitoring did not
cover partner-managed intermediates.

## Remediation

1. All payment integration certs added to CertManager with 30/14/7-day alerts.
2. Quarterly certificate audit for payments domain.
3. Failover to secondary processor tested monthly (previously quarterly).

## Lessons Learned

Certificate expiry remains a top-five root cause for payment failures industry-wide. This
incident reinforces automated discovery of full chain, not just leaf certificates.

## Document Governance

"INC-2024-1203: TLS Certificate Expiry on Payment API" is an official Commercial Bank incident owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: payment-failure, certificate, tls, outage. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this incident during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2024-09-22. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.
