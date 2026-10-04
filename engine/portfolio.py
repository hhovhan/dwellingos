"""Disk-backed portfolio index. Work is proportional to a jurisdiction, not the portfolio."""

import csv
import sqlite3
from pathlib import Path

from engine.common import LEGAL_CITY_ALIASES


def connect(path):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS property (
            address_id TEXT PRIMARY KEY,
            street_address TEXT NOT NULL,
            postal_city TEXT NOT NULL,
            legal_city TEXT,
            state TEXT NOT NULL,
            zip TEXT,
            year_built INTEGER,
            units INTEGER,
            owner_type TEXT,
            certificate_of_occupancy TEXT,
            jurisdiction_evidence TEXT NOT NULL,
            source_dataset TEXT NOT NULL,
            retrieved_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS property_state_id ON property(state, address_id);
        CREATE INDEX IF NOT EXISTS property_city_id ON property(state, legal_city, address_id);
    """)
    return connection


def normalize_row(row, assume_sample_city=False, allow_alias=True):
    required = ("address_id", "street_address", "postal_city", "state", "source_dataset", "retrieved_at")
    missing = [field for field in required if not (row.get(field) or "").strip()]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    legal_city = (row.get("legal_city") or "").strip()
    if legal_city:
        evidence = "supplied_legal_city_unverified"
    elif allow_alias and row["postal_city"] in LEGAL_CITY_ALIASES:
        legal_city = LEGAL_CITY_ALIASES[row["postal_city"]]
        evidence = "audited_sample_alias"
    elif assume_sample_city:
        legal_city = row["postal_city"].strip()
        evidence = "sample_postal_city_assumption_needs_boundary_check"
    else:
        # A postal city is not proof of municipal boundaries. Keep that fact
        # explicit even though it makes some city answers unresolved.
        legal_city = None
        evidence = "legal_boundary_unverified"
    def number(field):
        value = (row.get(field) or "").strip()
        if not value:
            return None
        parsed = int(float(value))
        if parsed < 0:
            raise ValueError(f"{field} must be non-negative")
        return parsed
    return (
        row["address_id"].strip(), row["street_address"].strip(),
        row["postal_city"].strip(), legal_city, row["state"].strip().upper(),
        (row.get("zip") or "").strip() or None, number("year_built"), number("units"),
        (row.get("owner_type") or "").strip() or None,
        (row.get("certificate_of_occupancy") or "").strip() or None,
        evidence, row["source_dataset"].strip(), row["retrieved_at"].strip(),
    )


def import_csv(connection, csv_path, batch_size=5000, assume_sample_city=False):
    """Stream and upsert a CSV; memory stays bounded by batch_size."""
    columns = "address_id,street_address,postal_city,legal_city,state,zip,year_built,units,owner_type,certificate_of_occupancy,jurisdiction_evidence,source_dataset,retrieved_at"
    placeholders = ",".join("?" for _ in range(13))
    update = ",".join(f"{name}=excluded.{name}" for name in columns.split(",") if name != "address_id")
    sql = f"INSERT INTO property ({columns}) VALUES ({placeholders}) ON CONFLICT(address_id) DO UPDATE SET {update}"
    imported = 0
    batch = []
    with Path(csv_path).open(newline="", encoding="utf-8-sig") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), start=2):
            try:
                batch.append(normalize_row(row, assume_sample_city=assume_sample_city))
            except (ValueError, KeyError) as exc:
                raise ValueError(f"CSV line {line_number}: {exc}") from exc
            if len(batch) >= batch_size:
                with connection:
                    connection.executemany(sql, batch)
                imported += len(batch)
                batch.clear()
    if batch:
        with connection:
            connection.executemany(sql, batch)
        imported += len(batch)
    return imported


def upsert_property(connection, row):
    """Add one operator-supplied property to the same indexed portfolio."""
    values = normalize_row(row, allow_alias=False)
    columns = "address_id,street_address,postal_city,legal_city,state,zip,year_built,units,owner_type,certificate_of_occupancy,jurisdiction_evidence,source_dataset,retrieved_at"
    names = columns.split(",")
    update = ",".join(f"{name}=excluded.{name}" for name in names if name != "address_id")
    with connection:
        connection.execute(f"INSERT INTO property ({columns}) VALUES ({','.join('?' for _ in names)}) ON CONFLICT(address_id) DO UPDATE SET {update}", values)
    return values[0]


def portfolio_stats(connection):
    """Portfolio-wide evidence inventory; no property rows loaded into Python."""
    row = connection.execute("""
        SELECT count(*) AS properties,
               sum(CASE WHEN legal_city IS NULL THEN 1 ELSE 0 END) AS legal_city_unresolved,
               sum(CASE WHEN jurisdiction_evidence IN
                   ('sample_postal_city_assumption_needs_boundary_check', 'supplied_legal_city_unverified')
                   THEN 1 ELSE 0 END) AS city_boundary_unverified,
               sum(CASE WHEN units IS NULL THEN 1 ELSE 0 END) AS units_missing,
               sum(CASE WHEN year_built IS NULL THEN 1 ELSE 0 END) AS year_built_missing,
               sum(CASE WHEN owner_type IS NULL THEN 1 ELSE 0 END) AS owner_type_missing,
               sum(CASE WHEN certificate_of_occupancy IS NULL THEN 1 ELSE 0 END) AS occupancy_evidence_missing
        FROM property
    """).fetchone()
    keys = ("properties", "legal_city_unresolved", "city_boundary_unverified",
            "units_missing", "year_built_missing", "owner_type_missing",
            "occupancy_evidence_missing")
    return dict(zip(keys, (value or 0 for value in row)))


def impact(connection, jurisdiction, page_size=1000):
    """Yield affected IDs in pages using an indexed cursor, never OFFSET."""
    if ", " in jurisdiction:
        city, state = jurisdiction.rsplit(", ", 1)
        where, parameters = "state=? AND legal_city=?", (state, city)
    else:
        where, parameters = "state=?", (jurisdiction,)
    last_id = ""
    while True:
        rows = connection.execute(
            f"SELECT address_id FROM property WHERE {where} AND address_id>? ORDER BY address_id LIMIT ?",
            (*parameters, last_id, page_size),
        ).fetchall()
        if not rows:
            break
        for (address_id,) in rows:
            yield address_id
        last_id = rows[-1][0]


def assess_rule(connection, rule, as_of, page_size=1000):
    """Evaluate one reviewed rule for indexed jurisdiction candidates."""
    from collections import Counter
    from engine.evaluator import evaluate

    jurisdiction = rule["jurisdiction"]
    if ", " in jurisdiction:
        city, state = jurisdiction.rsplit(", ", 1)
        where, parameters = "state=? AND legal_city=?", (state, city)
    else:
        where, parameters = "state=?", (jurisdiction,)
    last_id = ""
    counts = Counter()
    examples = {}
    connection.row_factory = sqlite3.Row
    try:
        while True:
            rows = connection.execute(
                f"SELECT * FROM property WHERE {where} AND address_id>? ORDER BY address_id LIMIT ?",
                (*parameters, last_id, page_size),
            ).fetchall()
            if not rows:
                break
            for row in rows:
                value = evaluate(rule, dict(row), as_of)
                label = value["result"] if value else "not_applicable"
                counts[label] += 1
                if len(examples.get(label, [])) < 5:
                    examples.setdefault(label, []).append(row["address_id"])
            last_id = rows[-1]["address_id"]
    finally:
        connection.row_factory = None
    return {"jurisdiction": jurisdiction, "as_of": as_of,
            "candidates": sum(counts.values()), "results": dict(counts), "example_ids": examples}


def passport(connection, address_id, rules, as_of):
    """Compute one passport on demand by indexed ID, including explicit gaps."""
    from engine.evaluator import evaluate, resolve_jurisdiction

    connection.row_factory = sqlite3.Row
    try:
        found = connection.execute("SELECT * FROM property WHERE address_id=?", (address_id,)).fetchone()
        if not found:
            return None
        record = dict(found)
    finally:
        connection.row_factory = None
    results = [dict(value, category=rule["category"], citation=rule["citation"],
                    source_url=rule["source_url"], quoted_span=rule["quoted_span"])
               for rule in rules if (value := evaluate(rule, record, as_of))]
    return {"address_id": address_id, "as_of": as_of,
            "property": record, "jurisdiction": resolve_jurisdiction(record),
            "city_boundary_needs_verification": record["jurisdiction_evidence"] in {"legal_boundary_unverified", "sample_postal_city_assumption_needs_boundary_check", "supplied_legal_city_unverified"},
            "rules": results}
