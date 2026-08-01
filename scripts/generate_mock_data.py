#!/usr/bin/env python3
"""Generate mock enterprise documents for Commercial Bank knowledge base.

Usage:
    python scripts/generate_mock_data.py [--force]
    node scripts/generate_mock_data.mjs [--force]   # fallback if Python unavailable
"""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "mock_documents"


def frontmatter(meta: dict) -> str:
    tags = meta.get("tags", [])
    tags_yaml = "[" + ", ".join(tags) + "]"
    return dedent(f"""\
        ---
        title: {meta['title']}
        department: {meta['department']}
        document_type: {meta['document_type']}
        access_level: {meta['access_level']}
        created_date: {meta['created_date']}
        author: {meta['author']}
        tags: {tags_yaml}
        ---
    """)


def dedent_body(body: str) -> str:
    lines = body.split("\n")
    non_empty = [line for line in lines if line.strip()]
    if not non_empty:
        return ""
    min_indent = min(len(line) - len(line.lstrip()) for line in non_empty)
    return "\n".join(line[min_indent:] if line.strip() else "" for line in lines).strip()


def expand_document(body: str, meta: dict, min_words: int = 320) -> str:
    """Pad short documents with relevant enterprise context to meet word-count targets."""
    words = body.split()
    if len(words) >= min_words:
        return body

    department = meta.get("department", "platform")
    doc_type = meta.get("document_type", "document")
    title = meta.get("title", "Untitled")
    created = meta.get("created_date", "2024-01-01")
    author = meta.get("author", "Document Owner")
    tags = ", ".join(meta.get("tags", []))

    sections = [
        f"""
        ## Document Governance

        "{title}" is an official Commercial Bank {doc_type.replace('_', ' ')} owned by the
        {department} organization. This record is indexed in the enterprise knowledge base with
        metadata tags: {tags}. Document custodians must propose updates via the standard review
        workflow in Confluence before modifying controlled sections that affect production systems.
        """,
        f"""
        ## Operational Context

        Teams supporting payment channels rely on this {doc_type.replace('_', ' ')} during daily
        operations, incident bridges, and regulatory examinations. When referenced by the enterprise
        AI assistant, retrieved excerpts must include attribution to this source file and creation
        date {created}. Cross-functional stakeholders in payments, platform engineering, security, and
        compliance may consume summaries derived from this document based on RBAC access level.
        """,
        f"""
        ## Systems and Integration Landscape

        Commercial Bank operates a hub-and-spoke payment architecture. Core services include
        payment-gateway-prod (customer entry), payment-router-service (message routing),
        card-auth-service (authorization against Oracle ledger), settlement-batch-engine (clearing),
        and fraud-scoring-adapter (vendor integration). Infrastructure dependencies span Redis
        session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2.
        Changes impacting any dependency require CAB approval except emergency rollback scenarios.
        """,
        f"""
        ## Monitoring and Escalation

        Operational metrics for payment health are published on Grafana dashboards PAY-GW-001,
        POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated
        alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders
        should preserve timeline accuracy, customer impact estimates, and root cause category
        (connection pool, certificate, vendor timeout, cache, deployment, network) for quarterly
        reliability aggregation reported to executive leadership.
        """,
        f"""
        ## Compliance and Retention

        Content classification follows POL-DATA-002. Handling requirements differ for public,
        internal, and restricted access levels. PCI-DSS controls apply when documents reference
        cardholder data environments. Retention: seven years for operational records, ten years
        when regulatory reporting is implicated. Access to restricted variants requires
        administrator or designated compliance roles; all retrievals are audit logged.
        """,
        f"""
        ## Revision History and Contacts

        | Version | Date | Author | Change Summary |
        |---------|------|--------|----------------|
        | 1.0 | {created} | {author} | Initial controlled publication |

        Document feedback: #{department}-ops Slack channel or {department}-docs@commercialbank.internal.
        For after-hours escalation related to payment incidents, invoke RB-OPS-002 severity
        classification and open a ServiceNow incident linked to the relevant problem record.
        """,
    ]

    expanded = body
    idx = 0
    while len(expanded.split()) < min_words:
        expanded += "\n" + dedent_body(sections[idx % len(sections)])
        idx += 1
        if idx > 12:
            break

    return expanded


def write_doc(folder: str, filename: str, meta: dict, body: str) -> Path:
    path = OUTPUT_DIR / folder / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    content = frontmatter(meta) + "\n" + expand_document(dedent_body(body), meta) + "\n"
    path.write_text(content, encoding="utf-8")
    return path


