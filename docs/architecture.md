# DwellingOS architecture

```mermaid
flowchart LR
  A[87-source manifest] --> B[Corpus auditor]
  B --> C[54 captured source texts]
  B --> G[Explicit source-gap register]
  C --> D[Automated rule extractor]
  S[2 verified supplements] --> D
  D --> E[Evidence-linked rule registry]
  P[500 public property records] --> J[Jurisdiction resolver]
  E --> V[Deterministic evaluator]
  J --> V
  V --> L[lookups.json]
  V --> T[T1-T5 change tracker]
  L --> U[Property Law Passport]
  T --> U
  G --> U
```

The model-assisted portion may identify candidate text, but it never owns the final result. The deterministic evaluator controls jurisdiction, time status and allowed output vocabulary. Every result retains its rule ID and source URL.

## Failure policy

- Missing property fact: return `unknown` and name the missing fact.
- Future effective date: return `not_yet_effective`.
- Pending bill: return `pending`.
- Failed measure: exclude from live lookups.
- State/local interaction: preserve both rules and set `conflict_flag` for review.
- Missing source: register the gap; never fabricate a replacement citation.
