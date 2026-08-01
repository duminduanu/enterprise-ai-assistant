---
title: Data Classification Policy
department: compliance
document_type: policy
access_level: public
created_date: 2022-06-01
author: Data Governance
tags: [policy, data, classification]
---

## Classification Levels

**Public** — Marketing materials, published policies
**Internal** — Operational docs, runbooks, internal architecture
**Restricted** — Fraud investigations, executive reviews, PCI detailed configs

## Handling

Restricted documents require role-based access in knowledge systems. AI assistant must filter
retrieval by user role and document `access_level` metadata.

## Labeling

All documents in enterprise knowledge base must include `access_level` in metadata.

## Document Governance

"Data Classification Policy" is an official Commercial Bank policy owned by the compliance organization. This record is indexed in the enterprise knowledge base with metadata tags: policy, data, classification. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this policy during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2022-06-01. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.

## Compliance and Retention

Content classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.

## Revision History and Contacts

| Version | Date | Author | Change Summary |
|---------|------|--------|----------------|
| 1.0 | 2022-06-01 | Data Governance | Initial controlled publication |

Document feedback: #compliance-ops Slack or compliance-docs@commercialbank.internal. For after-hours payment escalation, invoke RB-OPS-002 severity classification and open a ServiceNow incident.