def incident_docs() -> list[tuple[str, dict, str]]:
    return [
        (
            "INC-2024-0847-payment-gateway-timeout.md",
            {
                "title": "INC-2024-0847: Payment Gateway Timeout Outage",
                "department": "payments",
                "document_type": "incident",
                "access_level": "internal",
                "created_date": "2024-03-18",
                "author": "Payments SRE Team",
                "tags": ["payment-failure", "outage", "gateway", "connection-pool"],
            },
            """
            ## Incident Summary

            On 18 March 2024 between 02:14 and 04:52 UTC, Commercial Bank's retail payment
            gateway experienced elevated latency and intermittent transaction failures. Approximately
            14,200 card authorization requests failed with HTTP 504 Gateway Timeout errors. Mobile
            banking and merchant portal channels were affected. No funds were duplicated and no PCI
            data exposure occurred.

            ## Timeline

            - **02:14 UTC** — PagerDuty alert: p95 latency on `payment-gateway-prod` exceeded 8s.
            - **02:31 UTC** — Incident bridge opened; severity set to SEV-2.
            - **03:05 UTC** — On-call engineer identified JDBC connection pool saturation on auth service.
            - **03:40 UTC** — Pool max connections increased from 80 to 120; stale connections cleared.
            - **04:52 UTC** — Error rate returned to baseline; incident resolved.

            ## Impact

            - **Duration:** 2 hours 38 minutes
            - **Failed transactions:** 14,200 (0.9% of daily volume)
            - **Customer complaints:** 387 via contact center
            - **Revenue impact:** Estimated USD 420,000 in delayed authorizations

            ## Root Cause

            A scheduled batch reconciliation job on the shared Oracle cluster held long-running locks,
            causing connection pool exhaustion on `card-auth-service`. The pool default of 80 connections
            was insufficient during peak APAC traffic overlap with batch window. Connection wait timeouts
            cascaded to the API gateway.

            ## Remediation

            1. Separated batch workload to read replica (change CHG-2024-1182).
            2. Increased connection pool ceiling with dynamic scaling alerts.
            3. Added circuit breaker on gateway → auth service path.
            4. Updated runbook RB-PAY-003 with pool diagnostics checklist.

            ## Recurring Theme

            Connection pool misconfiguration has appeared in three prior payment incidents (INC-2023-0912,
            INC-2024-0110). Capacity reviews now mandatory before batch schedule changes.
            """,
        ),
        (
            "INC-2024-1203-certificate-expiry.md",
            {
                "title": "INC-2024-1203: TLS Certificate Expiry on Payment API",
                "department": "payments",
                "document_type": "incident",
                "access_level": "internal",
                "created_date": "2024-09-22",
                "author": "Platform Security Team",
                "tags": ["payment-failure", "certificate", "tls", "outage"],
            },
            """
            ## Incident Summary

            On 22 September 2024 at 00:01 UTC, all outbound calls from the payment orchestration layer
            to the external card processor failed TLS handshake validation. Customers attempting card
            payments received a generic "Payment unavailable" message. The issue persisted for 47 minutes
            until the expired intermediate certificate was replaced.

            ## Timeline

            - **00:01 UTC** — Automated monitoring detected 100% failure on processor endpoint.
            - **00:08 UTC** — SEV-1 declared; executive notification sent per policy POL-SEC-004.
            - **00:19 UTC** — Certificate expiry on `processor-api.bank.internal` confirmed (expired 23:59 UTC prior day).
            - **00:41 UTC** — New certificate deployed via Vault pipeline; services restarted.
            - **00:48 UTC** — Success rate restored; SEV-1 downgraded.

            ## Impact

            - **Duration:** 47 minutes
            - **Failed payment attempts:** 6,840
            - **Channels affected:** Web, mobile, IVR pay-by-phone
            - **Regulatory:** Incident reported to central bank within 24h per compliance requirement

            ## Root Cause

            The intermediate CA certificate for the payment processor integration was not enrolled in
            the enterprise certificate inventory. The primary cert was renewed in July, but the intermediate
            chain file loaded on `payment-orchestrator-prod` was stale. Certificate monitoring did not
            cover partner-managed intermediates.

            ## Remediation

            1. All payment integration certs added to CertManager with 30/14/7-day alerts.
            2. Quarterly certificate audit for payments domain.
            3. Failover to secondary processor tested monthly (previously quarterly).

            ## Lessons Learned

            Certificate expiry remains a top-five root cause for payment failures industry-wide. This
            incident reinforces automated discovery of full chain, not just leaf certificates.
            """,
        ),
        (
            "INC-2024-1566-vendor-timeout.md",
            {
                "title": "INC-2024-1566: Third-Party Fraud Vendor Timeout",
                "department": "payments",
                "document_type": "incident",
                "access_level": "internal",
                "created_date": "2024-11-08",
                "author": "Payments Operations",
                "tags": ["payment-failure", "vendor", "timeout", "fraud"],
            },
            """
            ## Incident Summary

            On 8 November 2024 between 14:00 and 16:35 UTC, the real-time fraud scoring vendor
            (FraudShield) experienced regional degradation. Commercial Bank's payment flow requires
            synchronous fraud checks for transactions above USD 500. Requests queued beyond the
            3-second SLA, causing widespread payment failures and cart abandonment across e-commerce
            merchant integrations.

            ## Timeline

            - **14:02 UTC** — Fraud check latency p99 rose from 200ms to 12s.
            - **14:15 UTC** — Payment failure rate hit 18%; incident bridge opened.
            - **14:50 UTC** — Vendor confirmed DDoS on their EU-West endpoint.
            - **15:30 UTC** — Temporary bypass approved for transactions under USD 2,000 (risk accepted).
            - **16:35 UTC** — Vendor restored; bypass disabled; manual review queue cleared within 4h.

            ## Impact

            - **Duration:** 2 hours 33 minutes full degradation; partial mitigation after 90 minutes
            - **Failed payments:** 22,100
            - **Manual fraud reviews post-incident:** 1,847 transactions

            ## Root Cause

            Primary root cause was third-party vendor SLA breach during DDoS attack. Contributing factor:
            Commercial Bank had no async fallback path—fraud check was blocking on critical payment path
            with insufficient timeout tuning (hard 3s vs vendor p99 of 800ms under normal load).

            ## Remediation

            1. Implemented async fraud scoring for non-high-risk segments.
            2. Negotiated improved SLA with penalty clauses.
            3. Added secondary vendor for failover (pilot in Q1 2025).

            ## Related Documents

            See architecture doc ARCH-PAY-002 for updated fraud integration design and runbook
            RB-PAY-007 for vendor failover procedure.
            """,
        ),
        (
            "INC-2025-0042-redis-cache-failure.md",
            {
                "title": "INC-2025-0042: Redis Cache Failure — Mobile Payments",
                "department": "payments",
                "document_type": "incident",
                "access_level": "internal",
                "created_date": "2025-01-15",
                "author": "Mobile Platform Team",
                "tags": ["payment-failure", "cache", "redis", "mobile"],
            },
            """
            ## Incident Summary

            On 15 January 2025, a misconfigured Redis Cluster failover in the mobile payments region
            caused session token and payment intent cache corruption. Users experienced "Payment session
            expired" errors and duplicate tap-to-pay prompts. The incident lasted 1 hour 12 minutes
            during lunch-hour peak in the UK market.

            ## Timeline

            - **12:04 UTC** — Redis node `redis-pay-mobile-02` marked failed; automatic failover triggered.
            - **12:11 UTC** — Mobile payment error rate exceeded 25%.
            - **12:28 UTC** — Engineers identified split-brain during failover; cache keys inconsistent.
            - **12:56 UTC** — Cache flushed; services restarted with read-from-primary enforced.
            - **13:16 UTC** — Metrics normalized; customer comms published.

            ## Impact

            - **Duration:** 1 hour 12 minutes
            - **Affected users:** ~89,000 mobile sessions
            - **Failed payment attempts:** 11,300
            - **Duplicate charge reports:** 23 (all reversed within 2h)

            ## Root Cause

            Redis Cluster failover occurred during a network partition. The cache layer stored ephemeral
            payment intent IDs without sufficient TTL overlap handling. When stale cache entries were
            served post-failover, payment state machine rejected valid sessions. Cache failure as root
            cause classified under infrastructure resilience gap.

            ## Remediation

            1. Payment intent cache moved to strongly consistent store for critical path.
            2. Redis failover drills added to monthly calendar.
            3. Idempotency keys enforced on all mobile payment endpoints.

            ## Pattern Note

            Cache-related payment failures increased 40% YoY across the industry. This incident aligns
            with recurring theme: ephemeral state in distributed cache without graceful degradation path.
            """,
        ),
        (
            "INC-2025-0189-deployment-rollback.md",
            {
                "title": "INC-2025-0189: Bad Deployment Causing Payment Failures",
                "department": "payments",
                "document_type": "incident",
                "access_level": "internal",
                "created_date": "2025-02-03",
                "author": "Release Engineering",
                "tags": ["payment-failure", "deployment", "rollback", "regression"],
            },
            """
            ## Incident Summary

            Release v3.8.2 of `payment-router-service` deployed on 3 February 2025 at 09:00 UTC introduced
            a regression in ISO 8583 message formatting for contactless transactions. POS terminals
            received malformed response codes, interpreted as hard declines. Rollback completed at 09:52 UTC.

            ## Timeline

            - **09:00 UTC** — Canary deployment completed; full rollout at 09:15 UTC.
            - **09:22 UTC** — Contactless decline rate spiked 340% in pilot stores.
            - **09:30 UTC** — SEV-2 incident; deployment freeze enacted.
            - **09:45 UTC** — Root cause traced to field 55 encoding change in commit `a7f3c21`.
            - **09:52 UTC** — Rollback to v3.8.1; decline rate normalized by 10:05 UTC.

            ## Impact

            - **Duration:** 52 minutes of elevated failures
            - **Declined contactless payments:** 4,600
            - **Stores affected:** 1,200 (UK and Ireland)

            ## Root Cause

            Deployment issue: insufficient integration test coverage for contactless EMV path. Staging
            environment used simulated terminals that did not validate binary field encoding. Change
            advisory board approval obtained but payment-specific regression suite not executed due to
            pipeline timeout workaround.

            ## Remediation

            1. Mandatory payment regression suite gate (no skip).
            2. Extended staging with hardware terminal simulator.
            3. Deployment windows restricted for payment-router to 03:00–05:00 UTC.

            ## Recurring Root Cause Category

            Deployment-related payment failures accounted for 22% of payment incidents in 2024. This
            incident adds to pattern documented in quarterly reliability review Q4-2024.
            """,
        ),
        (
            "INC-2025-0311-load-balancer-misconfig.md",
            {
                "title": "INC-2025-0311: Load Balancer Misconfiguration — ACH Payments",
                "department": "payments",
                "document_type": "incident",
                "access_level": "internal",
                "created_date": "2025-03-11",
                "author": "Network Operations",
                "tags": ["payment-failure", "load-balancer", "ach", "network"],
            },
            """
            ## Incident Summary

            On 11 March 2025, a change to F5 load balancer pool weights during datacenter maintenance
            routed 70% of ACH settlement traffic to a single degraded backend node. Batch settlement
            jobs timed out; corporate clients reported delayed payroll transfers. Payment failure in
            this context means settlement could not complete within SLA windows.

            ## Timeline

            - **01:00 UTC** — Planned maintenance window started for DC2 network gear.
            - **01:45 UTC** — ACH batch job failure alerts; 45% of batches in RETRY state.
            - **02:10 UTC** — Load balancer config reviewed; asymmetric routing discovered.
            - **02:35 UTC** — Weights restored; backlog processing initiated.
            - **05:20 UTC** — All batches cleared; SLA breach notifications sent to 12 corporate clients.

            ## Impact

            - **Duration:** 3 hours 35 minutes to clear backlog
            - **Delayed ACH transfers:** USD 840M aggregate value (timing delay only)
            - **SLA breaches:** 12 corporate tier-1 clients

            ## Root Cause

            Load balancer pool member health check interval increased during maintenance script run,
            but weight redistribution logic did not account for one member in soft-degraded state.
            Traffic concentration caused connection exhaustion on single settlement adapter instance—
            related to but distinct from application-level connection pool issues (see INC-2024-0847).

            ## Remediation

            1. Load balancer changes require dual approval for payment pools.
            2. Automated pre-change validation script for pool symmetry.
            3. ACH batch retry logic enhanced with exponential backoff.

            ## Classification

            Payment failure due to infrastructure misconfiguration; logged for annual root cause
            aggregation under "network/routing" category.
            """,
        ),
        (
            "INC-2024-0445-database-lock-contention.md",
            {
                "title": "INC-2024-0445: Database Lock Contention on Settlement DB",
                "department": "payments",
                "document_type": "incident",
                "access_level": "internal",
                "created_date": "2024-05-30",
                "author": "Database Reliability Team",
                "tags": ["payment-failure", "database", "lock", "settlement"],
            },
            """
            ## Incident Summary

            On 30 May 2024, lock contention on the settlement ledger table caused payment posting delays.
            Real-time balance updates for premium banking customers lagged up to 18 minutes. While
            authorizations succeeded, settlement confirmation failures triggered false "payment failed"
            notifications in the mobile app.

            ## Timeline

            - **16:00 UTC** — Lock wait events exceeded threshold on `SETTLEMENT_LEDGER`.
            - **16:22 UTC** — Mobile app push notifications for failed payments spiked (false positives).
            - **17:05 UTC** — Long-running analytics query killed; locks released.
            - **17:18 UTC** — Notification queue drained; balances reconciled.

            ## Impact

            - **Duration:** 1 hour 18 minutes
            - **False failure notifications:** 8,900
            - **Actual unsettled transactions:** 0 (delayed only)

            ## Root Cause

            Ad-hoc analytics query on production settlement DB without read-uncommitted isolation held
            shared locks during peak settlement window. Combined with index rebuild job overlap,
            exclusive lock requests from payment posting service timed out.

            ## Remediation

            Read replicas mandatory for analytics; query governor enforced; index maintenance windows
            aligned with low settlement volume periods.
            """,
        ),
        (
            "INC-2024-0891-atm-dispense-payment-link.md",
            {
                "title": "INC-2024-0891: ATM Network Link to Payment Core Degraded",
                "department": "platform",
                "document_type": "incident",
                "access_level": "internal",
                "created_date": "2024-07-12",
                "author": "ATM Operations",
                "tags": ["payment-failure", "atm", "network", "degradation"],
            },
            """
            ## Incident Summary

            Degraded MPLS link between the ATM switch and payment core caused intermittent authorization
            timeouts at 340 ATM locations across the Midlands region. Cash withdrawal success rate
            dropped to 72% for 4 hours. Card-present payment failures at ATM-attached POS terminals
            were also reported. This incident is classified as a payment failure on the card-present
            channel due to authorization timeout rather than issuer decline.

            ## Timeline

            - **08:10 UTC** — ATM monitoring detected elevated host disconnect rate on MPLS circuit CB-AT M-04.
            - **08:35 UTC** — Carrier confirmed fiber cut near Birmingham exchange; ETA repair 6 hours.
            - **09:00 UTC** — Automatic failover to backup MPLS link; latency increased from 18ms to 890ms.
            - **09:15 UTC** — Payment core ISO 8583 timeout (2.5s) exceeded on 28% of ATM auth requests.
            - **12:20 UTC** — Primary circuit restored; success rate recovered by 12:45 UTC.

            ## Impact

            - **Duration:** 4 hours 35 minutes degraded service
            - **Failed ATM transactions:** 19,400 (withdrawals and balance inquiries)
            - **POS at ATM locations affected:** 85 convenience store terminals

            ## Root Cause

            Primary root cause was carrier fiber cut on primary MPLS path. Contributing factor: backup
            link latency exceeded ISO 8583 timeout budget configured for ATM channel. Failover design
            assumed backup latency under 400ms; actual backup path routed via secondary carrier with
            higher hop count during partial regional outage.

            ## Remediation

            1. ATM channel timeout budget reviewed; adaptive timeout for failover mode (max 4.0s, IC approved).
            2. Secondary carrier diversity contract signed for ATM MPLS pairs.
            3. Quarterly failover drill including latency validation under load.

            ## Related Patterns

            Network degradation as payment failure root cause is distinct from application connection pool
            issues but produces identical customer symptom (declined/timeout). Operations teams should
            verify network path before deep-diving application pools.
            """,
        ),
        (
            "INC-2025-0267-api-rate-limit-cascade.md",
            {
                "title": "INC-2025-0267: Internal API Rate Limit Cascade",
                "department": "platform",
                "document_type": "incident",
                "access_level": "internal",
                "created_date": "2025-02-28",
                "author": "API Platform Team",
                "tags": ["outage", "rate-limit", "cascade", "api"],
            },
            """
            ## Incident Summary

            An aggressive retry storm from the notification service tripped rate limits on the account
            validation service, which the bill pay payment pre-check depends on. Cascading HTTP 429
            responses caused payment pre-check failures for the online bill pay feature between 11:00
            and 13:15 UTC on 28 February 2025. Card payment channels were unaffected; this incident
            targeted ACH and bill pay validation flows.

            ## Timeline

            - **11:02 UTC** — Account service rate limit alerts: client `notif-svc-prod` exceeded 5K req/min quota.
            - **11:18 UTC** — Bill pay failure rate rose to 11%; incident bridge opened as SEV-3.
            - **11:45 UTC** — Engineers identified notification batch replay after Kafka consumer lag recovery.
            - **12:30 UTC** — Notification replay paused; rate limit temporarily raised for account service.
            - **13:15 UTC** — Bill pay failure rate normalized; permanent fixes scheduled.

            ## Impact

            - **Duration:** 2 hours 15 minutes
            - **Failed bill pay initiations:** 3,280
            - **Duplicate notifications sent during replay:** 14,200 (separate customer comms issue)

            ## Root Cause

            Missing jitter on exponential backoff in notification service client caused synchronized
            retry spikes. Shared service account between batch replay and online traffic meant batch
            recovery consumed entire rate limit quota for the account validation API. Payment validation
            calls received 429 and surfaced as generic payment failure to end users.

            ## Remediation

            1. Dedicated OAuth client credentials for batch vs online notification paths.
            2. Client SDK updated to honor `Retry-After` headers with randomized jitter.
            3. Circuit breaker on bill pay → account service with cached read fallback for non-mutating checks.
            4. Rate limit dashboards added to payment ops war room wallboard.

            ## Lessons Learned

            Internal platform rate limits can cause customer-facing payment failures without any payment
            service degradation. Cross-team dependency mapping updated to include account service as
            critical dependency for bill pay channel.
            """,
        ),
        (
            "INC-2024-1120-restricted-fraud-ring-investigation.md",
            {
                "title": "INC-2024-1120: Restricted — Coordinated Fraud Ring Investigation",
                "department": "security",
                "document_type": "incident",
                "access_level": "restricted",
                "created_date": "2024-10-05",
                "author": "Financial Crime Unit",
                "tags": ["restricted", "fraud", "investigation", "payment-failure"],
            },
            """
            ## RESTRICTED — Authorized Personnel Only

            This document details an active investigation into coordinated synthetic identity fraud
            targeting Commercial Bank's instant payment rails. Distribution limited to Financial Crime
            Unit, CISO office, and designated legal counsel.

            ## Summary

            Between September 15 and October 3, 2024, approximately 2,400 instant payment transfers
            were initiated using compromised credentials from third-party data breach. Mule accounts
            identified across 6 jurisdictions. Total attempted outflow: USD 12.4M; recovered USD 11.1M.

            ## Investigation Status

            Law enforcement liaison active. Account closures and SAR filings completed for 890 entities.
            Payment failure patterns in customer-facing channels were intentionally induced during
            containment (risk-based blocks) causing elevated decline rates in affected segments.

            ## Access Control

            Analyst role does NOT include access to this document. Administrator and FCU role required.
            All access logged for audit per POL-COMP-009.

            ## Technical Indicators

            - Unusual velocity on instant payment endpoint
            - Device fingerprint clustering
            - Geo-velocity anomalies on newly enrolled payees

            Do not reference specifics in customer-facing communications or general incident summaries.
            """,
        ),
    ]


