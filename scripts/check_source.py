"""Poll one official manifest URL and queue any changed source for review."""

import argparse
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import CORPUS, ROOT, read_csv, read_json, write_json
from engine.source_monitor import observe

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("doc_id", help="An official captured corpus document ID")
parser.add_argument("--state", type=Path, default=ROOT / "output" / "source_monitor_state.json")
parser.add_argument("--queue", type=Path, default=ROOT / "output" / "source_review_queue")
args = parser.parse_args()
manifest = read_csv(CORPUS / "corpus_manifest.csv")
row = next((item for item in manifest if item["doc_id"] == args.doc_id), None)
if not row or row["capture"] != "yes" or not row["source_type"].startswith("official"):
    parser.error("doc_id must be an official captured source in the manifest")
request = urllib.request.Request(row["url"], headers={"User-Agent": "DwellingOS source monitor (hackathon research prototype)"})
with urllib.request.urlopen(request, timeout=15) as response:
    content_type = response.headers.get("Content-Type", "application/octet-stream")
    body = response.read(5_000_001)
if len(body) > 5_000_000:
    raise SystemExit("Source exceeds 5 MB review limit")
state = read_json(args.state) if args.state.exists() else {}
observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
next_state, event = observe(state, args.doc_id, body, observed_at, row["url"], content_type)
write_json(args.state, next_state)
if event["status"] == "changed":
    args.queue.mkdir(parents=True, exist_ok=True)
    stem = f"{args.doc_id}-{event['sha256'][:12]}"
    (args.queue / f"{stem}.bin").write_bytes(body)
    write_json(args.queue / f"{stem}.json", event)
print(f"{args.doc_id}: {event['status']} ({len(body)} bytes); review queue: {args.queue if event['status'] == 'changed' else 'unchanged'}")
