# Hybrid retrieval

## Status

Accepted

## Decision

Each question is searched two ways: cosine distance on the chunk vector, and `tsvector` with the `simple` dictionary so English and Kinyarwanda tokens are not stemmed away. The two lists are fused with reciprocal rank fusion, k = 60.

The relevance gate does not trust the fused score alone, because a nearest-neighbour list always has a top row. A result is used only when a lexical hit exists or the best cosine similarity is at least `RELEVANCE_THRESHOLD` (0.2). Otherwise the tutor refuses and does not call the model.

## Consequences

Keyword questions against the ingested pages answer. Paraphrases that share no words need the bge-m3 embedder before the vector side can carry them.