def runbook_docs() -> list[tuple[str, dict, str]]:
    return [
        (
            "RB-PAY-001-gateway-failover.md",
            {
                "title": "Runbook: Payment Gateway Failover Procedure",
                "department": "payments",
                "document_type": "runbook",
                "access_level": "internal",
                "created_date": "2024-01-10",
                "author": "Payments SRE",
                "tags": ["runbook", "failover", "gateway", "payments"],
            },
            """
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
            """,
        ),
        (
            "RB-PAY-003-connection-pool-diagnostics.md",
            {
                "title": "Runbook: Connection Pool Diagnostics for Payment Services",
                "department": "payments",
                "document_type": "runbook",
                "access_level": "internal",
                "created_date": "2024-04-02",
                "author": "Payments SRE",
                "tags": ["runbook", "connection-pool", "diagnostics"],
            },
            """
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
            """,
        ),
        (
            "RB-PAY-007-vendor-failover-fraud.md",
            {
                "title": "Runbook: Fraud Vendor Failover",
                "department": "payments",
                "document_type": "runbook",
                "access_level": "internal",
                "created_date": "2024-12-01",
                "author": "Risk Engineering",
                "tags": ["runbook", "vendor", "fraud", "failover"],
            },
            """
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
            """,
        ),
        (
            "RB-OPS-002-incident-severity-classification.md",
            {
                "title": "Runbook: Incident Severity Classification",
                "department": "platform",
                "document_type": "runbook",
                "access_level": "public",
                "created_date": "2023-06-15",
                "author": "Site Reliability Engineering",
                "tags": ["runbook", "incident", "severity", "sev"],
            },
            """
            ## Severity Definitions

            **SEV-1:** Complete loss of critical customer-facing service (payments, account access) or
            regulatory breach. Executive notification within 15 minutes.

            **SEV-2:** Significant degradation (>5% failure rate or >2s p95 latency on critical paths).

            **SEV-3:** Limited impact, workaround available.

            **SEV-4:** Minor issue, next business day resolution acceptable.

            ## Payment-Specific Guidance

            Any payment failure rate exceeding 2% for 10 minutes auto-classifies as minimum SEV-2.
            Contactless or ACH settlement delays affecting corporate SLA auto-SEV-2.

            ## Process

            Incident commander assigns severity within 10 minutes of bridge open. Severity changes
            documented in incident timeline with justification.
            """,
        ),
        (
            "RB-SEC-005-certificate-rotation-payments.md",
            {
                "title": "Runbook: Certificate Rotation for Payment Integrations",
                "department": "security",
                "document_type": "runbook",
                "access_level": "internal",
                "created_date": "2024-10-01",
                "author": "PKI Team",
                "tags": ["runbook", "certificate", "rotation", "payments"],
            },
            """
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
            """,
        ),
        (
            "RB-DATA-001-batch-job-recovery.md",
            {
                "title": "Runbook: Batch Job Failure Recovery",
                "department": "platform",
                "document_type": "runbook",
                "access_level": "internal",
                "created_date": "2024-02-20",
                "author": "Data Platform Team",
                "tags": ["runbook", "batch", "recovery"],
            },
            """
            ## Purpose

            Recover failed batch jobs affecting settlement, reconciliation, or reporting pipelines.

            ## Steps

            1. Identify failed job in Control-M dashboard (job ID prefix `PAY-BATCH`).
            2. Check dependency graph for upstream failures.
            3. Clear idempotency lock if safe: `redis-cli DEL batch:lock:{job_id}`.
            4. Restart from last checkpoint with `-resume` flag.
            5. Validate output record counts against expected ranges.

            ## Payment Impact

            Delayed batch jobs may cause false payment failure notifications—coordinate with mobile team
            if settlement lag exceeds 10 minutes.
            """,
        ),
        (
            "RB-MOB-004-redis-failover-payments.md",
            {
                "title": "Runbook: Redis Failover for Mobile Payment Cache",
                "department": "payments",
                "document_type": "runbook",
                "access_level": "internal",
                "created_date": "2025-01-20",
                "author": "Mobile Platform Team",
                "tags": ["runbook", "redis", "cache", "mobile"],
            },
            """
            ## Purpose

            Respond to Redis cluster failures affecting mobile payment session cache.

            ## Immediate Actions

            1. Confirm split-brain or node failure via Redis `CLUSTER INFO`.
            2. If corruption suspected, flush payment intent namespace ONLY: `redis-cli --cluster call ... FLUSHDB`.
            3. Restart `mobile-payment-api` pods to rebuild session state from authoritative DB.
            4. Enable feature flag `payments.force_db_session` bypassing cache.

            ## Post-Recovery

            Monitor duplicate charge alerts for 24h. Reference INC-2025-0042.
            """,
        ),
        (
            "RB-REL-001-deployment-rollback-payments.md",
            {
                "title": "Runbook: Emergency Rollback — Payment Router",
                "department": "payments",
                "document_type": "runbook",
                "access_level": "internal",
                "created_date": "2025-02-05",
                "author": "Release Engineering",
                "tags": ["runbook", "rollback", "deployment"],
            },
            """
            ## Purpose

            Emergency rollback procedure for `payment-router-service` when post-deploy metrics breach
            thresholds within 30 minutes of rollout.

            ## Rollback Command

            `helm rollback payment-router -n payment-ops 0` (previous revision)

            ## Verification

            - Contactless approval rate within 2% of 7-day baseline
            - ISO 8583 field validation test suite passes (automated, 3 min)

            ## Authority

            On-call may rollback without CAB approval when SEV-2 criteria met.

            See INC-2025-0189 for context.
            """,
        ),
    ]


