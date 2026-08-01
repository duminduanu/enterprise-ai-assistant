---
title: Runbook: Certificate Rotation for Payment Integrations
department: security
document_type: runbook
access_level: internal
created_date: 2024-10-01
author: PKI Team
tags: [runbook, certificate, rotation, payments]
---

## Purpose

Standard procedure for rotating TLS certificates on payment integration endpoints without
service interruption.

## Schedule

- Leaf certificates: 90-day cycle via ACME/Vault
- Manual partner certs: 30/14/7-day alerts

## Procedure

1. Generate CSR in Vault PKI mount `payment-intermediate`.
2. Submit to partner portal; obtain signed chain.
3. Deploy to staging; run `payment-tls-verify.sh` against all endpoints.
4. Blue-green deploy to prod load balancers during maintenance window.
5. Validate handshake from orchestrator pods.

## Rollback

Retain previous cert bundle 72h. Instant revert via LB cert reference swap.

Created in response to INC-2024-1203 certificate expiry incident.

## Document Governance

"Runbook: Certificate Rotation for Payment Integrations" is an official Commercial Bank runbook owned by the security organization. This record is indexed in the enterprise knowledge base with metadata tags: runbook, certificate, rotation, payments. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this runbook during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2024-10-01. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.

## Compliance and Retention

Content classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.
