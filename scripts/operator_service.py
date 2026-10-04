"""Local read/preview operations for the judge workbench; JSON on stdin/stdout."""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import OUTPUT, PACK, read_json
from engine.evaluator import evaluate
from engine.law_intake import approve_candidate, extract_candidates
from engine.portfolio import connect, import_csv, passport, portfolio_stats, upsert_property

DATABASE = OUTPUT / "operator_portfolio.sqlite"


def portfolio():
    db = connect(DATABASE)
    if portfolio_stats(db)["properties"] == 0:
        import_csv(db, PACK / "data" / "sample_addresses.csv", assume_sample_city=True)
    return db


def process(payload):
    action = payload.get("action")
    if action == "health":
        return {"ready": True, "mode": "local_operator_workbench"}
    if action == "import_property":
        incoming = payload["property"]
        row = {
            "address_id": str(incoming.get("address_id", "")).strip().upper(),
            "street_address": str(incoming.get("street_address", "")).strip(),
            "postal_city": str(incoming.get("postal_city", "")).strip(),
            "state": str(incoming.get("state", "")).strip().upper(),
            "zip": str(incoming.get("zip", "")).strip(),
            "year_built": str(incoming.get("year_built", "")).strip(),
            "units": str(incoming.get("units", "")).strip(),
            "source_dataset": "Operator workbench entry",
            "retrieved_at": date.today().isoformat(),
        }
        if row["state"] not in {"CA", "NJ", "MA"}:
            raise ValueError("state must be CA, NJ or MA")
        if not row["address_id"].startswith("DEMO-"):
            raise ValueError("use a DEMO- ID so the sample records cannot be overwritten")
        db = portfolio()
        try:
            address_id = upsert_property(db, row)
            result = passport(db, address_id, read_json(OUTPUT / "rules.json")["rules"], "2026-10-01")
            return {"saved": True, "portfolio_properties": portfolio_stats(db)["properties"], "passport": result}
        finally:
            db.close()
    if action == "preview_law":
        source_text = str(payload.get("source_text", ""))
        if len(source_text) > 30000:
            raise ValueError("source text exceeds 30,000 characters")
        candidates = extract_candidates(
            source_text,
            jurisdiction=str(payload["jurisdiction"]),
            source_url=str(payload["source_url"]),
            retrieved_at=str(payload["retrieved_at"]),
        )
        if not candidates:
            return {"candidate_count": 0, "review_status": "no_actionable_clause", "impact": None}
        selected = candidates[0]
        result = {"candidate_count": len(candidates), "candidate": selected,
                  "review_status": "needs_human_review", "impact": None}
        review = payload.get("review")
        if review:
            rule = approve_candidate(
                selected, source_text,
                title=str(review.get("title", "")),
                citation=str(review.get("citation", "")),
                status=str(review.get("status", "")),
                coverage_conditions=str(review.get("coverage_conditions", "")),
                effective_date=review.get("effective_date") or None,
                coverage_spec=review.get("coverage_spec"),
            )
            db = portfolio()
            from engine.portfolio import assess_rule
            result["review_status"] = "reviewed_preview_not_published"
            result["rule"] = rule
            try:
                result["impact"] = assess_rule(db, rule, str(payload.get("as_of") or "2026-10-01"))
            finally:
                db.close()
        return result
    raise ValueError("unknown action")


if __name__ == "__main__":
    try:
        print(json.dumps(process(json.load(sys.stdin))))
    except (ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)