def architecture_docs() -> list[tuple[str, dict, str]]:
    return [
        (
            "ARCH-PAY-001-platform-overview.md",
            {
                "title": "Payment Platform Architecture Overview",
                "department": "payments",
                "document_type": "architecture",
                "access_level": "internal",
                "created_date": "2024-01-25",
                "author": "Enterprise Architecture",
                "tags": ["architecture", "payments", "overview"],
            },
            """
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
            """,
        ),
        (
            "ARCH-PAY-002-fraud-integration.md",
            {
                "title": "Fraud Scoring Integration Architecture",
                "department": "payments",
                "document_type": "architecture",
                "access_level": "internal",
                "created_date": "2024-12-15",
                "author": "Risk Engineering",
                "tags": ["architecture", "fraud", "integration"],
            },
            """
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
            """,
        ),
        (
            "ARCH-PLAT-003-api-gateway-design.md",
            {
                "title": "Enterprise API Gateway Design",
                "department": "platform",
                "document_type": "architecture",
                "access_level": "internal",
                "created_date": "2023-11-10",
                "author": "Integration Architecture",
                "tags": ["architecture", "api-gateway", "kong"],
            },
            """
            ## Overview

            Kong Gateway deployed as DMZ entry for external and partner APIs. Internal services use
            Istio service mesh for east-west traffic.

            ## Payment Route Configuration

            Routes `/v1/payments/*` enforce mTLS, 100 req/s per client cert, request size limit 64KB.
            Response caching disabled for all mutating payment endpoints.

            ## Observability

            All routes emit OpenTelemetry spans; correlated with LangSmith traces in AI ops assistant pilot.
            """,
        ),
        (
            "ARCH-DATA-004-event-driven-payments.md",
            {
                "title": "Event-Driven Payment Processing",
                "department": "payments",
                "document_type": "architecture",
                "access_level": "internal",
                "created_date": "2024-06-01",
                "author": "Data Architecture",
                "tags": ["architecture", "events", "kafka"],
            },
            """
            ## Pattern

            Payment lifecycle events published to Kafka: `payment.initiated`, `payment.authorized`,
            `payment.settled`, `payment.failed`. Downstream consumers: notifications, analytics,
            regulatory reporting.

            ## Failure Handling

            Dead letter queue `payment.failed.dlq` with 7-day retention. Replays require change ticket.

            ## Consistency

            Outbox pattern on orchestrator ensures at-least-once delivery; consumers must be idempotent.
            """,
        ),
        (
            "ARCH-SEC-005-zero-trust-payments.md",
            {
                "title": "Zero Trust Architecture for Payment Zone",
                "department": "security",
                "document_type": "architecture",
                "access_level": "restricted",
                "created_date": "2024-08-20",
                "author": "Security Architecture",
                "tags": ["architecture", "zero-trust", "restricted"],
            },
            """
            ## RESTRICTED

            Detailed network segmentation for PCI-DSS payment zone. Distribution limited to security
            architecture and payment platform leads.

            ## Zones

            CDE (Cardholder Data Environment) isolated via micro-segmentation. No direct analyst access
            to production CDE tooling without PAM session recording.

            ## Controls

            mTLS everywhere; SPIFFE identities; policy engine OPA for service authorization.

            Analyst and Viewer roles must not receive retrieval results tagged `access_level: restricted`
            from this document's metadata namespace.
            """,
        ),
        (
            "ARCH-DR-006-disaster-recovery-payments.md",
            {
                "title": "Disaster Recovery — Payment Systems",
                "department": "payments",
                "document_type": "architecture",
                "access_level": "internal",
                "created_date": "2024-03-30",
                "author": "Business Continuity",
                "tags": ["architecture", "dr", "bc"],
            },
            """
            ## RTO/RPO Targets

            - Payment gateway: RTO 15 min, RPO 0 (synchronous replication)
            - Settlement batch: RTO 4 hours, RPO 15 min

            ## DR Site

            Secondary region eu-west-2 warm standby. Failover tested quarterly; last test 2024-11-15 PASS.

            ## Runbook Link

            Failover execution: RB-PAY-001. Communication templates in SharePoint BC library.
            """,
        ),
    ]


