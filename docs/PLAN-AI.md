GOAL
Replace every placeholder rule with real values from my books, then switch on the AI layer (Claude API) for the plan explanation and the weekly review. Plan numbers always come from the tested plan engine, never from the AI. There is no chat.

THE BOOKS (in ./Books, private PDFs: never commit them, upload them to the server, or show their text in the app)
1. Upper Lower Strength and Size Program - Jeff Nippard (training program)
2. The Ultimate Guide to Body Recomposition - Jeff Nippard, Chris Barakat (nutrition, training, cardio principles)
3. Intermediate Advanced LPP Program - Jeff Nippard (training program)
4. Fundamentals Hypertrophy Program - Jeff Nippard (training program)
5. Encyclopedia of Foods: A Guide to Healthy Nutrition - Dole, Mayo Clinic, UCLA (food and nutrition reference)
6. Strength Training Anatomy, 2nd ed. - Frederic Delavier (technique and anatomy; mostly illustrations)
7. Diet & Cheat Book 1 (Arabic) - Egyptian recipes
8. Diet & Cheat Nutrition FAQ (Arabic) - nutrition questions and answers for an Egyptian audience: use it for nutrition rules, practical guidance (meal timing, Ramadan, eating out) and Arabic wording, alongside books 2 and 5. Where it disagrees with another book, list the conflict in data/REVIEW.md.
Explain in plain language, stop after each phase so I can review, and commit at the end of every phase. While working, run only the tests related to your change; run the full suite once at the end of each phase.

PHASE A - Read the books
- For each PDF, check whether it has a text layer or is scanned. Extract text with PyMuPDF; OCR scanned pages with Tesseract (Arabic + English). Tell me which books needed OCR and show me samples so I can judge the quality, especially numbers and ingredient amounts in the Arabic recipe book.
- Extract tables (program tables, food tables) separately, keeping their structure.
- Save everything in data/private/ (gitignored: check this before writing). Keep page numbers with all extracted text so later phases can cite them.
- Report per book: pages, text or OCR, tables found, and anything unreadable.

PHASE B - Structured knowledge (the most important phase). Read the books yourself and draft:
- data/rules/*.yaml: real values for every rule (calories and deficits/surpluses, protein/fat/carbs, recomposition, rep ranges, RPE, progression, deloads, warm-up protocols, cool-down, cardio, injury guidance), each with source: book, chapter, page, and a 1–2 sentence summary in your own words. Set placeholder: false only when a book really supports the value. Formulas that aren't from my books stay "Standard formula" with their original source.
- data/programs/*.json: the three Jeff Nippard programs (weeks, days, exercises, sets, reps, RPE, rest, substitution options, warm-up instructions, deload weeks). Extract the exercise demo-video links from the PDFs into video_url. These replace the sample programs.
- Exercise catalogue: every exercise in those programs, tagged with the movement vocabulary, with description, steps, cues and mistakes in your own words (anatomy book as reference) and Free Exercise DB images where available. List exercises still missing an image.
- data/recipes/: the Egyptian recipes from the Arabic book: Arabic and English names, ingredients with grams per serving, food roles, essential ingredients, steps, prep and cook time, fridge life, reheating. Compute macros from the foods table only, and list missing ingredients. These replace the sample recipes.
- Foods table: Egyptian foods and ingredients with per-100 g values from reliable sources (USDA FoodData Central, the Encyclopedia of Foods, Egypt's National Nutrition Institute tables if available), with the source on every row. Generic grocery item mapping, no brands, no prices.
- Put every conflict, unclear number or OCR doubt in data/REVIEW.md for me to decide. Don't resolve them silently.
- Seed everything, rerun the 5 personas, and show me the "Why this plan" counter before and after.

PHASE C - Book search (RAG)
- Chunk the extracted text by headings (~400–800 tokens with overlap), with metadata: book, chapter, page, language, domain (training / nutrition / anatomy / recipes). Store the chunks in the database (PostgreSQL in production, SQLite for tests).
- Implement two retrieval options and compare them in Phase E: (1) pgvector with Voyage AI multilingual embeddings (VOYAGE_API_KEY in .env), (2) PostgreSQL full-text search. Keep the simpler one if it's good enough. Plug the result into the existing Retriever interface in backend/app/ai/retrieval.py.
- Ingestion runs on my PC and uploads only chunks and vectors, never the PDFs.

PHASE D - Switch on the AI layer (Claude API)
- The AI module already exists in backend/app/ai (built with a fake client, off by default). Review and adapt it to this plan instead of rebuilding it: keep the two tasks (plan_explanation, weekly_review), the number check, template fallback, 2 runs per person per week, and the monthly cap.
- Fix: the default model must be "claude-sonnet-5" (it currently says "claude-sonnet-5-5", which doesn't exist), with "claude-haiku-4-5" as the option. Set RATES_PER_MTOK to Sonnet 5: $2 input / $10 output, Haiku 4.5: $1 / $5 per million tokens. Monthly cap default: 8 USD.
- The key is ANTHROPIC_API_KEY in .env (I'll add it myself; never ask me to paste it). Use prompt caching for the system prompt and output schema.
- Tune the prompts with real retrieved passages and citations (book, chapter, page). Retrieval queries are built in code, never from the user's note. Never send photos or whole chapters.
- Run a small real test (a few calls) and show me the actual cost per call.

PHASE E - Evaluation
- 20 synthetic weekly check-ins (good week, stalled lifts, high hunger, rising pain, missed sessions, red flag, Arabic user, Ramadan, etc.): check the right changes, numbers matching the engine, relevant citations, and the safe message for red flags. Compare the two retrieval options. Show me a results table and the AI cost per review.
- 15 citation spot-checks: the claim, book, page and the actual text from data/private/, so I can verify them against the PDFs.
- Rerun the 5 personas and show their "Why this plan" pages: the goal is almost every rule from my books.
