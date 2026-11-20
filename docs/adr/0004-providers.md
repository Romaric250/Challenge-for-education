# Model providers

## Status

Accepted

## Decision

The tutor calls one provider interface. `anthropic` talks to the Anthropic Messages API. `openai_compatible` talks to a `/chat/completions` endpoint, which is how a local model such as Qwen or Llama is attached. `none` refuses generation. `fake` exists only when `APP_ENV=test` and returns a cited sentence from the first source so the citation check can be tested.

An admin can store the active provider and model in `schema_meta`. That overrides the environment for the next lesson turn. Three consecutive provider failures open a 30 second circuit.

Token cost is estimated from a small price table and stored on the assistant message. Unknown models use a conservative default so the column is still filled.

## Consequences

A local model needs an OpenAI-compatible server and `LLM_BASE_URL`. The API does not download weights.
