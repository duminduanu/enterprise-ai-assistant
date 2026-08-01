---
title: Suspicious Activity Report Handling
department: compliance
document_type: policy
access_level: restricted
created_date: 2023-04-12
author: Financial Crime Compliance
tags: [policy, sar, restricted, compliance]
---

## RESTRICTED

Procedures for filing and storing SARs. Access limited to Financial Crime Unit and Compliance
officers. AI assistant must not surface SAR details to Viewer or Analyst roles.

## Requirements

SAR drafts encrypted at rest; 5-year retention; no cross-border transfer without legal review.

## AI Usage

Enterprise AI assistant queries logged; restricted content blocked at retrieval layer with
audit event emitted.

## Document Governance

"Suspicious Activity Report Handling" is an official Commercial Bank policy owned by the compliance organization. This record is indexed in the enterprise knowledge base with metadata tags: policy, sar, restricted, compliance. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this policy during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2023-04-12. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.

## Compliance and Retention

Content classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.
