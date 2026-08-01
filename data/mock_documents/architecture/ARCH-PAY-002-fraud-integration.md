---
title: Fraud Scoring Integration Architecture
department: payments
document_type: architecture
access_level: internal
created_date: 2024-12-15
author: Risk Engineering
tags: [architecture, fraud, integration]
---

## Design Goals

Sub-300ms p99 fraud scoring on critical path; graceful degradation when vendor unavailable;
audit trail for all decisions.

## Current State (Post INC-2024-1566)

- Primary: FraudShield REST API (sync, 3s timeout)
- Secondary: RiskGuard (pilot failover, feature flag controlled)
- Async path: Kafka topic `fraud.score.async` for low-value transactions

## Sequence

1. Payment orchestrator receives auth request
2. Enrichment service adds device, geo, velocity features
3. Fraud adapter calls primary vendor; fallback on timeout/error
4. Decision cached 60s for retry idempotency

## Future

ML-based inline model on feature store (2025 H2 roadmap).

## Document Governance

"Fraud Scoring Integration Architecture" is an official Commercial Bank architecture owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: architecture, fraud, integration. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this architecture during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2024-12-15. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.

## Compliance and Retention

Content classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.
