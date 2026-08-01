---
title: Instant Payments Rail Integration Spec
department: payments
document_type: spec
access_level: internal
created_date: 2024-11-18
author: Payments Product
tags: [spec, instant-payments, iso20022]
---

## Scope

ISO 20022 instant credit transfer for domestic retail and corporate clients.

## SLA

End-to-end processing under 10 seconds; 99.9% availability target.

## Fraud Controls

Mandatory sync fraud check >USD 500; velocity limits 5 transfers/hour retail.

## Incident Reference

Fraud ring investigation INC-2024-1120 led to enhanced payee cooling period (24h new payees).

## Document Governance

"Instant Payments Rail Integration Spec" is an official Commercial Bank spec owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: spec, instant-payments, iso20022. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this spec during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2024-11-18. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.

## Compliance and Retention

Content classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.

## Revision History and Contacts

| Version | Date | Author | Change Summary |
|---------|------|--------|----------------|
| 1.0 | 2024-11-18 | Payments Product | Initial controlled publication |

Document feedback: #payments-ops Slack or payments-docs@commercialbank.internal. For after-hours payment escalation, invoke RB-OPS-002 severity classification and open a ServiceNow incident.
