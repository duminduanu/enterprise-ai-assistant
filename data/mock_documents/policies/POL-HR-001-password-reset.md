---
title: Password Reset Policy
department: security
document_type: policy
access_level: public
created_date: 2023-01-15
author: Information Security
tags: [policy, password, identity]
---

## Scope

All Commercial Bank employees, contractors, and third parties with access to corporate systems.

## Password Requirements

- Minimum 14 characters; passphrase encouraged
- MFA mandatory for all remote access
- Password reset via self-service portal or verified helpdesk call

## Reset Procedure

1. User navigates to `https://identity.commercialbank.internal/reset`
2. Verifies identity via MFA device or manager attestation for locked accounts
3. Temporary password expires in 24 hours; forced change on first login

## Helpdesk

Helpdesk agents must verify employee ID and two security questions before manual reset.
Payment system admin accounts require CISO approval for any reset.

## Audit

All reset events logged to SIEM with 7-year retention.

## Document Governance

"Password Reset Policy" is an official Commercial Bank policy owned by the security organization. This record is indexed in the enterprise knowledge base with metadata tags: policy, password, identity. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this policy during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2023-01-15. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.

## Compliance and Retention

Content classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.
