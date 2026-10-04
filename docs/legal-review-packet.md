# Legal review packet — RealPage challenge prototype

This packet is for an independent housing-law reviewer. The current project team is not claiming attorney validation. A passing software test is not a legal opinion.

## Review target

1. Open `output/rules.json` and review each emitted rule against its linked primary source. Check the operative text, law versus proposal status, effective date, geographic scope, covered property types, exceptions, penalties, and conflicts with state or local law.
2. Open `quality/reference_cases.json`. For each case, decide the expected result **without looking at engine output**, then record reviewer name/role, review date, source version and any correction. Only after locking those answers, run `npm run score:reference` and compare with `output/reference_case_report.json`.
3. Expand the set beyond the current 20 examples, especially rent-control exemptions, occupancy dates, owner types, municipal boundaries, conflicting laws and amended provisions. Include cases where a correct result is `unknown` or no rule match.
4. Review the 33 original link-only manifest entries by disposition. The relevant incremental gaps are below; secondary duplicates are not automatically missing laws.

## Current link-only disposition

- 22 secondary/context links: reference only; compare against captured official source if a discrepancy is suspected.
- 2 separately verified supplements: Hoboken and Jersey City algorithmic-pricing provisions.
- 2 recovered official city excerpts: Newark rent-control ceiling (`NEWARK-RENT-01`) and San Diego source-of-income restriction (`SD-INCOME-01`). The excerpts and URLs are in `sources/recovered/`; both rules intentionally stay `unknown` without property-specific coverage evidence.
- 6 code-publisher pages pending terms/content review: Hoboken D032–D033, Los Angeles D038, Newark D071–D072, and San Diego D074. Some may duplicate captured rules; verify before adding.
- 1 blocked official regulation: Massachusetts D056, 803 CMR 5.00 (CORI housing). The official catalog page is identifiable, but source text capture did not succeed in this build. Do not infer its provisions from a search result.

## Required sign-off record for each rule

`team_rule_id`, reviewer name and credentials, review date, primary source URL and retrieval timestamp, exact source section/version, operative status, effective date, coverage predicate, exceptions, penalty/remedy, conflict/preemption note, approved/rejected decision, and explanation. Rejected and unresolved rules must not be presented as definitive.

## Known limits

The current 20-case set is hand-authored and source-anchored by a non-attorney. It covers selected positive, negative, temporal and missing-fact outcomes; it cannot measure recall over every legal provision. The 500 sample addresses also have unverified municipal boundaries and missing ownership/occupancy data; 27 records have ZIP/state-prefix conflicts. Legal review alone cannot make every passport definitive.
