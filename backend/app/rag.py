import asyncio
import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings
from app.database import fetch_rows

logger = logging.getLogger(__name__)

ACCESS_LEVEL_RANK = {"EMPLOYEE": 0, "MANAGER": 1, "IT_AGENT": 2, "IT_ADMIN": 3, "SECURITY_ADMIN": 4}

EMPLOYEE_ROLE_QUERY = """
SELECT e.role
FROM itsupport.employees e
WHERE e.employee_code = :employee_code AND e.status = 'ACTIVE'
LIMIT 1
"""

KNOWLEDGE_SEARCH_QUERY = """
SELECT d.document_key AS document_id, d.title, d.category, d.access_level, c.chunk_index, c.content,
       (1 - (c.embedding <=> CAST(:query_embedding AS vector)))::float AS score
FROM itsupport.knowledge_chunks c
JOIN itsupport.knowledge_documents d ON d.id = c.document_id
WHERE d.access_rank <= :access_rank
ORDER BY c.embedding <=> CAST(:query_embedding AS vector)
LIMIT :result_limit
"""


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load the local sentence-transformers model once and reuse it for ingest and retrieval."""
    return SentenceTransformer(settings.embedding_model_name, device=settings.embedding_device)


async def search_knowledge(query: str, employee_code: str) -> list[dict]:
    """Return the highest-scoring knowledge chunks the employee is allowed to read, or an empty list."""
    try:
        employees = await fetch_rows(EMPLOYEE_ROLE_QUERY, {"employee_code": employee_code})
        access_rank = ACCESS_LEVEL_RANK.get((employees[0]["role"] if employees else "EMPLOYEE") or "EMPLOYEE", 0)
        embedding_model = get_embedding_model()
        query_embedding = await asyncio.to_thread(embedding_model.encode, query, normalize_embeddings=True)
        query_vector = "[" + ",".join(str(float(value)) for value in query_embedding.tolist()) + "]"
        rows = await fetch_rows(KNOWLEDGE_SEARCH_QUERY, {"query_embedding": query_vector, "access_rank": access_rank, "result_limit": settings.rag_top_k * 3})
        return [row for row in rows if row["score"] >= settings.rag_min_score][: settings.rag_top_k]
    except Exception:
        logger.exception("Knowledge search failed for employee %s", employee_code)
        return []
