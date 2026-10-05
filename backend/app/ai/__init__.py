"""The AI layer: writes explanations and weekly-review text around the plan engine's numbers. It never decides a number.

Boundaries, so the rest of the app never depends on a model:
- The plan engine computes every number in plain Python. This package only writes words from the engine's output, and
  every number in what it writes must be one of the engine's (checks.py); otherwise the template is used.
- It runs only after a plan is built and after each weekly check-in (hooks.py). There is no chat.
- Every call is recorded in the llm_calls table (task, model, tokens, latency, cost, status), with a limit of runs per
  person per week and a monthly spending cap (config.py).
- Book passages for citations come through retrieval.py; the books phase plugs in a real index there.
Modules: config (models, limits), client (the Claude API; faked in tests), prompts, checks, retrieval, tasks, hooks.
"""
