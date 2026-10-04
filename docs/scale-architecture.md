# Portfolio scale: one legal engine, indexed property storage

The hackathon website ships 500 precomputed passports so judges can open it instantly. The same Python evaluator also works against a disk-backed portfolio. It is invoked through `scripts/portfolio_cli.py`; there is no 20-million-row JSON file or browser preload.

## Actual path for a new property

1. Import a CSV in 5,000-row transactions. Required fields are ID, street address, postal city, state, source and retrieval date. Units, construction year, owner and occupancy evidence may be empty.
2. Resolve legal city from a supplied legal-city field or a reviewed alias. Unknown municipal boundaries remain explicit. The challenge-only `--assume-sample-city` switch marks its assumption in every record.
3. Look up one property by primary key and evaluate its state and city rules on demand. Only rule metadata is held in memory.
4. Return the rule status, citation, exact quotation and missing facts. A city rule is withheld when legal city is unverified.

## Actual path for a changed law

1. `check_source.py` polls one official source already listed in the manifest. It records a first baseline; subsequent byte changes enter a review queue. It never publishes changes automatically.
2. `intake_law.py` extracts candidate clauses from a new text file, attaching exact source text, URL and retrieval date. It does not guess effective date, exemptions or legal force.
3. `approve_candidate.py` requires a reviewer to supply status, coverage conditions, citation, and any effective date. The quotation is checked against the source. A machine-readable coverage test may be attached; absent that test, evaluation returns `unknown`.
4. Regenerate the small 500-property competition snapshot with `npm run pipeline`. For a large portfolio, `portfolio_cli.py assess RULE_ID` uses the state/city index and evaluates only candidate properties, reporting applies, unknown and excluded counts.

## Measured scale and boundaries

On this machine, `python3 scripts/benchmark_portfolio.py --count 20000000` imported 20 million **synthetic** properties in 133.488 seconds, selected 2 million city candidates in 3.185 seconds, and evaluated those 2 million against one rule in 25.927 seconds. The resulting SQLite file was 4,542,881,792 bytes. An earlier one-million-row run imported in 6.061 seconds, selected 100,000 candidates in 0.094 seconds and assessed them in 0.908 seconds. This verifies a bounded-memory import, indexed candidate lookup and rule-assessment path at the requested row count on this machine. It does **not** establish production service reliability, concurrent multi-user performance, accurate municipal boundaries, freshness of 20 million real property records, or complete legal-rule recall. A production service would still need a persistent database with capacity headroom, background workers, source-change scheduling, an HTTP API, monitoring and legal review. The engine and data model are reusable; the browser build is a challenge demonstration, not that production service.

## Commands

```bash
python3 scripts/portfolio_cli.py --database /path/to/portfolio.sqlite import realpage-starter-pack/data/sample_addresses.csv --assume-sample-city
python3 scripts/portfolio_cli.py --database /path/to/portfolio.sqlite stats
python3 scripts/portfolio_cli.py --database /path/to/portfolio.sqlite passport A0001 --as-of 2026-10-01
python3 scripts/portfolio_cli.py --database /path/to/portfolio.sqlite assess CA-ALG-01 --as-of 2026-01-02
python3 scripts/benchmark_portfolio.py --count 20000000
```

The 500-property sample has known quality issues: missing property facts and some postal ZIP codes inconsistent with their listed city. Independent address-to-boundary verification remains necessary before offering definitive city-level coverage in a large portfolio.

`portfolio_cli.py stats` exposes the evidence backlog instead of hiding it. In the 500-row challenge sample, 462 city mappings still rely on unverified postal-city assumptions, 242 unit counts and 212 construction years are missing, and owner type and occupancy evidence are missing for all 500. These counts identify exactly where RealPage data enrichment or municipal boundary checks are required before definitive answers.