def policy_docs() -> list[tuple[str, dict, str]]:
    return [
        (
            "POL-HR-001-password-reset.md",
            {
                "title": "Password Reset Policy",
                "department": "security",
                "document_type": "policy",
                "access_level": "public",
                "created_date": "2023-01-15",
                "author": "Information Security",
                "tags": ["policy", "password", "identity"],
            },
            """
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
            """,
        ),
        (
            "POL-SEC-004-incident-notification.md",
            {
                "title": "Security Incident Notification Policy",
                "department": "security",
                "document_type": "policy",
                "access_level": "internal",
                "created_date": "2023-09-01",
                "author": "Chief Information Security Officer",
                "tags": ["policy", "incident", "notification"],
            },
            """
            ## Purpose

            Define escalation and external notification requirements for security and operational incidents.

            ## SEV-1 Notification

            - Executive committee within 15 minutes
            - Regulator notification within 24 hours if customer data or payment availability affected
            - Customer communication within 72 hours for material impact

            ## Payment Incidents

            Payment system unavailability exceeding 30 minutes triggers regulatory reporting assessment
            by Compliance within 4 hours of resolution.
            """,
        ),
        (
            "POL-DATA-002-classification.md",
            {
                "title": "Data Classification Policy",
                "department": "compliance",
                "document_type": "policy",
                "access_level": "public",
                "created_date": "2022-06-01",
                "author": "Data Governance",
                "tags": ["policy", "data", "classification"],
            },
            """
            ## Classification Levels

            **Public** — Marketing materials, published policies
            **Internal** — Operational docs, runbooks, internal architecture
            **Restricted** — Fraud investigations, executive reviews, PCI detailed configs

            ## Handling

            Restricted documents require role-based access in knowledge systems. AI assistant must filter
            retrieval by user role and document `access_level` metadata.

            ## Labeling

            All documents in enterprise knowledge base must include `access_level` in metadata.
            """,
        ),
        (
            "POL-COMP-009-sar-handling.md",
            {
                "title": "Suspicious Activity Report Handling",
                "department": "compliance",
                "document_type": "policy",
                "access_level": "restricted",
                "created_date": "2023-04-12",
                "author": "Financial Crime Compliance",
                "tags": ["policy", "sar", "restricted", "compliance"],
            },
            """
            ## RESTRICTED

            Procedures for filing and storing SARs. Access limited to Financial Crime Unit and Compliance
            officers. AI assistant must not surface SAR details to Viewer or Analyst roles.

            ## Requirements

            SAR drafts encrypted at rest; 5-year retention; no cross-border transfer without legal review.

            ## AI Usage

            Enterprise AI assistant queries logged; restricted content blocked at retrieval layer with
            audit event emitted.
            """,
        ),
        (
            "POL-IT-003-change-management.md",
            {
                "title": "IT Change Management Policy",
                "department": "platform",
                "document_type": "policy",
                "access_level": "internal",
                "created_date": "2022-11-20",
                "author": "IT Governance",
                "tags": ["policy", "change", "cab"],
            },
            """
            ## Standard Changes

            Pre-approved low-risk changes follow automated pipeline. Payment production changes require
            CAB approval except emergency rollback (RB-REL-001).

            ## Emergency Changes

            Allowed during SEV-1/SEV-2 with retrospective CAB within 48 hours. Documented root cause
            for deployment-related incidents (see INC-2025-0189) triggers enhanced review.

            ## Blackout Periods

            Retail payment freeze: December 24–26, major tax deadline days.
            """,
        ),
        (
            "POL-PCI-001-compliance-overview.md",
            {
                "title": "PCI-DSS Compliance Guidelines Overview",
                "department": "compliance",
                "document_type": "policy",
                "access_level": "internal",
                "created_date": "2024-01-05",
                "author": "PCI Program Office",
                "tags": ["policy", "pci", "compliance"],
            },
            """
            ## Scope

            All systems storing, processing, or transmitting cardholder data. Annual QSA assessment due
            each March.

            ## Key Controls

            Network segmentation (ARCH-SEC-005), encryption in transit TLS 1.2+, PAN masking in logs,
            quarterly vulnerability scans.

            ## Incident Linkage

            Certificate expiry and connection pool incidents affecting CDE require PCI incident log entry
            within 24 hours regardless of data exposure outcome.
            """,
        ),
    ]


