# DwellingOS

An evidence-first Property Law Passport for the RealPage Rental Housing Law Navigator challenge.

DwellingOS turns the organizer's 500-property dataset into date-specific,
six-category passports. It never treats missing coverage facts as permission to
guess: uncertain results are labelled `unknown` and explain what evidence is
still required.

## Verify the complete pipeline

```bash
npm run pipeline
npm start
```

Open `http://127.0.0.1:4173`.

The organizer-provided corpus and 500-address dataset are bundled under
`realpage-starter-pack/`, so these commands work from a clean checkout without
machine-specific paths.

## Current verified build

- 500/500 properties processed
- 57 evidence-linked rules
- 5,419 deterministic address-rule evaluations
- 47 automated tests, a separate 9-case extraction/11-case address holdout, and 20 source-anchored, non-attorney rule-decision cases
- 100% citation and verbatim-evidence completeness among emitted rules
- Zero unsupported extraction candidates
- 20-million-row synthetic portfolio import and indexed rule assessment completed (see measured limits below)
- 27 supplied ZIP/state-prefix conflicts surfaced as blocking address-verification gaps, not silently accepted as valid locations
- 383 single Census address-range matches; 117 unresolved or ambiguous checks. None is claimed as parcel-level boundary proof.

## Pipeline

1. Audit all 87 starter-pack corpus records.
2. Extract evidence-linked candidate rules from captured source texts using reviewed, source-specific anchors; queue unfamiliar text for separate human-reviewed intake.
3. Add two separately verified city sources needed for the official boundary test.
4. Map all 500 properties to state and provisional legal city, including reviewed sample aliases; flag that municipal boundaries still need independent verification.
   `python3 scripts/geocode_samples.py` refreshes the optional Census incorporated-place evidence before rebuilding outputs. This external check does not settle parcel boundaries or override unverified legal-city decisions.
5. Evaluate jurisdiction, status and effective dates without using an LLM for final decisions.
6. Generate `rules.json`, `lookups.json`, `changes.json`, passports, an audit log and a quality report.
7. Run the automated test suite.

## Evidence policy

- Every rule must carry a source URL, citation, provenance and a verbatim supporting span.
- `unknown` is returned when property facts cannot prove coverage.
- Pending, failed and future-effective law are kept separate from current law.
- The interface always displays the answer date and “Not legal advice.”

The extractor produces source-reviewed hackathon candidates, not
attorney-validated production legal advice. Thirty-three starter-manifest
entries are link-only: 22 are secondary context, two have verified supplements,
two now have official-city-source recoveries, six publisher pages remain under
terms review, and one official regulation remains capture-blocked. The 20-case
reference suite catches selected decision regressions but is not a complete
expert-reviewed legal gold set.

## New laws and larger portfolios

The 500-property static website is the competition demonstration. `scripts/check_source.py`
queues changes to a named official source, `scripts/intake_law.py` proposes
verbatim candidates from unfamiliar text, and `scripts/approve_candidate.py`
records reviewed rules. `scripts/portfolio_cli.py` streams new properties into
an indexed database and evaluates a selected property or jurisdiction on demand
through the same rule engine. See [scale architecture](docs/scale-architecture.md)
and the [one-page method note](docs/method-note.md) for what has been measured
and what 20-million-property deployment would still require.

The 20-million-row synthetic run took 133.488 seconds to import, 3.185 seconds
to select 2 million city candidates and 25.927 seconds to evaluate those
candidates against one reviewed rule. This is a scale test of the data path,
not proof of verified boundaries, complete law coverage or production service
reliability.

With `npm start`, the local website exposes an operator workbench: import a
`DEMO-` property into a persistent SQLite portfolio, or paste a dated HTTPS
source to extract a verbatim candidate and preview its jurisdiction-wide
impact after filling reviewer fields. New properties with unverified municipal
boundaries have city rules withheld. A source preview never publishes a law;
human legal/source review remains required. The workbench is **local-only**:
static hosting displays the 500-property demonstration without these API
operations. Test it locally or show it in the technical video.

The [full RealPage presentation audit](docs/realpage-presentation-audit.md) records the 100-point rubric and six explicit judge traps. The [two-minute demo script](docs/demo-video-script.md) follows the live product and marks every claim that remains provisional.

## Static deployment

The deployable site is entirely inside `public/`. Platforms that support a
static output directory can publish that folder directly; `vercel.json`
contains the matching Vercel configuration.
