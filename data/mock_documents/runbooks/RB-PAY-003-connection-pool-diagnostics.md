---
title: Runbook: Connection Pool Diagnostics for Payment Services
department: payments
document_type: runbook
access_level: internal
created_date: 2024-04-02
author: Payments SRE
tags: [runbook, connection-pool, diagnostics]
---

## Purpose

Diagnose and remediate JDBC/HTTP connection pool exhaustion affecting payment services.

## Symptoms

- HTTP 504 from gateway
- `Pool exhausted` in application logs
- Rising `hikaricp.connections.pending` metric

## Diagnostic Steps

1. Check active connections: Grafana panel POOL-ACTIVE on `card-auth-service`.
2. Identify long-running queries on shared DB: run script `scripts/db/long_queries.sql`.
3. Review recent batch job schedule changes in CHANGE calendar.
4. Capture thread dump if wait time >30s.

## Remediation

- Kill offending ad-hoc queries (DBA approval)
- Temporarily increase pool max (max 150, requires IC approval)
- Scale horizontally if CPU allows

## Post-Incident

File CAPA if root cause is recurring pool saturation. Reference INC-2024-0847.

## Document Governance

"Runbook: Connection Pool Diagnostics for Payment Services" is an official Commercial Bank runbook owned by the payments organization. This record is indexed in the enterprise knowledge base with metadata tags: runbook, connection-pool, diagnostics. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.

## Operational Context

Teams supporting payment channels rely on this runbook during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date 2024-04-02. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.

## Systems and Integration Landscape

Commercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.

## Monitoring and Escalation

Operational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.

## Compliance and Retention

Content classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.
