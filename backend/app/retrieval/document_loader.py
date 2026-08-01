"""Load and chunk markdown documents with YAML frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Folder name → Pinecone namespace
FOLDER_TO_NAMESPACE = {
    "incidents": "incidents",
    "runbooks": "runbooks",
    "architecture": "architecture",
    "policies": "policies",
    "product_specs": "product_specs",
    "meeting_notes": "meeting_notes",
}


@dataclass
class DocumentChunk:
    """A single chunk ready for embedding and indexing."""

    chunk_id: str
    text: str
    namespace: str
    metadata: dict[str, Any] = field(default_factory=dict)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter and markdown body."""
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content.strip()

    raw_fm = match.group(1)
    body = content[match.end() :].strip()

    # Line-based parser avoids YAML errors when titles contain colons (e.g. "INC-2024-0847: ...")
    frontmatter: dict[str, Any] = {}
    for line in raw_fm.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            frontmatter[key] = [
                item.strip().strip('"').strip("'")
                for item in value[1:-1].split(",")
                if item.strip()
            ]
        else:
            frontmatter[key] = value.strip('"').strip("'")

    return frontmatter, body


def _split_by_headings(body: str) -> list[tuple[str, str]]:
    """Split body into (heading, section_text) pairs."""
    sections: list[tuple[str, str]] = []
    current_heading = "Introduction"
    current_lines: list[str] = []

    for line in body.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    return [(h, t) for h, t in sections if t.strip()]


def _split_by_tokens(
    text: str,
    encoding,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    """Split long text into token-bounded chunks with overlap."""
    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_text = encoding.decode(tokens[start:end]).strip()
        if chunk_text:
            chunks.append(chunk_text)
        if end >= len(tokens):
            break
        start = max(0, end - overlap_tokens)

    return chunks


def chunk_document(
    frontmatter: dict[str, Any],
    body: str,
    source_file: str,
    namespace: str,
    encoding,
    max_tokens: int = 800,
    overlap_tokens: int = 100,
) -> list[DocumentChunk]:
    """Chunk a document into embedding-ready pieces with metadata."""
    sections = _split_by_headings(body)
    if not sections:
        sections = [("Document", body)]

    raw_chunks: list[tuple[str, str]] = []
    for heading, section_text in sections:
        for part in _split_by_tokens(section_text, encoding, max_tokens, overlap_tokens):
            raw_chunks.append((heading, part))

    title = frontmatter.get("title", source_file)
    tags = frontmatter.get("tags", [])
    if isinstance(tags, list):
        tags_str = ", ".join(str(t) for t in tags)
    else:
        tags_str = str(tags)

    chunks: list[DocumentChunk] = []
    for idx, (heading, chunk_text) in enumerate(raw_chunks):
        chunk_id = f"{source_file}::chunk_{idx}"
        enriched_text = f"# {title}\n## {heading}\n\n{chunk_text}"
        metadata = {
            "title": title,
            "department": frontmatter.get("department", "unknown"),
            "document_type": frontmatter.get("document_type", "unknown"),
            "access_level": frontmatter.get("access_level", "internal"),
            "created_date": str(frontmatter.get("created_date", "")),
            "author": frontmatter.get("author", ""),
            "tags": tags_str,
            "source_file": source_file,
            "chunk_id": chunk_id,
            "section_heading": heading,
            "chunk_index": idx,
            "text": enriched_text[:1000],  # preview for attribution in Pinecone metadata
        }
        chunks.append(
            DocumentChunk(
                chunk_id=chunk_id,
                text=enriched_text,
                namespace=namespace,
                metadata=metadata,
            )
        )

    return chunks


def load_documents(docs_root: Path) -> list[DocumentChunk]:
    """Load all markdown documents under docs_root and return chunks."""
    import tiktoken

    encoding = tiktoken.get_encoding("cl100k_base")
    all_chunks: list[DocumentChunk] = []

    for md_path in sorted(docs_root.rglob("*.md")):
        relative = md_path.relative_to(docs_root)
        folder = relative.parts[0] if len(relative.parts) > 1 else "default"
        namespace = FOLDER_TO_NAMESPACE.get(folder, folder)
        source_file = str(relative).replace("\\", "/")

        content = md_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)
        chunks = chunk_document(
            frontmatter=frontmatter,
            body=body,
            source_file=source_file,
            namespace=namespace,
            encoding=encoding,
        )
        all_chunks.extend(chunks)

    return all_chunks
