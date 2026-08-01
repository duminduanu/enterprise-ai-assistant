---
title: Payment Platform Architecture Overview
department: payments
document_type: architecture
access_level: internal
created_date: 2024-01-25
author: Enterprise Architecture
tags: [architecture, payments, overview]
---

## Executive Summary

Commercial Bank's payment platform processes 1.6M transactions daily across card, ACH,
instant payments, and bill pay channels. The architecture follows a hub-and-spoke model
with `payment-orchestrator` as central workflow engine.

## Core Components

- **payment-gateway-prod** — North-south API entry, OAuth2, rate limiting
- **payment-router-service** — ISO 8583 / ISO 20022 message routing
- **card-auth-service** — Authorization, connection pool to Oracle ledger
- **fraud-scoring-adapter** — Sync/async fraud vendor integration
- **settlement-batch-engine** — End-of-day clearing and reconciliation

## Data Stores

- Oracle Exadata: authoritative ledger (SETTLEMENT_LEDGER)
- Redis Cluster: session cache, idempotency keys
- Pinecone (search index): operational runbook RAG for internal ops (meta)

## Resilience Patterns

Circuit breakers on all vendor calls; dual-region active-passive for gateway; connection
pool autoscaling with HikariCP. Known weak points documented in Q4 reliability review:
shared batch/online DB connections, single primary fraud vendor.

## Integration Points

External: card processor, ACH network, FraudShield, open banking aggregators.
Internal: core banking, CRM, notification service, data warehouse.

## Document Governance

"Payment Platform Architecture Overview" is an official Commercial Bank architecture owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: architecture, payments, overview. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this architecture during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2024-01-25. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.
