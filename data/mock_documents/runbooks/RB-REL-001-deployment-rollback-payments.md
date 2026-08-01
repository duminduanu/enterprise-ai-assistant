---
title: Runbook: Emergency Rollback — Payment Router
department: payments
document_type: runbook
access_level: internal
created_date: 2025-02-05
author: Release Engineering
tags: [runbook, rollback, deployment]
---

## Purpose

Emergency rollback procedure for `payment-router-service` when post-deploy metrics breach
thresholds within 30 minutes of rollout.

## Rollback Command

`helm rollback payment-router -n payment-ops 0` (previous revision)

## Verification

- Contactless approval rate within 2% of 7-day baseline
- ISO 8583 field validation test suite passes (automated, 3 min)

## Authority

On-call may rollback without CAB approval when SEV-2 criteria met.

See INC-2025-0189 for context.

## Document Governance

"Runbook: Emergency Rollback — Payment Router" is an official Commercial Bank runbook owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: runbook, rollback, deployment. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this runbook during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2025-02-05. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.

## Compliance and Retention

Content classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.
