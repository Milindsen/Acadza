# Acadza Question Care

A report-to-fix workflow for 43 production-format questions and 44 reports.

- Live console: https://milindsen.github.io/Acadza/
- Single narrated walkthrough: https://milindsen.github.io/Acadza/walkthrough.html
- Complete handover: HANDOVER.md (a consolidated PDF is included with the submission email)

## What is implemented

The console groups 44 reports into 39 question cases, prioritizes answer impact, renders sanitized HTML and MathML, shows surgical before/after edits, and supports approve, edit, reject, escalate and close actions. A durable cloud D1 backend stores decisions and audit snapshots in isolated per-browser workspaces. The public frontend is hosted on GitHub Pages; its API is supplied by the existing cloud Worker. This split changes the public URL without removing persistence. A random browser workspace capability is used for the evaluation sandbox; no model API key is exposed to the client. Production faculty SSO is outside this prototype.

All 44 committed judgments are precomputed and assistant-reviewed. The live solver -> triager -> verifier pipeline is implemented, with independent first-solver inputs and deterministic scope guards. It has not been evaluated with a paid API key; control-flow tests use mocks. No hidden ground-truth accuracy score is claimed.

Student identifiers are removed from the public dataset with the applicant's approval. Questions, report IDs, timestamps and comments are retained for evaluation. The original ZIP stays private.

## Run locally

```sh
python server.py
```

Open http://127.0.0.1:8765, set your reviewer name and the token printed at startup. Decisions are saved in work/review.sqlite3. Source JSON files stay unchanged.

```sh
python scripts/build_results.py
python -m unittest discover -s tests -v
node --test tests/worker.test.mjs
```

The JavaScript database tests require Node 22 or newer. Current verification: 25 Python tests and 11 JavaScript tests pass. A real cloud approval and its persistence after reload were also checked through the browser.

## Optional live inference

Configure OPENAI_API_KEY and a model available to your account in OPENAI_MODEL, then:

```sh
python -m engine.run --output results.live.json --workers 2
```

Review all failed, uncertain or disagreeing cases before replacing results.json. Live inference output is deliberately separate from the committed reviewed baseline. Duplicate reports share a question-level solve. Provider credentials and billing must belong to the applicant; no key was configured during this build.

## Hosting and build

GitHub Pages publishes docs/ from main. Run python scripts/build_pages.py to rebuild it. The hosted Worker is bundled with python scripts/build_worker.py. Its .openai/hosting.json declares the existing project ID and DB binding. Schema-only Drizzle migrations live in drizzle/. The Worker applies content and audit in one D1 batch, with optimistic revisions and a nonce-conditioned audit insertion. The local Python alternative uses SQLite transactions. Docker deployment needs a persistent ACADZA_DB volume, HTTPS and a strong REVIEW_TOKEN.

The public demo is separate from Acadza production. Workspaces are isolated by browser capability; changing devices does not automatically share review state. The site should remain accessible through at least 18 November 2026. No advance uptime guarantee or production-scale throughput claim is made.

## Submission contents

results.json, PROMPTS.md, PRODUCT.md, BONUS.md, HANDOVER.md, NARRATION.json, source code, migrations, tests and a personal recording script are included. The single reference video uses synthetic narration, not the applicant's recorded voice. No student replies are sent by the application. See SUBMISSION.md for the four personal answers.
