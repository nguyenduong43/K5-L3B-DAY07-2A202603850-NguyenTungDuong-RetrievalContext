"""Dense Retriever connecting Day 6 pgvector database and Gemini Embedding model."""
import json
import os
import urllib.error
import urllib.request
from typing import Any
import psycopg
from dotenv import load_dotenv

load_dotenv()


class PgVectorRetriever:
    """Retriever implementation adhering to starter/agentic.py Retriever protocol."""

    def __init__(
        self,
        database_url: str | None = None,
        api_key: str | None = None,
        model_name: str = "gemini-embedding-001",
        dimensions: int = 768,
        strategy: str = "strategy_b",
    ) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.database_url:
            raise ValueError("DATABASE_URL is missing in .env")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing in .env")

        self.model_name = model_name
        self.dimensions = dimensions
        self.strategy = strategy

    def embed_query(self, query: str) -> list[float]:
        """Generate a 768-dimension embedding vector for the query via Gemini API."""
        normalized_model = (
            self.model_name
            if self.model_name.startswith("models/")
            else f"models/{self.model_name}"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/{normalized_model}:embedContent?key={self.api_key}"
        payload = {
            "model": normalized_model,
            "content": {"parts": [{"text": query}]},
            "taskType": "RETRIEVAL_QUERY",
            "outputDimensionality": self.dimensions,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            vec = data.get("embedding", {}).get("values", [])
            if len(vec) != self.dimensions:
                raise ValueError(
                    f"Expected vector dimensions {self.dimensions}, got {len(vec)}"
                )
            return vec

    def search(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Query pgvector table with cosine similarity and optional metadata filters."""
        if not query.strip():
            return []

        query_vec = self.embed_query(query)

        # Base query with cosine distance <=>
        sql = """
            SELECT 
                chunk_id,
                text,
                document_id AS source_id,
                source,
                page,
                metadata,
                (1 - (embedding <=> %s::vector)) AS score
            FROM chunks
            WHERE strategy = %s
        """
        params: list[Any] = [query_vec, self.strategy]

        # Optional metadata filtering
        if filters:
            if "section" in filters:
                sql += " AND (section = %s OR metadata->>'section' = %s)"
                params.extend([filters["section"], filters["section"]])
            if "page" in filters:
                sql += " AND page = %s"
                params.append(int(filters["page"]))

        sql += " ORDER BY embedding <=> %s::vector LIMIT %s;"
        params.extend([query_vec, top_k])

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        results = []
        for r in rows:
            results.append({
                "id": r[0],
                "text": r[1],
                "source_id": r[2],
                "source": r[3],
                "page": r[4],
                "metadata": r[5] if isinstance(r[5], dict) else json.loads(r[5]),
                "score": float(r[6]),
            })

        return results
