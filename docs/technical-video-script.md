# Technical demo — one clean take, about 2 minutes

Use the running local site at `http://127.0.0.1:4173/`. Record only the browser and project terminal/editor; avoid personal notifications. This script describes verified behaviors, not legal advice or a private-score claim.

| Time | Screen action | Spoken line |
| --- | --- | --- |
| 0:00–0:18 | Open `01 / Evidence gap` (Newark). Hold on the address, conditional 4% rule, citation and next action. | “RealPage asked for an address-level answer. For this Newark building we found a cited 4% ceiling, but the record does not prove rent-control coverage. We show the missing fact instead of claiming the limit applies.” |
| 0:18–0:36 | Click **Explore a hypothetical fact**; select **Hypothetically covered**; show the changed result and warning. | “The evaluator recomputes when the fact changes. This is explicitly hypothetical and unsaved; the real-world next step is to verify rent-control status with city or property records.” |
| 0:36–0:56 | Click `03 · DATE`; then **Show after date**. | “Jurisdiction, effective date and property facts are evaluated deterministically. A California rule changes from not yet effective to applicable across the boundary, with its source and date visible.” |
| 0:56–1:16 | Show terminal output of `npm run test:holdout` and `npm test` (run before recording; do not wait through a long command). | “We added a source-first holdout, separate from our original rule cases. It exposed two missed rate notices and a bill-status false positive. After repair, all nine targeted extraction checks and eleven address consistency checks pass; the full regression suite also passes.” |
| 1:16–1:38 | Show `engine/law_intake.py` around `extract_candidates`, then `engine/evaluator.py` around `evaluate`; do not scroll rapidly. | “An unfamiliar source produces an unpublished, verbatim candidate; review is required before it can become a rule. The evaluator then uses explicit coverage, jurisdiction and time conditions. Missing facts remain unknown.” |
| 1:38–1:58 | Return to the site, open `04 · IMPACT` and show T1/T3 candidate counts; end on `workflow`. | “The indexed path was benchmarked on 20 million synthetic rows. That is a processing result, not 20 million verified legal answers. Parcel boundaries, continuous source discovery and expert review remain deployment work.” |

## Capture checks

- Keep the conditional wording visible: 4% is **not** confirmed for the sample Newark building.
- The holdout is source-first and non-attorney, not a full legal gold set. It does not estimate the organizer's private score.
- The address checks compare raw rows, captured Census evidence and passports. They do not prove parcel-level municipal boundaries; 117 of 500 had no single usable Census address-range match.
- The new-law workbench is a local reviewed preview, not automatic live publication and not available on a static-only host.
- Before recording, run `npm run test:holdout` and `npm test`, prepare the terminal at the summaries, set browser zoom so the full decision brief is legible, and confirm no personal data or notifications are in frame.
