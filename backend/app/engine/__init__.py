"""The plan engine: every number in a plan comes from here, from deterministic, tested Python. Never from an LLM.

- rules.py      loads data/rules/*.yaml (each rule has a source and a one-line explanation in English and Arabic)
- nutrition.py  calories, protein, fat, carbs, with safety bounds
- injuries.py   which exercises an injury rules out, load reductions, red flags
- training.py   choose a program template, adapt it to equipment and injuries, starting weights
- meals.py      pick recipes and portions with an optimizer (scipy MILP)
- grocery.py    weekly / monthly grocery lists and the WhatsApp text
- checkin.py    the weekly check-in questions (data/checkin_questions.yaml) and answer checks
- review.py     the weekly review: small, bounded changes from the check-in, logs and weight trend

The functions here take plain inputs (types.py) and return plain results, so they're easy to test.
backend/app/plans.py reads the database, calls them, and saves the plan. The LLM (next session) only writes
explanations and weekly-review text from these results.
"""