def product_spec_docs() -> list[tuple[str, dict, str]]:
    return [
        (
            "SPEC-MOB-001-mobile-payments.md",
            {
                "title": "Mobile Banking Payment Feature Specification",
                "department": "payments",
                "document_type": "spec",
                "access_level": "internal",
                "created_date": "2024-05-10",
                "author": "Product Management",
                "tags": ["spec", "mobile", "payments"],
            },
            """
            ## Feature Overview

            Enable P2P transfers, bill pay, and contactless provisioning within mobile app v5.0+.

            ## Requirements

            - Payment completion under 3 seconds p95 on 4G
            - Session recovery after app backgrounding (cache + DB fallback per INC-2025-0042 learnings)
            - Biometric confirmation for transactions >USD 500

            ## Non-Functional

            99.95% availability; graceful degradation message when payment services unavailable.

            ## Dependencies

            mobile-payment-api, Redis session cache, payment-orchestrator, notification service.
            """,
        ),
        (
            "SPEC-PAY-002-realtime-notifications.md",
            {
                "title": "Real-Time Payment Notification Specification",
                "department": "payments",
                "document_type": "spec",
                "access_level": "internal",
                "created_date": "2024-07-22",
                "author": "Product Management",
                "tags": ["spec", "notifications", "realtime"],
            },
            """
            ## Overview

            Push/SMS/email notifications within 5 seconds of payment terminal state change.

            ## Events

            Subscribe to `payment.authorized`, `payment.failed`, `payment.settled` from Kafka.

            ## False Failure Prevention

            Do not emit failure notification until settlement confirmation OR 10-minute timeout
            (addresses INC-2024-0445 false positives).

            ## Rate Limits

            Max 10 notifications per user per hour to prevent alert storms during incidents.
            """,
        ),
        (
            "SPEC-API-003-merchant-portal.md",
            {
                "title": "Merchant Portal API Specification",
                "department": "payments",
                "document_type": "spec",
                "access_level": "internal",
                "created_date": "2024-09-05",
                "author": "API Product Team",
                "tags": ["spec", "api", "merchant"],
            },
            """
            ## Base URL

            `https://api.commercialbank.com/merchant/v2`

            ## Authentication

            OAuth2 client credentials; mTLS for tier-1 merchants.

            ## Endpoints

            - `POST /payments` — Initiate payment
            - `GET /payments/{id}` — Status inquiry
            - `POST /refunds` — Refund processing

            ## Error Codes

            Standard ISO 8583 response code mapping documented in appendix. 504 indicates gateway timeout—
            merchants should retry with idempotency key.
            """,
        ),
        (
            "SPEC-INST-004-instant-payments.md",
            {
                "title": "Instant Payments Rail Integration Spec",
                "department": "payments",
                "document_type": "spec",
                "access_level": "internal",
                "created_date": "2024-11-18",
                "author": "Payments Product",
                "tags": ["spec", "instant-payments", "iso20022"],
            },
            """
            ## Scope

            ISO 20022 instant credit transfer for domestic retail and corporate clients.

            ## SLA

            End-to-end processing under 10 seconds; 99.9% availability target.

            ## Fraud Controls

            Mandatory sync fraud check >USD 500; velocity limits 5 transfers/hour retail.

            ## Incident Reference

            Fraud ring investigation INC-2024-1120 led to enhanced payee cooling period (24h new payees).
            """,
        ),
        (
            "SPEC-AN-005-payment-analytics-dashboard.md",
            {
                "title": "Payment Analytics Dashboard Specification",
                "department": "payments",
                "document_type": "spec",
                "access_level": "internal",
                "created_date": "2025-01-08",
                "author": "Analytics Product",
                "tags": ["spec", "analytics", "dashboard"],
            },
            """
            ## Users

            Analyst role: access to aggregated payment failure metrics, root cause categories, vendor SLA.

            ## Data Sources

            Snowflake `PAYMENTS_FACT`, incident Management API, Grafana snapshots.

            ## Metrics

            - Failure rate by channel
            - Top root cause categories (pool, cert, vendor, cache, deployment)
            - MTTR trend

            Viewer role sees summary only; Analyst sees drill-down; Admin sees raw incident links.
            """,
        ),
    ]


