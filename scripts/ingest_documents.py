import asyncio
import hashlib
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
BACKEND_DIRECTORY = ROOT_DIRECTORY / "backend"
KNOWLEDGE_DIRECTORY = ROOT_DIRECTORY / "knowledge"
sys.path.insert(0, str(BACKEND_DIRECTORY))
os.chdir(BACKEND_DIRECTORY)

from app.config import settings
from app.database import engine, execute_write, fetch_rows
from app.rag import ACCESS_LEVEL_RANK, get_embedding_model

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ingest_documents")


UPSERT_DOCUMENT_QUERY = """
INSERT INTO itsupport.knowledge_documents (document_key, company_id,title, category, department, version, effective_date, source, access_level, access_rank, file_path, content_hash, embedding_model, updated_at)
VALUES (:document_key,:company_id,:title, :category, :department, :version, :effective_date, :source, :access_level, :access_rank, :file_path, :content_hash, :embedding_model, NOW())
ON CONFLICT (document_key) DO UPDATE SET
    company_id=EXCLUDED.company_id, title = EXCLUDED.title, category = EXCLUDED.category, department = EXCLUDED.department, version = EXCLUDED.version,
    effective_date = EXCLUDED.effective_date, source = EXCLUDED.source, access_level = EXCLUDED.access_level, access_rank = EXCLUDED.access_rank,
    file_path = EXCLUDED.file_path, content_hash = EXCLUDED.content_hash, embedding_model = EXCLUDED.embedding_model, updated_at = NOW()
RETURNING id, content_hash, embedding_model
"""

EXISTING_DOCUMENT_QUERY = """
SELECT id, content_hash, embedding_model
FROM itsupport.knowledge_documents
WHERE document_key = :document_key
"""

DELETE_CHUNKS_QUERY = """
DELETE FROM itsupport.knowledge_chunks WHERE document_id = :document_id
"""

INSERT_CHUNK_QUERY = """
INSERT INTO itsupport.knowledge_chunks (document_id, chunk_index, content, embedding, metadata, content_hash)
VALUES (:document_id, :chunk_index, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash)
"""


class DocumentFrontMatter(BaseModel):
    """Required header on every knowledge markdown file."""

    document_id: str = Field(min_length=3, max_length=64)
    title: str = Field(min_length=3, max_length=255)
    category: str = Field(min_length=2, max_length=64)
    department: str = Field(min_length=2, max_length=128)
    version: str = Field(min_length=1, max_length=32)
    access_level: Literal["EMPLOYEE", "MANAGER", "IT_AGENT", "IT_ADMIN", "SECURITY_ADMIN"]
    effective_date: date
    source: str = Field(min_length=3, max_length=255)


def parse_front_matter(raw_text: str) -> tuple[DocumentFrontMatter, str]:
    """Split a markdown file into validated front-matter and the article body."""
    if not raw_text.startswith("---"):
        raise ValueError("Knowledge file must start with YAML front-matter between --- lines")
    _, header, body = raw_text.split("---", 2)
    fields: dict[str, str] = {}
    for line in header.strip().splitlines():
        if ":" not in line:
            raise ValueError(f"Front-matter line is not key: value — {line}")
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return DocumentFrontMatter.model_validate(fields), body.strip()


def split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split article text on paragraphs into overlapping character windows of about 500–800 tokens."""
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= chunk_size:
            overlap_text = current[-overlap:] if overlap and current else ""
            current = f"{overlap_text}\n\n{paragraph}".strip() if overlap_text else paragraph
            continue
        start = 0
        while start < len(paragraph):
            chunks.append(paragraph[start:start + chunk_size])
            start += max(chunk_size - overlap, 1)
        current = ""
    if current:
        chunks.append(current)
    return chunks


def format_embedding(values) -> str:
    """Turn a numpy embedding into the [0.1,0.2] text pgvector accepts."""
    return "[" + ",".join(str(float(value)) for value in values.tolist()) + "]"



async def ingest_documents() -> None:
    """Embed every knowledge markdown file and upsert it; unchanged files are skipped."""
    try:
        embedding_model = get_embedding_model()
        markdown_files = sorted(KNOWLEDGE_DIRECTORY.glob("*.md"))
        if not markdown_files:
            raise FileNotFoundError(f"No markdown files found in {KNOWLEDGE_DIRECTORY}")

        ingested = 0
        skipped = 0
        for markdown_file in markdown_files:
            front_matter, body = parse_front_matter(markdown_file.read_text(encoding="utf-8"))
            content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            existing_rows = await fetch_rows(EXISTING_DOCUMENT_QUERY, {"document_key": front_matter.document_id})
            if existing_rows and existing_rows[0]["content_hash"] == content_hash and existing_rows[0]["embedding_model"] == settings.embedding_model_name:
                logger.info("Unchanged, skipping %s", front_matter.document_id)
                skipped += 1
                continue

            chunks = split_into_chunks(body, settings.rag_chunk_size_chars, settings.rag_chunk_overlap_chars)
            embeddings = embedding_model.encode(chunks, normalize_embeddings=True)
            document_row = await execute_write(UPSERT_DOCUMENT_QUERY, {
                "company_id":1,
                "document_key": front_matter.document_id,
                "title": front_matter.title,
                "category": front_matter.category,
                "department": front_matter.department,
                "version": front_matter.version,
                "effective_date": front_matter.effective_date,
                "source": front_matter.source,
                "access_level": front_matter.access_level,
                "access_rank": ACCESS_LEVEL_RANK[front_matter.access_level],
                "file_path": str(markdown_file.relative_to(ROOT_DIRECTORY)).replace("\\", "/"),
                "content_hash": content_hash,
                "embedding_model": settings.embedding_model_name,
            })
            await execute_write(DELETE_CHUNKS_QUERY, {"document_id": document_row["id"]})
            for chunk_index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                await execute_write(INSERT_CHUNK_QUERY, {
                    "document_id": document_row["id"],
                    "chunk_index": chunk_index,
                    "content": chunk,
                    "embedding": format_embedding(embedding),
                    "metadata": json.dumps({"document_id": front_matter.document_id, "category": front_matter.category}),
                    "content_hash": hashlib.sha256(chunk.encode("utf-8")).hexdigest(),
                })
            logger.info("Ingested %s (%d chunks)", front_matter.document_id, len(chunks))
            ingested += 1

        logger.info("Ingest finished: %d updated, %d unchanged, model=%s", ingested, skipped, settings.embedding_model_name)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest_documents())
