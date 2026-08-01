---
title: IT Change Management Policy
department: platform
document_type: policy
access_level: internal
created_date: 2022-11-20
author: IT Governance
tags: [policy, change, cab]
---

## Standard Changes

Pre-approved low-risk changes follow automated pipeline. Payment production changes require
CAB approval except emergency rollback (RB-REL-001).

## Emergency Changes

Allowed during SEV-1/SEV-2 with retrospective CAB within 48 hours. Documented root cause
for deployment-related incidents (see INC-2025-0189) triggers enhanced review.

## Blackout Periods

Retail payment freeze: December 24–26, major tax deadline days.

## Document Governance

"IT Change Management Policy" is an official Commercial Bank policy owned by the platform organization. This record is indexed in the enterprise knowledge base with metadata tags: policy, change, cab. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this policy during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2022-11-20. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.

## Compliance and Retention

Content classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.

## Revision History and Contacts

| Version | Date | Author | Change Summary |
|---------|------|--------|----------------|
| 1.0 | 2022-11-20 | IT Governance | Initial controlled publication |

Document feedback: #platform-ops Slack or platform-docs@commercialbank.internal. For after-hours payment escalation, invoke RB-OPS-002 severity classification and open a ServiceNow incident.
