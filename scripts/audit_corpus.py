import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import CORPUS, OUTPUT, read_csv, write_json

manifest = read_csv(CORPUS / "corpus_manifest.csv")
issues = []
captured = []
links_only = []
gap_register = []
jurisdictions = collections.Counter()

for row in manifest:
    jurisdictions[row["jurisdictions"]] += 1
    rel = row.get("text_file", "").strip()
    if not rel:
        links_only.append(row["doc_id"])
        if row["doc_id"] in {"D070", "D075"}:
            disposition = "recovered_from_official_city_source"
        elif row["doc_id"] in {"D034", "D035"}:
            disposition = "covered_by_verified_supplement"
        elif row["source_type"].startswith("secondary"):
            disposition = "context_only_official_source_preferred"
        elif row["source_type"] == "code publisher":
            disposition = "terms_review_required_not_captured"
        else:
            disposition = "official_source_capture_blocked"
        gap_register.append({"doc_id": row["doc_id"], "jurisdiction": row["jurisdictions"],
                             "source_type": row["source_type"], "url": row["url"],
                             "disposition": disposition})
        continue
    path = CORPUS / rel
    if not path.exists():
        issues.append({"doc_id": row["doc_id"], "kind": "missing_text_file", "path": rel})
        continue
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    if len(text.strip()) < 100:
        issues.append({"doc_id": row["doc_id"], "kind": "text_too_short"})
    captured.append(row["doc_id"])

audit = {
    "manifest_documents": len(manifest),
    "captured_documents": len(captured),
    "links_only_or_unavailable": len(links_only),
    "captured_doc_ids": captured,
    "links_only_doc_ids": links_only,
    "documents_by_jurisdiction": dict(sorted(jurisdictions.items())),
    "integrity_issues": issues,
    "integrity_note": "Manifest hashes describe captured source artifacts and are not compared with derived plain-text files.",
}
write_json(OUTPUT / "corpus_audit.json", audit)
write_json(OUTPUT / "source_gap_register.json", {"gaps": gap_register})
print(f"Audited {len(manifest)} documents: {len(captured)} captured, {len(links_only)} links-only, {len(issues)} integrity issues")
