"""Check sample mailing-city assumptions against Census incorporated-place geography."""

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urlencode

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import OUTPUT, PACK, read_csv, write_json

ENDPOINT = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
rows = read_csv(PACK / "data" / "sample_addresses.csv")


def inspect(row):
    address = f'{row["street_address"]}, {row["postal_city"]}, {row["state"]}'
    url = ENDPOINT + "?" + urlencode({"address": address, "benchmark": "Public_AR_Current",
                                    "vintage": "Current_Current", "format": "json"})
    last_error = None
    for attempt in range(3):
        try:
            response = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--max-time", "15", url],
                                      capture_output=True, text=True, check=True)
            matches = json.loads(response.stdout)["result"]["addressMatches"]
            if len(matches) != 1:
                return row["address_id"], {"status": "unresolved", "reason": f"{len(matches)} address matches", "input": address}
            match = matches[0]
            components = match["addressComponents"]
            input_number = row["street_address"].split()[0]
            matched_number = match["matchedAddress"].split()[0]
            if components["state"].upper() != row["state"].upper():
                return row["address_id"], {"status": "conflict", "reason": "matched state differs", "input": address,
                                           "matched_address": match["matchedAddress"]}
            if input_number != matched_number:
                return row["address_id"], {"status": "unresolved", "reason": "address number or range differs from single geocoder match",
                                           "input": address, "matched_address": match["matchedAddress"]}
            places = match["geographies"].get("Incorporated Places", [])
            if not places:
                return row["address_id"], {"status": "unresolved", "reason": "no incorporated place in geocoder response",
                                           "input": address, "matched_address": match["matchedAddress"]}
            place = places[0]["NAME"]
            city = place.rsplit(" ", 1)[0] if place.lower().endswith((" city", " town", " village")) else place
            return row["address_id"], {"status": "matched", "legal_city": city,
                                       "matched_address": match["matchedAddress"], "input": address,
                                       "geocoder_url": url, "match_type": "Census street-range geocode; parcel point not verified"}
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.3 * (attempt + 1))
    return row["address_id"], {"status": "unresolved", "reason": last_error, "input": address}


if __name__ == "__main__":
    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for future in as_completed(pool.submit(inspect, row) for row in rows):
            address_id, evidence = future.result()
            results[address_id] = evidence
    counts = {status: sum(value["status"] == status for value in results.values())
              for status in ("matched", "unresolved", "conflict")}
    write_json(OUTPUT / "geocode_evidence.json", {
        "source": "U.S. Census Geocoding Services API", "benchmark": "Public_AR_Current",
        "vintage": "Current_Current", "checked_at": datetime.now(timezone.utc).isoformat(),
        "interpretation": "Address-range and incorporated-place lookup; parcel-level legal boundaries remain unverified.",
        "counts": counts, "records": dict(sorted(results.items())),
    })
    print(f"Census check: {counts}")
