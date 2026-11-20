# Embedding model

## Status

Accepted

## Decision

Chunks are stored as 1024-dimension vectors. That width matches `BAAI/bge-m3`, which is the model to use when an OpenAI-compatible embeddings endpoint is configured (`EMBEDDER=openai_compatible`).

When no embedding service is configured, the API uses a hashed bag-of-words vector of the same width. Shared words land in the same dimensions, so cosine similarity follows lexical overlap. It is only a development and offline fallback. Do not describe those vectors as bge-m3.

Changing the width requires a new migration and a re-embed of every chunk. Migration `0001_enable_pgvector` records the width and must not be edited after it has been applied.

## Consequences

Retrieval quality in the default configuration is close to keyword search. The lexical `tsvector` index is what makes the relevance gate trustworthy without bge-m3. A deployment that needs semantic retrieval should point `EMBEDDING_BASE_URL` at an endpoint serving bge-m3.
