# DwellingOS

## Engineering overview

DwellingOS is a source-backed rental-law decision pipeline for the RealPage Rental Housing Law Navigator challenge. It audits the supplied corpus, extracts evidence-linked rule candidates, gates publication on review, and evaluates jurisdiction, effective date and property coverage deterministically. Each result retains a source, quotation and explicit reason when coverage cannot be established. An LLM does not make the final applicability decision.

**[Architecture and failure policy](docs/architecture.md)** · **[Judge verification guide](docs/judge-guide.md)** · **[Measured scale path](docs/scale-architecture.md)** · **[Live product](https://dwelling.hovhannes.dev/)**

| Stage | Implementation | Checkable artifact |
| --- | --- | --- |
| Corpus audit and extraction | `scripts/audit_corpus.py`, `scripts/extract_rules.py`, `engine/law_intake.py` | `output/corpus_audit.json`, `output/rules.json`, candidate/rejection queues |
| Address and date decisions | `engine/portfolio.py`, `engine/evaluator.py`, `scripts/build_outputs.py` | 500 passports and `output/lookups.json` |
| Law-change impact | `engine/change_tracker.py` | `output/changes.json`, five supplied scenarios |
| New-source review and larger portfolios | `engine/source_monitor.py`, `scripts/intake_law.py`, `scripts/approve_candidate.py`, `scripts/portfolio_cli.py` | Review-gated intake and indexed SQLite assessment |
| Regression and release gates | `tests/`, `quality/`, `scripts/release_check.py` | Unit, holdout, reference and output-contract results |

The decision path is **source text → evidence-linked candidate → review gate → jurisdiction/date/coverage evaluator → cited passport**. Unfamiliar source text cannot silently become an operative law: a reviewer must confirm legal force, dates, coverage and citation. Missing property evidence produces `unknown`, not a guessed answer. The 500-property public site is a precomputed demonstration; a separate local server exposes an operator workbench for new-property import and law-source preview.

## Reproduce from a clean checkout

Requires Python 3 and Node.js/npm. The starter pack is bundled; the core pipeline needs no API key or machine-specific path.

```bash
git clone https://github.com/hhovhan/dwellingos.git
cd dwellingos
npm run pipeline       # audit, extract, evaluate, test and validate outputs
npm run build:static   # create deployable dist/ with 500 chunked passports
npm start              # local product and operator workbench at http://127.0.0.1:4173
```

The repository is public and clones without authentication. Competition outputs are `output/rules.json`, `output/lookups.json` and `output/changes.json`. The pipeline and static build have also been run successfully in a fresh local clone.

## Verified scope and limits

The current build processes **500/500** supplied properties into **5,419** rule evaluations, emits **57** evidence-linked candidate rules, and passes **47** automated tests, **9/9** targeted extraction checks, **11/11** targeted address checks and **20/20** non-attorney reference decisions. All *emitted* rules have a source URL, citation and verbatim quotation. These checks do not measure full-corpus extraction recall or predict the organizer's private score. [Holdout method](docs/holdout-evaluation.md) · [Method note and evidence backlog](docs/method-note.md).

The 87-entry source manifest contains 54 captured texts and 33 link-only records. Of the 57 emitted rules, 53 come from supplied captured texts and four from independently checked supplements; supplements are **not** claimed as supplied-corpus citation credit. Baseline extraction largely uses document-specific review profiles. Generic intake proposes candidates from unfamiliar text, but never auto-publishes them. No attorney has certified the rules.

Address and building evidence is incomplete: 383 single Census address-range matches, 117 unresolved or ambiguous matches, 27 ZIP/state-prefix conflicts and 462 provisional postal-city assignments. A Census address-range match is **not** parcel-level municipal-boundary proof. Missing unit counts, construction years, owner type and occupancy evidence remain explicit.

The indexed portfolio path imported **20 million synthetic rows** in 133.488 seconds and assessed 2 million city candidates against one rule in 25.927 seconds on this machine. This demonstrates bounded-memory import and indexed evaluation at that row count—not verified law coverage, fresh facts for 20 million real homes, concurrent production reliability or a deployable RealPage integration. [Benchmark details](docs/scale-architecture.md).

## Product demonstration

**[Open DwellingOS](https://dwelling.hovhannes.dev/)** to search one of the 500 supplied properties, compare rules across dates and inspect the five supplied change scenarios. The [judge guide](docs/judge-guide.md) gives expected observations and the corresponding code/output artifacts, without a rehearsed narration script.

![Live DwellingOS passport for a Newark sample property: a conditional 4% rent rule, its source, and the next fact to verify](docs/assets/newark-passport.png)

*Live capture, not a mockup. The 4% figure is conditional on legal coverage; the sample property has not been certified as covered.*

The public website is static and precomputed. The local operator workbench for new properties and law-source previews is **not** deployed on static hosting. This is an independent hackathon research prototype, not legal advice, a compliance certification or a product endorsed by RealPage.
