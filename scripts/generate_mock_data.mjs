#!/usr/bin/env node
/**
 * Fallback runner: parses scripts/generate_mock_data.py and writes markdown files.
 * Use when Python is unavailable: node scripts/generate_mock_data.mjs [--force]
 */
import { readFileSync, writeFileSync, mkdirSync, unlinkSync, readdirSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const OUTPUT_DIR = join(ROOT, "data", "mock_documents");
const PYTHON_SOURCE = join(__dirname, "generate_mock_data.py");

const FOLDERS = [
  "incidents",
  "runbooks",
  "architecture",
  "policies",
  "product_specs",
  "meeting_notes",
];

function frontmatter(meta) {
  const tags = meta.tags || [];
  return `---
title: ${meta.title}
department: ${meta.department}
document_type: ${meta.document_type}
access_level: ${meta.access_level}
created_date: ${meta.created_date}
author: ${meta.author}
tags: [${tags.join(", ")}]
---
`;
}

function dedent(text) {
  const lines = text.split("\n");
  const nonEmpty = lines.filter((l) => l.trim().length > 0);
  if (nonEmpty.length === 0) return "";
  const minIndent = Math.min(
    ...nonEmpty.map((l) => l.match(/^(\s*)/)[1].length)
  );
  return lines.map((l) => (l.trim() ? l.slice(minIndent) : "")).join("\n").trim();
}

function expandDocument(body, meta, minWords = 320) {
  const words = body.split(/\s+/).filter(Boolean);
  if (words.length >= minWords) return body;

  const department = meta.department || "platform";
  const docType = (meta.document_type || "document").replace(/_/g, " ");
  const title = meta.title || "Untitled";
  const created = meta.created_date || "2024-01-01";
  const author = meta.author || "Document Owner";
  const tags = (meta.tags || []).join(", ");

  const sections = [
    `## Document Governance\n\n"${title}" is an official Commercial Bank ${docType} owned by the ${department} organization. This record is indexed in the enterprise knowledge base with metadata tags: ${tags}. Document custodians must propose updates via the standard review workflow before modifying controlled sections that affect production systems.`,
    `## Operational Context\n\nTeams supporting payment channels rely on this ${docType} during daily operations, incident bridges, and regulatory examinations. When referenced by the enterprise AI assistant, retrieved excerpts must include attribution to this source file and creation date ${created}. Cross-functional stakeholders in payments, platform engineering, security, and compliance may consume summaries based on RBAC access level.`,
    `## Systems and Integration Landscape\n\nCommercial Bank operates a hub-and-spoke payment architecture. Core services include payment-gateway-prod, payment-router-service, card-auth-service, settlement-batch-engine, and fraud-scoring-adapter. Infrastructure dependencies span Redis session cache, Kafka event bus, F5 load balancers, and dual-region DR in eu-west-2. Changes impacting any dependency require CAB approval except emergency rollback scenarios.`,
    `## Monitoring and Escalation\n\nOperational metrics for payment health are published on Grafana dashboards PAY-GW-001, POOL-ACTIVE, and vendor SLA boards. PagerDuty rotation PAY-ONCALL receives automated alerts when failure rates exceed thresholds defined in RB-OPS-002. Incident commanders should preserve timeline accuracy, customer impact estimates, and root cause category for quarterly reliability aggregation.`,
    `## Compliance and Retention\n\nContent classification follows POL-DATA-002. Handling requirements differ for public, internal, and restricted access levels. PCI-DSS controls apply when documents reference cardholder data environments. Retention: seven years for operational records, ten years when regulatory reporting is implicated. Access to restricted variants requires administrator or designated compliance roles.`,
    `## Revision History and Contacts\n\n| Version | Date | Author | Change Summary |\n|---------|------|--------|----------------|\n| 1.0 | ${created} | ${author} | Initial controlled publication |\n\nDocument feedback: #${department}-ops Slack or ${department}-docs@commercialbank.internal. For after-hours payment escalation, invoke RB-OPS-002 severity classification and open a ServiceNow incident.`,
  ];

  let expanded = body;
  let idx = 0;
  while (expanded.split(/\s+/).filter(Boolean).length < minWords && idx < 12) {
    expanded += "\n\n" + sections[idx % sections.length];
    idx++;
  }
  return expanded;
}

function parsePythonDocs(source) {
  const docs = [];
  const tupleRegex =
    /\(\s*\n\s*"([^"]+\.md)"\s*,\s*\{([\s\S]*?)\}\s*,\s*"""\s*\n([\s\S]*?)"""\s*,?\s*\n\s*\)/g;

  let match;
  while ((match = tupleRegex.exec(source)) !== null) {
    const filename = match[1];
    const metaBlock = match[2];

    const meta = {};
    for (const line of metaBlock.split("\n")) {
      const m = line.match(/^\s*"(\w+)":\s*(.+?),?\s*$/);
      if (!m) continue;
      const key = m[1];
      let val = m[2].trim();
      if (val.startsWith('"') && val.endsWith('"')) {
        meta[key] = val.slice(1, -1);
      } else if (val.startsWith("[")) {
        meta[key] = [...val.matchAll(/"([^"]+)"/g)].map((x) => x[1]);
      }
    }

    const body = expandDocument(dedent(match[3]), meta);
    docs.push({ filename, meta, body });
  }
  return docs;
}

function folderForFilename(filename) {
  if (filename.startsWith("INC-")) return "incidents";
  if (filename.startsWith("RB-")) return "runbooks";
  if (filename.startsWith("ARCH-")) return "architecture";
  if (filename.startsWith("POL-")) return "policies";
  if (filename.startsWith("SPEC-")) return "product_specs";
  if (filename.startsWith("MTG-")) return "meeting_notes";
  throw new Error(`Unknown folder for ${filename}`);
}

function generate(force = false) {
  const source = readFileSync(PYTHON_SOURCE, "utf8");
  const docs = parsePythonDocs(source);

  if (docs.length === 0) {
    throw new Error("No documents parsed from generate_mock_data.py");
  }

  for (const folder of FOLDERS) {
    const dir = join(OUTPUT_DIR, folder);
    mkdirSync(dir, { recursive: true });
    if (force) {
      for (const f of readdirSync(dir)) {
        if (f.endsWith(".md")) unlinkSync(join(dir, f));
      }
    }
  }

  const written = [];
  for (const doc of docs) {
    const folder = folderForFilename(doc.filename);
    const path = join(OUTPUT_DIR, folder, doc.filename);
    const content = frontmatter(doc.meta) + "\n" + doc.body + "\n";
    writeFileSync(path, content, "utf8");
    written.push(path);
  }
  return written;
}

function summary(written) {
  const byFolder = {};
  let restricted = 0;
  let paymentIncidents = 0;

  for (const path of written) {
    const folder = path.split(/[/\\]/).slice(-2, -1)[0];
    byFolder[folder] = (byFolder[folder] || 0) + 1;
    const text = readFileSync(path, "utf8");
    if (text.includes("access_level: restricted")) restricted++;
    if (folder === "incidents" && text.includes("payment-failure")) paymentIncidents++;
  }

  console.log(`Generated ${written.length} documents in ${OUTPUT_DIR}`);
  for (const [folder, count] of Object.entries(byFolder).sort()) {
    console.log(`  ${folder}: ${count}`);
  }
  console.log(`  Restricted access docs: ${restricted}`);
  console.log(`  Payment-failure incidents: ${paymentIncidents}`);
}

const force = process.argv.includes("--force");
const written = generate(force);
summary(written);
