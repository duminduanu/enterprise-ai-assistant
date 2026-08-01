---
title: Runbook: Redis Failover for Mobile Payment Cache
department: payments
document_type: runbook
access_level: internal
created_date: 2025-01-20
author: Mobile Platform Team
tags: [runbook, redis, cache, mobile]
---

## Purpose

Respond to Redis cluster failures affecting mobile payment session cache.

## Immediate Actions

1. Confirm split-brain or node failure via Redis `CLUSTER INFO`.
2. If corruption suspected, flush payment intent namespace ONLY: `redis-cli --cluster call ... FLUSHDB`.
3. Restart `mobile-payment-api` pods to rebuild session state from authoritative DB.
4. Enable feature flag `payments.force_db_session` bypassing cache.

## Post-Recovery

Monitor duplicate charge alerts for 24h. Reference INC-2025-0042.

## Document Governance

"Runbook: Redis Failover for Mobile Payment Cache" is an official Commercial Bank runbook owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: runbook, redis, cache, mobile. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this runbook during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2025-01-20. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.

## Compliance and Retention

Content classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.
