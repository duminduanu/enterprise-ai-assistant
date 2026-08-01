---
title: INC-2025-0267: Internal API Rate Limit Cascade
department: platform
document_type: incident
access_level: internal
created_date: 2025-02-28
author: API Platform Team
tags: [outage, rate-limit, cascade, api]
---

## Incident Summary

An aggressive retry storm from the notification service tripped rate limits on the account
validation service, which the bill pay payment pre-check depends on. Cascading HTTP 429
responses caused payment pre-check failures for the online bill pay feature between 11:00
and 13:15 UTC on 28 February 2025. Card payment channels were unaffected; this incident
targeted ACH and bill pay validation flows.

## Timeline

- **11:02 UTC** — Account service rate limit alerts: client `notif-svc-prod` exceeded 5K req/min quota.
- **11:18 UTC** — Bill pay failure rate rose to 11%; incident bridge opened as SEV-3.
- **11:45 UTC** — Engineers identified notification batch replay after Kafka consumer lag recovery.
- **12:30 UTC** — Notification replay paused; rate limit temporarily raised for account service.
- **13:15 UTC** — Bill pay failure rate normalized; permanent fixes scheduled.

## Impact

- **Duration:** 2 hours 15 minutes
- **Failed bill pay initiations:** 3,280
- **Duplicate notifications sent during replay:** 14,200 (separate customer comms issue)

## Root Cause

Missing jitter on exponential backoff in notification service client caused synchronized
retry spikes. Shared service account between batch replay and online traffic meant batch
recovery consumed entire rate limit quota for the account validation API. Payment validation
calls received 429 and surfaced as generic payment failure to end users.

## Remediation

1. Dedicated OAuth client credentials for batch vs online notification paths.
2. Client SDK updated to honor `Retry-After` headers with randomized jitter.
3. Circuit breaker on bill pay → account service with cached read fallback for non-mutating checks.
4. Rate limit dashboards added to payment ops war room wallboard.

## Lessons Learned

Internal platform rate limits can cause customer-facing payment failures without any payment
service degradation. Cross-team dependency mapping updated to include account service as
critical dependency for bill pay channel.

## Document Governance

"INC-2025-0267: Internal API Rate Limit Cascade" is an official Commercial Bank incident owned by the platform organization. This record is indexed in the enterprise knowledge base with metadata tags: outage, rate-limit, cascade, api. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.
