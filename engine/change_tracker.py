from engine.evaluator import evaluate


def ids(addresses, predicate):
    return sorted(row["address_id"] for row in addresses if predicate(row))


def build_changes(addresses, rules):
    by_id = {rule["team_rule_id"]: rule for rule in rules}
    ca = ids(addresses, lambda row: row["state"] == "CA")
    nj = ids(addresses, lambda row: row["state"] == "NJ")
    ma = ids(addresses, lambda row: row["state"] == "MA")
    local_nj = ids(addresses, lambda row: row["postal_city"] in {"Jersey City", "Hoboken"})

    t1 = [row["address_id"] for row in addresses if row["state"] == "CA"
          and evaluate(by_id["CA-ALG-01"], row, "2025-12-31")["result"] == "not_yet_effective"
          and evaluate(by_id["CA-ALG-01"], row, "2026-01-02")["result"] == "applies"]
    t2 = [row["address_id"] for row in addresses
          if any(evaluate(by_id[rule_id], row, "2026-10-01") for rule_id in ("JC-ALG-01", "HOB-ALG-01"))]
    t3 = [row["address_id"] for row in addresses if row["state"] == "NJ"
          and evaluate(by_id["NJ-ALG-01"], row, "2026-10-01")["result"] == "not_yet_effective"
          and evaluate(by_id["NJ-ALG-01"], row, "2027-07-02")["result"] == "applies"]
    pending = [by_id[rule_id] for rule_id in ("MA-ALG-P1", "MA-ALG-P2")]
    t4 = [row["address_id"] for row in addresses if row["state"] == "MA"
          and all(evaluate(rule, row, "2026-10-01")["result"] == "pending" for rule in pending)]

    assert sorted(t1) == ca
    assert sorted(t2) == local_nj
    assert sorted(t3) == nj
    assert sorted(t4) == ma
    return {
        "T1": {"affected_address_ids": sorted(t1), "conflict_flag_address_ids": [], "notes": "CA rule changes from not_yet_effective to applies across all CA sample addresses."},
        "T2": {"affected_address_ids": sorted(t2), "conflict_flag_address_ids": [], "notes": "City boundary separates Jersey City and Hoboken rules; Newark receives neither."},
        "T3": {"affected_address_ids": sorted(t3), "conflict_flag_address_ids": local_nj, "notes": "NJ FAIR Act changes from not_yet_effective to applies; local-rule preemption requires review."},
        "T4": {"affected_address_ids": sorted(t4), "conflict_flag_address_ids": [], "notes": "Both Massachusetts proposals remain pending; set represents hypothetical coverage if enacted."},
        "T5": {"affected_address_ids": [], "conflict_flag_address_ids": [], "notes": "Failed ballot question produces no live rent-cap result."},
    }
