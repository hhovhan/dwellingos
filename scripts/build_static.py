"""Build a static judge demo without the local-only operator API or oversized assets."""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
DIST = ROOT / "dist"

if DIST.exists():
    shutil.rmtree(DIST)
DIST.mkdir()
for name in ("index.html", "app.js", "styles.css", "theme.css", "system.json"):
    shutil.copy2(PUBLIC / name, DIST / name)

source = json.loads((PUBLIC / "passports.json").read_text(encoding="utf-8"))
passports = source["passports"]
assert len(passports) == source["count"] == 500
chunk_dir = DIST / "passports"
chunk_dir.mkdir()
chunks = []
for index in range(0, len(passports), 50):
    filename = f"passports/{index // 50:02}.json"
    payload = json.dumps({"passports": passports[index:index + 50]}, separators=(",", ":"), ensure_ascii=False)
    (DIST / filename).write_text(payload, encoding="utf-8")
    if (DIST / filename).stat().st_size > 20_000_000:
        raise ValueError(f"Static chunk too large: {filename}")
    chunks.append(filename)
(DIST / "passports-manifest.json").write_text(
    json.dumps({"count": len(passports), "chunks": chunks}, separators=(",", ":")) + "\n", encoding="utf-8")
print(f"Static demo ready: {len(passports)} passports in {len(chunks)} chunks; local-only API omitted")
