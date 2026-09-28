"""Reserved for the local LLM + RAG layer (next session).

Boundaries, so the rest of the app never depends on a model:
- The plan engine computes every number in plain Python. This package only
  writes explanations and weekly-review text from the engine's output.
- It runs only after onboarding and after each weekly check-in. There is no chat.
- Every call is recorded in the llm_calls table (task, model, tokens, latency, cost).
- Book passages (from books/, never committed) are indexed here for citations.
"""
