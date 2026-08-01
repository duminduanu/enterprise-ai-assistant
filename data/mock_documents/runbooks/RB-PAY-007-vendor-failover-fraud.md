---
title: Runbook: Fraud Vendor Failover
department: payments
document_type: runbook
access_level: internal
created_date: 2024-12-01
author: Risk Engineering
tags: [runbook, vendor, fraud, failover]
---

## Purpose

Failover procedure when primary fraud vendor (FraudShield) exceeds latency SLA or returns
error rate above 10% for 3 minutes.

## Options

1. **Secondary vendor route** — Enable feature flag `fraud.secondary.enabled` (Analyst+ role).
2. **Risk-based bypass** — Transactions under configured threshold skip sync check (IC approval).
3. **Queue async** — Route to async scoring; hold settlement until score received (max 15 min).

## Authorization

Bypass options require Risk Officer on bridge. All bypass periods logged to audit store.

## Reference

Created after INC-2024-1566 vendor timeout incident.

## Document Governance

"Runbook: Fraud Vendor Failover" is an official Commercial Bank runbook owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: runbook, vendor, fraud, failover. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this runbook during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2024-12-01. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.

## Compliance and Retention

Content classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.