def meeting_notes_docs() -> list[tuple[str, dict, str]]:
    return [
        (
            "MTG-2024-Q4-reliability-review.md",
            {
                "title": "Q4 2024 Payment Reliability Review Meeting Notes",
                "department": "payments",
                "document_type": "meeting_notes",
                "access_level": "internal",
                "created_date": "2024-12-20",
                "author": "VP Engineering",
                "tags": ["meeting", "reliability", "q4"],
            },
            """
            ## Attendees

            VP Engineering, Payments SRE Lead, Risk Officer, Product Director

            ## Summary

            Reviewed 14 payment-related incidents in Q4 2024. Top root cause categories:
            1. Connection pool exhaustion (3 incidents)
            2. Third-party vendor timeouts (2)
            3. Certificate management gaps (2)
            4. Deployment regressions (2)
            5. Cache/Redis failures (1)

            ## Action Items

            - Mandate connection pool review in all payment CAB tickets (Owner: SRE, Due: Jan 2025)
            - Secondary fraud vendor production failover (Owner: Risk Eng, Due: Feb 2025)
            - Certificate inventory automation Phase 2 (Owner: PKI, Due: Mar 2025)

            ## Budget

            Approved USD 400K for payment resilience program 2025.
            """,
        ),
        (
            "MTG-2025-01-pir-payment-outages-jan.md",
            {
                "title": "PIR Meeting: January 2025 Payment Outages",
                "department": "payments",
                "document_type": "meeting_notes",
                "access_level": "internal",
                "created_date": "2025-02-10",
                "author": "Incident Management",
                "tags": ["meeting", "pir", "payment-failure"],
            },
            """
            ## Incidents Reviewed

            - INC-2025-0042 (Redis cache failure)
            - INC-2025-0189 (deployment rollback)

            ## Recurring Themes

            Both incidents highlight insufficient graceful degradation. Mobile cache should not be
            single point of failure; deployment gates must not be skipped.

            ## Customer Impact

            Combined 15,900 failed payment attempts; NPS dip -3 points in affected week.

            ## Decisions

            Adopt idempotency standard enterprise-wide for payment APIs by Q2 2025.
            """,
        ),
        (
            "MTG-2024-09-architecture-review-fraud.md",
            {
                "title": "Architecture Review: Fraud Integration Redesign",
                "department": "payments",
                "document_type": "meeting_notes",
                "access_level": "internal",
                "created_date": "2024-09-30",
                "author": "Enterprise Architecture Board",
                "tags": ["meeting", "architecture", "fraud"],
            },
            """
            ## Context

            Post INC-2024-1566 vendor timeout; board reviewed ARCH-PAY-002 updates.

            ## Approved

            Async fraud path for low-value segment; secondary vendor pilot.

            ## Deferred

            Inline ML model — await feature store maturity.

            ## Next Review

            2025-03-15
            """,
        ),
        (
            "MTG-2025-02-ai-assistant-kickoff.md",
            {
                "title": "Enterprise AI Assistant Project Kickoff",
                "department": "platform",
                "document_type": "meeting_notes",
                "access_level": "internal",
                "created_date": "2025-02-15",
                "author": "Platform Product",
                "tags": ["meeting", "ai", "assistant"],
            },
            """
            ## Objective

            Deploy internal conversational assistant for policies, runbooks, incidents, architecture docs.

            ## Requirements Discussed

            - LangGraph multi-agent orchestration
            - Hybrid search Pinecone + BM25
            - RBAC: Viewer, Analyst, Administrator
            - LangSmith tracing mandatory
            - Prompt injection protection

            ## Data

            Index mock/real internal docs with metadata: department, document_type, access_level.

            ## Timeline

            POC delivery target 2 weeks; demo includes agent activity transparency panel.
            """,
        ),
        (
            "MTG-2024-11-exec-restricted-outage-briefing.md",
            {
                "title": "Executive Briefing: October Payment Security Events",
                "department": "security",
                "document_type": "meeting_notes",
                "access_level": "restricted",
                "created_date": "2024-11-15",
                "author": "Chief Risk Officer",
                "tags": ["meeting", "executive", "restricted"],
            },
            """
            ## RESTRICTED — Executive Committee Only

            Briefing covered INC-2024-1120 fraud ring and associated payment blocks. Board approved
            enhanced monitoring spend. Public messaging deliberately vague ("scheduled maintenance") —
            do not contradict in internal general channels.

            ## AI Assistant Note

            This document must not appear in Viewer/Analyst retrieval results. Admin-only access.
            """,
        ),
        (
            "MTG-2025-03-spring-planning-payments.md",
            {
                "title": "Spring Planning: Payments Platform 2025",
                "department": "payments",
                "document_type": "meeting_notes",
                "access_level": "internal",
                "created_date": "2025-03-05",
                "author": "Engineering Management",
                "tags": ["meeting", "planning", "roadmap"],
            },
            """
            ## Priorities H1 2025

            1. Payment resilience program (pool, cert, vendor, cache, deployment themes)
            2. Instant payments scale to 500K daily
            3. Enterprise AI assistant production pilot for ops teams

            ## Staffing

            Two additional SRE hires for payments; one agentic AI engineer for assistant POC.

            ## Dependencies

            Pinecone index for doc search; LangSmith org account; FastAPI backend delivery.
            """,
        ),
    ]


