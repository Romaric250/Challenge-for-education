import hashlib
import math
import re

import httpx

from tutor_api.core.settings import Settings

_TOKEN = re.compile(r"[a-z0-9]+")


def hash_embed(text: str, dimension: int) -> list[float]:
    """Bag-of-tokens embedding used when no embedding API is configured.

    Shared words land in the same dimensions, so cosine similarity tracks
    lexical overlap. It is not the bge-m3 model named in configuration.
    """
    vector = [0.0] * dimension
    for token in _TOKEN.findall(text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


async def embed_texts(texts: list[str], settings: Settings) -> list[list[float]]:
    if settings.embedder == "hashing":
        return [hash_embed(text, settings.embedding_dimension) for text in texts]
    if settings.embedding_base_url is None:
        raise RuntimeError("EMBEDDING_BASE_URL is required")
    headers = {"content-type": "application/json"}
    if settings.embedding_api_key is not None:
        headers["authorization"] = f"Bearer {settings.embedding_api_key.get_secret_value()}"
    payload = {"model": settings.embedding_model, "input": texts}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.embedding_base_url}/embeddings",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        body = response.json()
    rows = body.get("data")
    if not isinstance(rows, list) or len(rows) != len(texts):
        raise RuntimeError("The embedding API returned an unexpected payload.")
    vectors: list[list[float]] = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("embedding"), list):
            raise RuntimeError("The embedding API returned an unexpected payload.")
        vector = [float(value) for value in row["embedding"]]
        if len(vector) != settings.embedding_dimension:
            raise RuntimeError("The embedding width does not match EMBEDDING_DIMENSION.")
        vectors.append(vector)
    return vectors
