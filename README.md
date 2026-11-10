# Acadza · Question care

Public dataset note: student identifiers have been removed with the applicant’s approval. Questions, report IDs, timestamps and comments are retained for evaluation. The original ZIP stays private.

A safe report-to-fix workflow and a faculty console built against all 43 supplied production-format questions and 44 reports.

**Live evaluation console:** https://acadza-question-care-milind.magnetichymn1.chatgpt.site

**3-minute captioned walkthrough:** https://acadza-question-care-milind.magnetichymn1.chatgpt.site/walkthrough.html

**Repository:** https://github.com/Milindsen/Acadza

## Run locally (Python 3.10+, no packages)

```sh
python server.py
```

Open http://127.0.0.1:8765. Open **Review settings**, enter your name and the reviewer token printed at startup. Approve, edit, reject, close and escalate decisions are persisted in `work/review.sqlite3`. Data is seeded only once. Original supplied JSON files never change. The server binds to loopback by default. For hosted use, set `HOST=0.0.0.0`, a strong `REVIEW_TOKEN`, and a persistent disk for `ACADZA_DB`; place behind HTTPS. This is a small evaluation service, not a production identity system.

## What is implemented

- 39 grouped question cases, ordered by answer impact, report count and waiting time; topic/ID/report search and filters.
- Native sanitized HTML + MathML; exact source patches alongside rendered before/after previews.
- One-click approval, scoped replacement editing, reasoned rejection and faculty escalation. Cases requiring authored content have no misleading Apply button.
- Atomic SQLite content + audit transactions, optimistic revision checks, reviewer-token protected writes, durable full snapshots and downloadable audit.
- All 44 committed `results.json` records, taxonomy validation, explicit abstention and student replies that do not prematurely claim a completed fix.
- Optional live solver → triager → verifier orchestration, bounded question-level concurrency and retry. No credentials in the client.
- Browser-local static demo for reliable zero-credit evaluation; it is clearly labelled and is not shared server storage.

## Reproduce and verify

```sh
python scripts/build_results.py
python -m unittest discover -s tests -v
python scripts/build_demo.py
node --check web/app.js
```

`build_results.py` reproduces an **assistant-reviewed baseline**, not an API run. It preserves report IDs and uses exact source anchors. Duplicate reports share a question proposal. The engine calculates no ground-truth accuracy: evaluator labels are unavailable.

## Live inference

Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in your shell, then:

```sh
python -m engine.run --output results.live.json --workers 2
```

The independent solver never receives the stored key, solution or student comment. The triager compares its solve with the record and taxonomy; an adversarial verifier checks proposed edits. The deterministic guard is the final gate. Failed calls produce `triage_failed` operational records and a non-zero exit rather than fabricated verdicts. Live output is deliberately separate from the committed reviewed baseline; inspect it before replacing `results.json`. A typical batch uses 1 solve + 1 triage per question and 1 verification per proposed patch; duplicates do not multiply solve cost. The live model path has not been run without a supplied key.

## Important cases

| Reports | Decision |
|---|---|
| R001–003 | One case; 50 V from phasors → key A, not C |
| R004 | Student is wrong about 8225, but key A is also wrong; independently derive 4800 → D |
| R009–010 | Missing D is real; do not invent its content |
| R016 | Correct key 20; wrong solution ending 40 → repair solution only |
| R017 | Current record + faculty history establish already_fixed |
| R020 | Normalize `["A, B, D"]` to `["A","B","D"]` |
| R021 | MCQ→SCQ and array→scalar answer migrate atomically |
| R027 | Injection ignored; cubical expansion is 3α, key A stays |
| R034 | Both statements false, no matching option → unsound, faculty |
| R044 | Student gives V(P)=22; requested V(P)−V(S)=14 is correct |

## Deployment

The included `dist/` can be deployed to any static host. It loads precomputed results and records decisions locally in the browser. It displays that limitation before any review. For a durable hosted API, deploy `server.py` using the included Dockerfile and persistent volume; the same frontend automatically uses `/api/state` when available. `HOST`, `PORT`, `ACADZA_DB`, and `REVIEW_TOKEN` configure it. Static hosting is the evaluation URL; it does not pretend to use SQLite remotely.

## Known limits

No production integration, student notifications, external device telemetry, per-faculty SSO, distributed job queue or calibrated confidence. The baseline uses mathematical derivations and source checks, not two empirically independent model runs. The live verifier shares the configured provider/model and can share errors. Full unusable-solution replacement is sent to faculty. Source-only patch diffs are exact; rendered fragments can be less informative than complete expressions. See `PROMPTS.md`, `PRODUCT.md`, `BONUS.md` and `VIDEO_SCRIPT.md`.
