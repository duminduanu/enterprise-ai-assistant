---
title: Runbook: Incident Severity Classification
department: platform
document_type: runbook
access_level: public
created_date: 2023-06-15
author: Site Reliability Engineering
tags: [runbook, incident, severity, sev]
---

## Severity Definitions

**SEV-1:** Complete loss of critical customer-facing service (payments, account access) or
regulatory breach. Executive notification within 15 minutes.

**SEV-2:** Significant degradation (>5% failure rate or >2s p95 latency on critical paths).

**SEV-3:** Limited impact, workaround available.

**SEV-4:** Minor issue, next business day resolution acceptable.

## Payment-Specific Guidance

Any payment failure rate exceeding 2% for 10 minutes auto-classifies as minimum SEV-2.
Contactless or ACH settlement delays affecting corporate SLA auto-SEV-2.

## Process

Incident commander assigns severity within 10 minutes of bridge open. Severity changes
documented in incident timeline with justification.

## Document Governance

"Runbook: Incident Severity Classification" is an official Commercial Bank runbook owned by the platform organization. This record is indexed in the enterprise knowledge base with metadata tags: runbook, incident, severity, sev. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this runbook during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2023-06-15. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.

## Compliance and Retention

Content classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.
