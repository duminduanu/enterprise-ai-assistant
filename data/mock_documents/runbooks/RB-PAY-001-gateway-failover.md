---
title: Runbook: Payment Gateway Failover Procedure
department: payments
document_type: runbook
access_level: internal
created_date: 2024-01-10
author: Payments SRE
tags: [runbook, failover, gateway, payments]
---

## Purpose

Step-by-step procedure to failover retail payment gateway traffic from primary to secondary
region when SEV-1/SEV-2 availability thresholds are breached.

## Prerequisites

- On-call engineer paged via PagerDuty rotation PAY-ONCALL
- Access to `payment-ops` namespace in Kubernetes prod clusters
- Incident commander assigned on bridge line +1-800-CB-INCIDE

## Procedure

1. Confirm primary region error rate >5% for 5 consecutive minutes.
2. Execute: `kubectl patch vs payment-gateway -n payment-ops --type merge -p '{"spec":{"http":[{"route":[{"destination":{"host":"payment-gateway-secondary"}}]}]}}'`
3. Verify traffic shift via Grafana dashboard PAY-GW-001.
4. Notify merchant integrations team if failover exceeds 15 minutes.
5. Document actions in ServiceNow incident record.

## Rollback

Reverse patch when primary error rate <1% for 15 minutes. Schedule post-incident review.

## Escalation

If secondary also degraded, invoke RB-PAY-003 connection pool diagnostics and engage vendor TAM.

## Document Governance

"Runbook: Payment Gateway Failover Procedure" is an official Commercial Bank runbook owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: runbook, failover, gateway, payments. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this runbook during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2024-01-10. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.