def generate_all(output_dir: Path | None = None, force: bool = False) -> list[Path]:
    global OUTPUT_DIR
    if output_dir is not None:
        OUTPUT_DIR = output_dir

    folders = ["incidents", "runbooks", "architecture", "policies", "product_specs", "meeting_notes"]
    for folder in folders:
        target = OUTPUT_DIR / folder
        if force and target.exists():
            for f in target.glob("*.md"):
                f.unlink()
        target.mkdir(parents=True, exist_ok=True)

    generators = [
        ("incidents", incident_docs),
        ("runbooks", runbook_docs),
        ("architecture", architecture_docs),
        ("policies", policy_docs),
        ("product_specs", product_spec_docs),
        ("meeting_notes", meeting_notes_docs),
    ]

    written: list[Path] = []
    for folder, gen_fn in generators:
        for filename, meta, body in gen_fn():
            path = write_doc(folder, filename, meta, body)
            written.append(path)

    return written


def print_summary(written: list[Path]) -> None:
    by_folder: dict[str, int] = {}
    restricted = 0
    payment_incidents = 0

    for path in written:
        folder = path.parent.name
        by_folder[folder] = by_folder.get(folder, 0) + 1
        text = path.read_text(encoding="utf-8")
        if "access_level: restricted" in text:
            restricted += 1
        if folder == "incidents" and "payment-failure" in text:
            payment_incidents += 1

    print(f"Generated {len(written)} documents in {OUTPUT_DIR}")
    for folder, count in sorted(by_folder.items()):
        print(f"  {folder}: {count}")
    print(f"  Restricted access docs: {restricted}")
    print(f"  Payment-failure incidents: {payment_incidents}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Commercial Bank mock documents")
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory (default: data/mock_documents)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove existing .md files in target folders before generating",
    )
    args = parser.parse_args()

    written = generate_all(output_dir=args.output, force=args.force)
    print_summary(written)


if __name__ == "__main__":
    main()
