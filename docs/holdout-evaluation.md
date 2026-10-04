# Source-first holdout evaluation (2026-10-04)

This set is separate from the project's 20-case rule-decision regression set. The annotations in `quality/holdout_cases.json` were made from original starter-pack source texts, raw property rows and the captured Census response before running `scripts/score_holdout.py`. They are non-attorney annotations, not the organizer's hidden scoring cases.

Run `npm run score:holdout` for a diagnostic report in `output/holdout_report.json`, or `npm run test:holdout` to fail on a regression.

## What was tested

- Eight targeted provisions in original source texts across Berkeley, Massachusetts and San Francisco, plus one status-only bill page expected to produce no operative candidate. A pass means the candidate has the expected category and quotes the target source phrase; it does **not** prove all clauses or conditions were extracted correctly.
- Eleven selected address records: five single Census address-range matches, five ambiguous/unmatched responses, and one supplied ZIP/state conflict. Checks compare the raw row, captured Census evidence and passport; they do **not** prove parcel boundaries or legal jurisdiction.

## Initial findings and repairs

The first locked run found **6/9 extraction** and **11/11 address** checks. The generic extractor missed a Berkeley rent-ceiling notice and a San Francisco rate table; it also treated language on a Massachusetts bill-history listing as an operative candidate. The parser now recognizes these rate formats and rejects status-only bill pages lacking actual bill text. The same locked set now reports **9/9 extraction** and **11/11 address** checks; dedicated regression tests cover the three repairs.

This is a small targeted set. It does not measure full-corpus extraction recall or precision. In the complete sample, 117 of 500 addresses had no single usable Census address-range match, and no parcel-level municipal-boundary proof is available. A real legal-quality score requires an independent expert to annotate unseen source provisions and addresses, then compare them with frozen model outputs. The organizer's private scoring script is unavailable.
