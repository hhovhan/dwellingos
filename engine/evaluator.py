from datetime import date

from engine.common import LEGAL_CITY_ALIASES
from engine.coverage import check


def resolve_jurisdiction(row):
    postal = row["postal_city"]
    legal_city = row.get("legal_city") or LEGAL_CITY_ALIASES.get(postal, postal)
    evidence = row.get("jurisdiction_evidence")
    return {
        "state": row["state"],
        "postal_city": postal,
        "legal_city": legal_city,
        "city_jurisdiction": f"{legal_city}, {row['state']}",
        "method": evidence or ("audited_postal_alias" if postal != legal_city else "dataset_postal_city_assumed"),
        "confidence": 0.0 if evidence in {"legal_boundary_unverified", "supplied_legal_city_unverified"} else 0.6 if evidence == "sample_postal_city_assumption_needs_boundary_check" or (not evidence and postal == legal_city) else 0.95,
    }


def jurisdiction_matches(rule, jurisdiction):
    return rule["jurisdiction"] in {jurisdiction["state"], jurisdiction["city_jurisdiction"]}


def has_fact(row, field):
    return row.get(field) not in (None, "")


def temporal_result(rule, as_of):
    if rule["status"] == "pending":
        return "pending"
    if rule["status"] == "failed":
        return None
    effective = rule.get("effective_date")
    if effective and date.fromisoformat(as_of) < date.fromisoformat(effective):
        return "not_yet_effective"
    return "applies"


def evaluate(rule, row, as_of):
    if rule["level"] == "city" and row.get("jurisdiction_evidence") in {
        "legal_boundary_unverified", "supplied_legal_city_unverified"
    }:
        return None
    jurisdiction = resolve_jurisdiction(row)
    if not jurisdiction_matches(rule, jurisdiction):
        return None
    result = temporal_result(rule, as_of)
    if result is None:
        return None
    valid_through = rule.get("valid_through")
    if valid_through and date.fromisoformat(as_of) > date.fromisoformat(valid_through):
        return {
            "team_rule_id": rule["team_rule_id"], "result": "unknown",
            "explanation": f"The source states a rate through {valid_through}; the rate for this date needs a newer official source.",
            "missing_coverage_facts": ["current_rate_source"],
            "conflict_flag": bool(rule.get("conflict_flag")),
        }
    # The supplied California statute expressly excludes units under a
    # stricter local rent-control ceiling. Only a verified covered-unit fact
    # permits us to resolve the SF example; a city name alone never does.
    if rule["source_doc_id"] in {"D024", "D080"} and jurisdiction["legal_city"] == "San Francisco":
        rent_status = str(row.get("rent_control_status") or "").lower()
        if rule["source_doc_id"] == "D080":
            if rent_status == "exempt":
                return None
            if rent_status == "covered" and result == "applies":
                return {
                    "team_rule_id": rule["team_rule_id"], "result": "applies",
                    "explanation": "Verified San Francisco rent-control coverage: the city's 1.6% annual adjustment governs this unit for the stated rate window.",
                    "missing_coverage_facts": [], "conflict_flag": True,
                }
        elif rent_status == "covered" and "2026-03-01" <= as_of <= "2027-02-28":
            return {
                "team_rule_id": rule["team_rule_id"], "result": "superseded",
                "explanation": "California Civil Code § 1947.12(d)(3) exempts housing controlled by a stricter local annual cap. With SF rent-control coverage verified, the 1.6% city limit governs instead of the state ceiling.",
                "missing_coverage_facts": [], "conflict_flag": True,
            }
    if rule.get("extraction_mode") == "generic_candidate_reviewed":
        match, missing = check(rule.get("coverage_spec"), row)
        if match is False:
            return None
        if result == "applies" and match is None:
            result = "unknown"
        return {
            "team_rule_id": rule["team_rule_id"], "result": result,
            "explanation": ("Reviewed coverage conditions matched." if match else
                            "Coverage cannot be proven; missing: " + ", ".join(missing)),
            "missing_coverage_facts": missing if match is None else [],
            "conflict_flag": bool(rule.get("conflict_flag")),
        }
    # Jersey City's official coverage page expressly excludes every 1–4 unit
    # property. This is one of the few supplied property facts that can prove a
    # rule does not apply, so do not surface it as a vague "unknown" result.
    if rule["source_doc_id"] == "D036" and has_fact(row, "units"):
        if int(float(row["units"])) <= 4:
            return None
    # New Jersey's $50 application-fee statute excludes one- and two-family
    # dwellings. It also has an actor-specific licensee exception that this
    # property dataset cannot resolve.
    if rule["source_doc_id"] == "D066" and has_fact(row, "units"):
        if int(float(row["units"])) <= 2:
            return None
    # Boston's Fair Chance policy is not a citywide rule. The starter dataset
    # does not identify DND/BPDA program participation, so jurisdiction alone
    # cannot establish coverage.
    if rule["source_doc_id"] == "D010" and result == "applies":
        participation = str(row.get("DND_or_BPDA_program_participation") or "").lower()
        if participation == "no":
            return None
        result = "applies" if participation == "yes" else "unknown"
    # Categories whose supplied evidence governs conduct rather than building
    # characteristics can be resolved from jurisdiction and time alone. Rent,
    # eviction and deposit coverage commonly depend on owner, occupancy, age or
    # unit-count facts that the challenge data does not consistently provide.
    jurisdiction_only_categories = {
        "algorithmic_rent_setting", "application_screening_fees", "screening_restrictions"
    }
    unresolved_fields = []
    if rule["category"] in {"rent_increase_limits", "just_cause_eviction"}:
        unresolved_fields = ["owner_type", "certificate_of_occupancy"]
        if not has_fact(row, "units"): unresolved_fields.append("units")
        if not has_fact(row, "year_built"): unresolved_fields.append("year_built")
    elif rule["category"] == "security_deposits":
        unresolved_fields = ["owner_type"]
        if not has_fact(row, "units"): unresolved_fields.append("units")
    elif rule["source_doc_id"] == "D066":
        unresolved_fields = ["fee_charging_party_role"]
        if not has_fact(row, "units"): unresolved_fields.append("units")
        if result == "applies": result = "unknown"
    elif rule["source_doc_id"] == "D010" and result == "unknown":
        unresolved_fields = ["DND_or_BPDA_program_participation"]
    if result == "applies" and rule["category"] not in jurisdiction_only_categories:
        result = "unknown"
    explanation = (
        f"{rule['jurisdiction']} jurisdiction matched. "
        + ("The rule is not yet effective on this date." if result == "not_yet_effective" else
           "The proposal is pending, not current law." if result == "pending" else
           f"Coverage cannot be proven because these facts are unavailable or source-specific: {', '.join(unresolved_fields)}." if result == "unknown" else
           "The rule applies jurisdiction-wide without a property-age or unit-count condition in the extracted evidence.")
    )
    return {"team_rule_id": rule["team_rule_id"], "result": result, "explanation": explanation,
            "missing_coverage_facts": unresolved_fields if result == "unknown" else [],
            "conflict_flag": bool(rule.get("conflict_flag"))}
