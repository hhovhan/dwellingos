# DwellingOS — Property Law Passports

## One-line description

DwellingOS compiles changing rental law into an evidence-backed, date-specific legal passport for each property—showing what applies, what is unknown and exactly why.

## Problem

Rental compliance research is repeated address by address across fragmented state and city sources. A mailing city may not be the legal jurisdiction, a statute may not yet be effective, and coverage may depend on facts missing from public property data. A confident-looking generic answer is therefore dangerous.

## Solution

Search any of the 500 challenge properties. DwellingOS resolves its legal city, displays the supplied property evidence, evaluates evidence-linked rules across all six challenge categories, exposes missing coverage facts and provides direct citations. A five-scenario tracker shows how results change over time and across boundaries.

## What makes it different

- Evidence before answers: every rule has a source and verbatim supporting span.
- Deterministic final decisions: language models do not choose `applies`.
- Honest uncertainty: missing owner, occupancy, age or unit facts remain visible.
- Change-native: future, pending, failed and conflicting law are separate states.
- Auditable scale: the same pipeline generates all 500 passports and submission JSON.

## Technical implementation

Python performs corpus auditing, automated candidate extraction, jurisdiction resolution, rule evaluation, change tracking and quality reporting. A dependency-free JavaScript interface serves the resulting passports. The pipeline produces `rules.json`, `lookups.json` and `changes.json` in the organizer formats.

## Verified results — October 4, 2026 build

- 500/500 property IDs processed
- 57 evidence-linked rules after state-by-state source review: 53 from supplied captured texts and 4 clearly identified external supplements
- 5,419 deterministic address-rule evaluations
- 100% source-link and supporting-span completeness among emitted candidates; this is an internal audit, not a claimed organizer citation score. The organizer says independently saved link-only texts do not count toward its supplied-corpus citation metric.
- Zero unsupported extraction candidates
- Official change scenarios produce affected sets of 250, 90, 140, 110 and 0
- 47 automated tests, 9 extraction/11 address holdout checks, 20 non-attorney reference cases, plus release and browser checks
- Desktop search/detail flow passed with no console errors
- 390px mobile viewport passed with zero horizontal overflow

## Responsible-use statement

DwellingOS is a research prototype, not legal advice or a compliance
certification. The emitted rules were checked against the supplied source text,
but production use still requires qualified legal review, freshness monitoring,
and additional property/ownership evidence.
