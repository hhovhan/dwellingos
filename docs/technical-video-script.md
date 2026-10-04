# Teach / technical video — one minute

Use the local checkout and `http://127.0.0.1:4173/`. This video teaches the implementation, not the private score. Prepare test output before recording.

| Time | Screen | Spoken point |
| --- | --- | --- |
| 0:00–0:12 | Show `realpage-starter-pack/`, then `scripts/extract_rules.py`. | “The build audits 87 source entries, reads the supplied captured texts, extracts verbatim candidates, and publishes only reviewed rules. Four external supplements are identified separately.” |
| 0:12–0:27 | Show `engine/evaluator.py` and the `unknown` branch. | “The decision engine checks jurisdiction, date and coverage facts. It will not turn missing owner or occupancy evidence into an `applies` answer.” |
| 0:27–0:40 | Show terminal summaries for `npm test`, `npm run test:holdout`, and `npm run score:reference`. | “We run regression tests, source-first extraction and address holdouts, and source-anchored reference decisions. They do not predict the hidden organizer score.” |
| 0:40–0:52 | Show `engine/portfolio.py`, then a prepared benchmark result. | “An indexed portfolio path processed 20 million synthetic rows; law change assessment scans jurisdiction candidates rather than every property.” |
| 0:52–1:00 | Return to the live passport and its evidence gap. | “Production still requires parcel-boundary verification, official-source monitoring and expert legal review. The prototype exposes those limits.” |

Do not imply the static public site hosts the local import/review API. Show the local workbench only if it has been separately tested in the recording session. Keep the code and terminal readable; no personal data or notifications.
