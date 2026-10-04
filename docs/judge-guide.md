# Judge verification guide

This guide maps observable product behavior to code and outputs. It is not a narration script or a claim about the organizer's private score.

| Check | In the [live product](https://dwelling.hovhannes.dev/) | Expected observation | Verify in the repository |
| --- | --- | --- | --- |
| Conditional coverage | Open **01 · Unknown** (Newark sample A0013). | The possible 4% ceiling is cited, but coverage remains conditional and the next action is to verify `rent_control_status`. Changing that control is an unsaved hypothetical, not a verified fact. | `engine/evaluator.py`, `output/lookups.json`, `tests/test_pipeline.py` |
| Jurisdiction | Open **02 · City**. | A postal-city name or address-range match does not silently become proof of a legal municipal boundary. | `engine/portfolio.py`, `output/geocode_evidence.json`, `tests/test_portfolio.py` |
| Effective date | Open **03 · Date** and compare before/after. | A rule does not apply before its effective date; status and citation remain visible. | `engine/evaluator.py`, `output/changes.json`, `tests/test_pipeline.py` |
| Portfolio impact | Open **04 · Impact** and inspect T1–T5. | The app reports candidate addresses and potential conflicts, not certified coverage for every building. | `engine/change_tracker.py`, `output/changes.json`, `tests/test_pipeline.py` |

## Reproduce the outputs

From a clean clone, run `npm run pipeline` followed by `npm run build:static`. The pipeline audits 87 manifest entries, creates the three competition JSON outputs, builds 500 passports, runs 47 unit tests, scores targeted holdouts and checks the release contract. The static build writes a deployable `dist/` snapshot in ten passport chunks. No provider key is required.

For the local-only operator path, run `npm start`: import a new property or preview a pasted legal source. New city rules are withheld when municipal jurisdiction is unverified; a new source remains a candidate until review. Static hosting does not expose these write operations. See [architecture](architecture.md) and [scale architecture](scale-architecture.md).

## Interpretation boundaries

- The 9 extraction and 11 address holdout checks are targeted, non-attorney cases—not full-corpus recall or parcel-boundary validation.
- The 20 reference decisions are project-authored regressions, not the organizer's hidden answer key.
- The 20-million-row benchmark uses synthetic properties and establishes a data-processing path, not verified legal coverage at production scale.
- The four independently checked supplemental rules are not claimed as supplied-corpus citation credit.
