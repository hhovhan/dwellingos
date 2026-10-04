# RealPage presenter recording: full 2:51 review

Source: the user's local `housing.mov` recording from the Hack-Nation kickoff. Reviewed the full audio and all nine visible slides on 2026-10-03. Speech was machine-transcribed and checked against the visible slide text; the slides control where the audio is unclear.

## What the representative actually asked for

- RealPage described software used across 20M+ homes and a need to make fast-changing rental rules understandable to residents and operators. The 20M+ figure describes RealPage's business, not the size or verified completeness of the challenge data.
- For one apartment/building address, identify which state and local rules apply now, which do not, and which are changing. The answer must be understandable, source-linked, maintainable and not legal advice.
- Required build sequence on slide 6: **extract → resolve → apply → explain → track change**.
- Provided starter pack on slide 6: **500 sample buildings/parcel records, 54 captured source texts, three states (CA, NJ, MA), six rule categories, and one scoring script**. The deck says a scoring script exists; it does not make the script or its cases public to our team.

## Explicit judging rubric on slide 8

| Area | Points | Our demonstrated evidence | Remaining risk |
| --- | ---: | --- | --- |
| Extraction accuracy | 25 | 57 evidence-linked reviewed candidates; verbatim source-span gate | Not checked against a complete independent legal answer set; unfamiliar sources queue for review |
| Address coverage | 20 | 500 passports and state/city evaluation | Municipal boundaries not independently verified; 27 supplied ZIP/state-prefix conflicts |
| Citations | 15 | Each emitted rule has URL, citation, retrieved date and verbatim span | Citation completeness is not proof that the rule interpretation is legally correct |
| Change tracking | 15 | Five starter scenarios and affected-address sets | Pending and conflicts require expert interpretation; real-time official-feed coverage is not yet proven |
| Plain language | 10 | Address-first passport, decision rationale and source details | Record titles and legal wording still need concise operator-facing summaries |
| Responsible design | 10 | `unknown` for missing facts, pending/future/failed separated, not-legal-advice notice | Additional source and property verification needed before operational reliance |
| Path to scale | 5 | Indexed 20M-row synthetic import and evaluation benchmark | Not a production integration or 20M legally validated passports |

The slide totals **100 points: 75 script-scored + 25 judged in the demo**. Visual polish supports the demo categories but is not a separate score line.

## Six traps on slide 7

1. A missing construction year: `unknown` should earn credit; guessing should not.
2. Mailing city is not legal city: Dorchester/Boston and San Ysidro/San Diego are examples.
3. Enacted is not effective: the NJ FAIR Act was signed in 2026 but takes effect in July 2027.
4. Pending is not law: Massachusetts proposals must remain hypothetical.
5. Struck is not law: a failed Massachusetts rent-control ballot measure must not generate a live rule.
6. A stricter city rule can control over a state ceiling: the San Francisco example needs explicit coverage and conflict analysis, not two unqualified rule cards.

## Presenter emphasis from speech

He repeatedly said changing laws are difficult for renters to understand, wanted a simple answer for a building/apartment, and closed by rejecting AI-generated legal advice. He framed the outcome as following rules, not advising people how to evade them. This means we should show the decision, source, date and unresolved facts before any elaborate architecture diagram.

## Immediate priorities from this audit

1. Keep browser scenarios on the same Python evaluator as exports; precomputed decision tables and parity tests now cover that.
2. Do not trust postal city or ZIP alone; surface conflicts and seek independent municipal-boundary evidence.
3. The San Francisco city/state example now has an evidence-gated scenario: unknown coverage stays unknown; verified rent-control coverage applies the time-bounded city rate and marks the state ceiling superseded. This is not a claim that any sample building is actually rent-controlled.
4. Make the live demo address-first and visibly distinguish current, pending, future and unknown outcomes.
5. Show scale as a measured data path, not a legal-accuracy claim.
