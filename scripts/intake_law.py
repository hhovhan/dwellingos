"""Propose evidence-backed rules from a new text file; never auto-publish."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import write_json
from engine.law_intake import extract_candidates

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("text_file", type=Path)
parser.add_argument("--jurisdiction", required=True)
parser.add_argument("--source-url", required=True)
parser.add_argument("--retrieved-at", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
candidates = extract_candidates(args.text_file.read_text(encoding="utf-8"),
    jurisdiction=args.jurisdiction, source_url=args.source_url,
    retrieved_at=args.retrieved_at)
write_json(args.output, {"source_file": str(args.text_file), "candidate_count": len(candidates),
                         "candidates": candidates})
print(f"Proposed {len(candidates)} reviewable candidates at {args.output}")
