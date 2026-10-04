import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import AS_OF, CATEGORIES, CORPUS, OUTPUT, ROOT, normalize, read_csv, read_json, source_body, write_json
from engine.law_intake import extract_candidates

SPECIAL_IDS = {
    ("D022", "algorithmic_rent_setting"): "CA-ALG-01",
    ("D069", "algorithmic_rent_setting"): "NJ-ALG-01",
    ("D045", "algorithmic_rent_setting"): "MA-ALG-P2",
    ("D046", "algorithmic_rent_setting"): "MA-ALG-P1",
    ("D081", "algorithmic_rent_setting"): "SF-ALG-01",
    ("D076", "algorithmic_rent_setting"): "SD-ALG-01",
    ("D001", "algorithmic_rent_setting"): "BERK-ALG-01",
}

# Document-level taxonomy is the review gate: a mention of another rule inside a
# statute does not turn that document into a second rule. The rule text itself is
# still extracted from the source, never written here.
DOC_CATEGORY_ALLOWLIST = {
    "D001": {"algorithmic_rent_setting"},
    "D003": {"screening_restrictions"},
    "D004": set(),
    "D005": {"application_screening_fees", "screening_restrictions"},
    "D006": {"rent_increase_limits", "just_cause_eviction"},
    "D007": {"security_deposits"},
    "D008": {"rent_increase_limits"},
    "D009": {"rent_increase_limits", "just_cause_eviction", "security_deposits"},
    "D010": {"screening_restrictions"},
    "D011": {"rent_increase_limits"},
    "D012": {"screening_restrictions"},
    "D013": set(), "D014": {"just_cause_eviction"},
    "D016": {"screening_restrictions"},
    "D022": {"algorithmic_rent_setting"},
    "D023": {"just_cause_eviction"}, "D024": {"rent_increase_limits"},
    "D025": {"security_deposits"}, "D026": {"application_screening_fees"},
    "D027": {"screening_restrictions"}, "D029": {"screening_restrictions"},
    "D031": {"just_cause_eviction"}, "D036": {"rent_increase_limits"},
    "D039": set(), "D040": {"just_cause_eviction"},
    "D041": {"just_cause_eviction"},
    "D042": {"rent_increase_limits"}, "D043": set(),
    "D045": {"algorithmic_rent_setting"}, "D046": {"algorithmic_rent_setting"},
    "D047": set(), "D048": {"rent_increase_limits"},
    "D049": {"screening_restrictions"}, "D050": {"just_cause_eviction"},
    "D051": {"just_cause_eviction"}, "D052": {"security_deposits"},
    "D053": {"just_cause_eviction"}, "D057": set(),
    "D058": {"just_cause_eviction"},
    "D065": {"screening_restrictions"}, "D066": {"application_screening_fees"},
    "D067": {"rent_increase_limits", "just_cause_eviction", "security_deposits"},
    "D068": {"screening_restrictions"}, "D069": {"algorithmic_rent_setting"},
    "D073": {"just_cause_eviction"}, "D076": {"algorithmic_rent_setting"},
    "D078": {"screening_restrictions"}, "D079": {"just_cause_eviction"},
    "D080": {"rent_increase_limits"}, "D081": {"algorithmic_rent_setting"},
    "D082": set(),
    "D083": {"security_deposits"},
    "D084": set(),
    "D085": {"rent_increase_limits", "just_cause_eviction"},
}

SPECIAL_STATUS = {"D011": "failed", "D045": "pending", "D046": "pending", "D047": "pending"}

REVIEW_PROFILES = {
    ("D010", "screening_restrictions"): {"needle": "housing providers agree to the following", "title": "Boston Fair Chance Tenant Selection Policy", "citation": "Boston DND Fair Chance Tenant Selection Policy", "coverage_conditions": "Only DND-funded/land-assisted housing and income-restricted units created under the BPDA Inclusionary Development Policy."},
    ("D011", "rent_increase_limits"): {"needle": "An Act petition for a special law authorizing the city of Boston to implement rent stabilization", "title": "Boston Rent Stabilization Home Rule Petition (failed proposal)", "citation": "Massachusetts House Bill H.3744 (193rd General Court)"},
    ("D012", "screening_restrictions"): {"needle": "In the City of Boston, it’s illegal to discriminate when renting", "title": "Boston Fair Housing Regulations", "citation": "Boston Fair Housing Commission regulations"},
    ("D014", "just_cause_eviction"): {"needle": "requires any landlord planning to end a tenancy agreement to provide the tenant with a Notice of Tenants’ Rights and Resources", "title": "Boston Housing Stability Notification Act", "citation": "Boston Code § 10-11.7", "effective_date": "2020-11-06"},
    ("D001", "algorithmic_rent_setting"): {"needle": "It shall be unlawful for a landlord to use a coordinated pricing algorithm", "title": "Berkeley Coordinated Pricing Algorithms Ordinance", "citation": "Berkeley Municipal Code § 13.63.030", "effective_date": "2026-03-01"},
    ("D003", "screening_restrictions"): {"needle": "prohibits rental housing providers in Berkeley from asking about and using criminal history", "citation": "Berkeley Municipal Code Chapter 13.106"},
    ("D005", "application_screening_fees"): {"needle": "maximum tenant screening fee for 2026", "citation": "Berkeley Municipal Code § 13.78.010", "key_value": "$68.96 in 2026"},
    ("D005", "screening_restrictions"): {"needle": "cannot charge a prospective tenant a screening fee if no rental unit is actually available", "citation": "Berkeley Municipal Code Chapter 13.78"},
    ("D006", "rent_increase_limits"): {"needle": "The maximum AGA is 5%", "citation": "Berkeley Rent Ordinance, Measure BB", "key_value": "Maximum annual general adjustment: 5%"},
    ("D006", "just_cause_eviction"): {"needle": "cannot be evicted unless there is", "citation": "Berkeley Rent Ordinance, Measure BB"},
    ("D007", "security_deposits"): {"needle": "landlords must pay tenants interest on their security deposit", "citation": "Berkeley Rent Ordinance, security-deposit interest"},
    ("D008", "rent_increase_limits"): {"needle": "eligible landlords to increase the 2025 permanent rent ceilings by 1.0%", "title": "Berkeley 2026 Annual General Adjustment", "citation": "Berkeley Rent Stabilization Board 2026 AGA Order", "key_value": "1.0%", "effective_date": "2026-01-01"},
    ("D009", "rent_increase_limits"): {"needle": "Guide to Coverage under Berkeley’s Rent Stabilization", "title": "Guide to Coverage under Berkeley’s Rent Stabilization and Eviction for Just Cause Ordinance"},
    ("D009", "just_cause_eviction"): {"needle": "Guide to Coverage under Berkeley’s Rent Stabilization", "title": "Guide to Coverage under Berkeley’s Rent Stabilization and Eviction for Just Cause Ordinance"},
    ("D009", "security_deposits"): {"needle": "Most units in multifamily properties built before 1980", "title": "Guide to Coverage under Berkeley’s Rent Stabilization and Eviction for Just Cause Ordinance"},
    ("D016", "screening_restrictions"): {"needle": "make it illegal to discriminate against or harass someone because of a protected characteristic", "citation": "California Fair Employment and Housing Act"},
    ("D022", "algorithmic_rent_setting"): {"needle": "make it unlawful for a person to use or distribute a common pricing algorithm", "citation": "Cal. Bus. & Prof. Code §§ 16729, 16756.1", "effective_date": "2026-01-01"},
    ("D023", "just_cause_eviction"): {"needle": "shall not terminate a tenancy without just cause", "citation": "Cal. Civ. Code § 1946.2", "effective_date": None},
    ("D024", "rent_increase_limits"): {"needle": "increase the gross rental rate for a dwelling or a unit more than 5 percent", "citation": "Cal. Civ. Code § 1947.12", "key_value": "Lesser of 5% + cost of living or 10%", "effective_date": None},
    ("D025", "security_deposits"): {"needle": "in excess of an amount equal to one month’s rent", "citation": "Cal. Civ. Code § 1950.5", "key_value": "Generally one month's rent", "effective_date": None},
    ("D026", "application_screening_fees"): {"needle": "shall not be greater than the actual out-of-pocket costs", "citation": "Cal. Civ. Code § 1950.6", "effective_date": None},
    ("D027", "screening_restrictions"): {"needle": "It shall be unlawful", "citation": "Cal. Gov. Code § 12955", "effective_date": None},
    ("D029", "screening_restrictions"): {"needle": "The Fair Housing Ordinance prohibits discrimination in real estate transactions", "title": "Cambridge Fair Housing Ordinance", "citation": "Cambridge Municipal Code Chapter 2.76"},
    ("D031", "just_cause_eviction"): {"needle": "The Ordinance also requires that a landlord provide the Guide to tenants when legal steps to terminate a tenancy are taken", "title": "Cambridge Tenants Rights and Resources Notification Ordinance", "citation": "Cambridge Municipal Code Chapter 8.71"},
    ("D036", "rent_increase_limits"): {"needle": "All 1-4 Unit Properties are exempt from rent control", "title": "Jersey City Rent Control Coverage", "citation": "Jersey City Municipal Code Chapter 260", "key_value": "All 1–4 unit properties exempt"},
    ("D040", "just_cause_eviction"): {"needle": "prohibits terminations of tenancies without just cause", "citation": "Los Angeles Municipal Code, Just Cause Ordinance", "effective_date": "2023-03-27"},
    ("D041", "just_cause_eviction"): {"needle": "All notices to terminate a tenancy for all rental units subject", "citation": "Los Angeles Municipal Code §§ 151.09.C.9, 165.05.B.5", "effective_date": None},
    ("D042", "rent_increase_limits"): {"needle": "effective July 1, 2025, through June 30, 2026 is 3%", "citation": "Los Angeles RSO annual adjustment", "key_value": "3% through 2026-06-30", "effective_date": "2025-07-01", "valid_through": "2026-06-30"},
    ("D045", "algorithmic_rent_setting"): {"needle": "An Act relative to preventing algorithmic rent fixing in the rental housing market", "title": "Massachusetts House algorithmic rent-fixing proposal", "citation": "Massachusetts House Bill H.5222 (194th General Court)"},
    ("D046", "algorithmic_rent_setting"): {"needle": "An Act prohibiting algorithmic rent setting", "title": "Massachusetts Senate algorithmic rent-setting proposal", "citation": "Massachusetts Senate Bill S.2983 (194th General Court)"},
    ("D048", "rent_increase_limits"): {"needle": "No city or town may enact, maintain or enforce rent control of any kind", "title": "Massachusetts Municipal Rent-Control Restriction", "citation": "Mass. Gen. Laws ch. 40P, § 4", "key_value": "Mandatory municipal rent control generally prohibited"},
    ("D049", "screening_restrictions"): {"needle": "For any person furnishing credit, services or rental accommodations to discriminate against any individual who is a recipient of federal, state, or local public assistance", "title": "Massachusetts Housing Anti-Discrimination Law", "citation": "Mass. Gen. Laws ch. 151B, § 4(10)"},
    ("D050", "just_cause_eviction"): {"needle": "Upon the neglect or refusal to pay the rent due under a written lease, fourteen days' notice to quit", "title": "Massachusetts Written-Lease Nonpayment Notice", "citation": "Mass. Gen. Laws ch. 186, § 11", "key_value": "14 days' notice for nonpayment"},
    ("D051", "just_cause_eviction"): {"needle": "Estates at will may be determined by either party by three months' notice in writing", "title": "Massachusetts Tenancy-at-Will Termination Notice", "citation": "Mass. Gen. Laws ch. 186, § 12", "key_value": "Payment interval or 30 days, whichever is longer; special rules apply"},
    ("D052", "security_deposits"): {"needle": "a security deposit equal to the first month's rent", "title": "Massachusetts Security Deposit Limit", "citation": "Mass. Gen. Laws ch. 186, § 15B", "key_value": "Maximum one month's rent", "effective_date": "2025-08-01"},
    ("D053", "just_cause_eviction"): {"needle": "The receipt of any notice of termination of tenancy, except for nonpayment of rent", "title": "Massachusetts Protection Against Retaliatory Termination", "citation": "Mass. Gen. Laws ch. 186, § 18", "key_value": "Six-month rebuttable-presumption window"},
    ("D058", "just_cause_eviction"): {"needle": "A notice to quit for nonpayment of rent given in writing by a landlord to a residential tenant", "title": "Massachusetts Nonpayment Notice-to-Quit Form", "citation": "Mass. Gen. Laws ch. 186, § 31"},
    ("D073", "just_cause_eviction"): {"needle": "A landlord shall not terminate a tenancy without just cause", "title": "San Diego Tenant Protection Ordinance", "citation": "San Diego Municipal Code § 98.0704", "effective_date": "2023-06-24"},
    ("D076", "algorithmic_rent_setting"): {"needle": "It is unlawful for a person to sell, license, or otherwise provide an algorithmic device", "title": "San Diego Automated Rent Price-Fixing Prohibition", "citation": "San Diego Municipal Code § 98.1103"},
    ("D078", "screening_restrictions"): {"needle": "Fair Chance Ordinance protects residents with arrest or conviction history", "citation": "San Francisco Police Code, Fair Chance Ordinance"},
    ("D079", "just_cause_eviction"): {"needle": "a landlord must have a \"just cause\" reason", "citation": "San Francisco Rent Ordinance § 37.9"},
    ("D080", "rent_increase_limits"): {"needle": "annual allowable increase amount effective March 1, 2026", "citation": "San Francisco Rent Board 2026 annual adjustment", "key_value": "1.6%", "effective_date": "2026-03-01", "valid_through": "2027-02-28"},
    ("D081", "algorithmic_rent_setting"): {"needle": "went into effect on October 14, 2024", "citation": "San Francisco Rent Ordinance § 37.10C", "effective_date": "2024-10-14"},
    ("D083", "security_deposits"): {"needle": "Security Deposit Interest: 4.2%", "citation": "San Francisco Rent Board current rates", "key_value": "4.2% interest for 2026-03-01 through 2027-02-28", "effective_date": "2026-03-01", "valid_through": "2027-02-28"},
    ("D085", "rent_increase_limits"): {"needle": "limited to the lower of 3% per year", "citation": "Santa Ana Rent Stabilization Ordinance", "key_value": "Lower of 3% or 80% of CPI change", "effective_date": "2021-11-19"},
    ("D085", "just_cause_eviction"): {"needle": "shall not terminate a tenancy without just cause", "citation": "Santa Ana Just Cause Eviction Ordinance", "effective_date": "2021-11-19"},
    ("D065", "screening_restrictions"): {"needle": "shall not make any oral or written inquiry regarding an applicant’s criminal record prior to making a conditional offer", "title": "New Jersey Fair Chance in Housing Act", "citation": "N.J.S.A. 46:8-55", "effective_date": None},
    ("D066", "application_screening_fees"): {"needle": "shall not require an application or other similar fee to apply to lease or sublease a residential rental property for dwelling purposes, which exceeds $50", "title": "New Jersey Residential Rental Application Fee Limit", "citation": "N.J.S.A. 46:8-18.1", "key_value": "$50 through 2026; CPI adjustment begins in 2027", "effective_date": "2026-05-01"},
    ("D067", "rent_increase_limits"): {"needle": "The State of New Jersey has no laws that establish, govern or control rents", "title": "New Jersey Truth in Renting Guide — Rent Increases", "citation": "N.J. Department of Community Affairs, Truth in Renting Guide"},
    ("D067", "just_cause_eviction"): {"needle": "An eviction is an actual removal of a tenant from the premises", "title": "New Jersey Truth in Renting Guide — Good Cause Eviction", "citation": "N.J.S.A. 2A:18-53 and 2A:18-61.1"},
    ("D067", "security_deposits"): {"needle": "The maximum-security deposit to be collected by the landlord cannot be more than one and one-half times one month’s rent", "title": "New Jersey Security Deposit Limit", "citation": "N.J.S.A. 46:8-21.2", "key_value": "Maximum 1.5 months' rent"},
    ("D068", "screening_restrictions"): {"needle": "The LAD also prohibits housing discrimination based on the source of lawful income", "title": "New Jersey Law Against Discrimination — Housing", "citation": "N.J.S.A. 10:5-12"},
    ("D069", "algorithmic_rent_setting"): {"needle": "It shall be unlawful and a violation of the “New Jersey Antitrust Act,”", "title": "New Jersey FAIR Act", "citation": "N.J.S.A. 56:9-23", "effective_date": "2027-07-01"},
}

def sentences(text):
    compact = normalize(text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z§(\[\u201c])", compact) if len(s.strip()) >= 20]

def best_quote(parts, needles):
    candidates = []
    for index, sentence in enumerate(parts):
        lower = sentence.lower()
        hits = sum(1 for needle in needles if needle in lower)
        force = any(word in lower for word in ("prohibited", "prohibits", "unlawful", "may not", "went into effect"))
        weak = "known and may be cited" in lower or "legislature finds" in lower
        if hits:
            candidates.append((hits + (3 if force else 0) - (3 if weak else 0), -index, sentence))
    return max(candidates)[2][:1200] if candidates else None

def reviewed_quote(parts, needle):
    needle = needle.lower()
    return next((sentence[:1200] for sentence in parts if needle in sentence.lower()), None)

def detect_status(text, doc_id):
    return SPECIAL_STATUS.get(doc_id, "in_force")

def detect_effective(text, doc_id):
    patterns = [
        r"(?:went into effect|effective(?: on)?|takes? effect(?: on)?)\s+(?:on\s+)?([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
        r"effective\s+(\d{4}-\d{2}-\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            raw = match.group(1)
            for fmt in ("%B %d, %Y", "%Y-%m-%d"):
                try:
                    return date.fromisoformat(raw).isoformat() if fmt == "%Y-%m-%d" else datetime.strptime(raw, fmt).date().isoformat()
                except (ValueError, AttributeError):
                    pass
    # AB 325 was chaptered in 2025 and follows California's default Jan 1 effective date.
    if doc_id == "D022":
        return "2026-01-01"
    # The FAIR Act says first day of the twelfth month following 2026-07-20 enactment.
    if doc_id == "D069" and re.search(r"first day of\s+the twelfth month", text, re.I):
        return "2027-07-01"
    return None

def title_for(text, fallback):
    body = source_body(text)
    for line in body.splitlines():
        line = normalize(line)
        if 8 <= len(line) <= 160 and not line.lower().startswith(("skip to", "home", "search")):
            return line
    return fallback

def citation_for(quote, title):
    matches = re.findall(r"(?:§+\s*|Section\s+)(\d[\w.:-]*)", quote, re.I)
    return f"Section {matches[0]}" if matches else title

manifest = read_csv(CORPUS / "corpus_manifest.csv")
rules = []
rejections = []
automated_candidates = []
counter = 1

for row in manifest:
    rel = row.get("text_file", "").strip()
    if not rel:
        continue
    path = CORPUS / rel
    if not path.exists():
        continue
    raw = path.read_text(encoding="utf-8", errors="replace")
    body = source_body(raw)
    # Broad automatic pass is independent of the per-document publication review
    # profiles below. It gives reviewers a reproducible candidate queue for
    # every captured text, including provisions we have not yet approved.
    automated_candidates.extend({"source_doc_id": row["doc_id"], **candidate}
                                for candidate in extract_candidates(
                                    body, jurisdiction=row["jurisdictions"],
                                    source_url=row["url"], retrieved_at=row["retrieved_at"]))
    parts = sentences(body)
    title = title_for(raw, row["doc_id"])
    status = detect_status(body, row["doc_id"])
    effective = detect_effective(body, row["doc_id"])
    if status == "in_force" and effective and effective > AS_OF:
        status = "not_yet_effective"
    for category, keywords in CATEGORIES.items():
        if row["doc_id"] in DOC_CATEGORY_ALLOWLIST and category not in DOC_CATEGORY_ALLOWLIST[row["doc_id"]]:
            continue
        quote = best_quote(parts, keywords)
        profile = REVIEW_PROFILES.get((row["doc_id"], category))
        if profile:
            quote = reviewed_quote(parts, profile["needle"])
        if not quote:
            rejections.append({"doc_id": row["doc_id"], "category": category, "reason": "review_anchor_not_found" if profile else "no_category_evidence"})
            continue
        # Exact evidence invariant: normalized quote must occur in normalized source body.
        if quote not in normalize(body):
            rejections.append({"doc_id": row["doc_id"], "category": category, "reason": "quote_not_in_source"})
            continue
        level = "state" if row["jurisdictions"] in {"CA", "NJ", "MA"} else "city"
        rule_id = SPECIAL_IDS.get((row["doc_id"], category), f"AUTO-{row['doc_id']}-{category[:4].upper()}-{counter:03d}")
        counter += 1
        rules.append({
            "team_rule_id": rule_id,
            "jurisdiction": row["jurisdictions"],
            "level": level,
            "category": category,
            "status": status,
            "title": profile.get("title", title) if profile else title,
            "requirement": quote,
            "key_value": profile.get("key_value") if profile else None,
            "coverage_conditions": profile.get("coverage_conditions", "Jurisdiction match required; property-specific exemptions remain unknown unless proven by supplied data.") if profile else "Jurisdiction match required; property-specific exemptions remain unknown unless proven by supplied data.",
            "exemptions": profile.get("exemptions") if profile else None,
            "overrides": [],
            "interaction": None,
            "effective_date": profile.get("effective_date", effective) if profile else effective,
            "valid_through": profile.get("valid_through") if profile else None,
            "citation": profile.get("citation", citation_for(quote, title)) if profile else citation_for(quote, title),
            "source_doc_id": row["doc_id"],
            "source_url": row["url"],
            "retrieved_at": row["retrieved_at"],
            "quoted_span": quote,
            "penalty": None,
            "extraction_mode": "source_review_anchor" if profile else "keyword_candidate",
            "confidence": 0.72 if any(w in quote.lower() for w in ("shall", "prohibit", "unlawful", "may not")) else 0.58,
            "conflict_flag": row["doc_id"] in {"D001", "D041", "D069"},
            "conflict_note": "Published timing or preemption question requires human review." if row["doc_id"] in {"D001", "D041", "D069"} else None,
            "review_status": (("california_source_reviewed" if row["jurisdictions"] == "CA" or row["jurisdictions"].endswith(", CA") else
                               "new_jersey_source_reviewed" if row["jurisdictions"] == "NJ" or row["jurisdictions"].endswith(", NJ") else
                               "massachusetts_source_reviewed" if row["jurisdictions"] == "MA" or row["jurisdictions"].endswith(", MA") else
                               "city_source_reviewed") if profile else "document_scope_reviewed_evidence_automated"),
        })

supplement_path = ROOT / "sources" / "verified_supplemental.json"
if supplement_path.exists():
    for source in read_json(supplement_path):
        rules.append({
            "team_rule_id": "JC-ALG-01" if source["doc_id"] == "S-JC-ALG" else "HOB-ALG-01",
            "jurisdiction": source["jurisdiction"], "level": "city",
            "category": source["category"], "status": source["status"],
            "title": source["title"], "requirement": source["quoted_span"],
            "key_value": None,
            "coverage_conditions": "Residential rental property within the named city.",
            "exemptions": None, "overrides": [], "interaction": None,
            "effective_date": source["effective_date"], "citation": source["citation"],
            "source_doc_id": source["doc_id"], "source_url": source["source_url"],
            "retrieved_at": source.get("retrieved_at"),
            "quoted_span": source["quoted_span"], "confidence": 0.88,
            "penalty": None, "extraction_mode": "separately_verified_source",
            "conflict_flag": False, "conflict_note": None,
            "review_status": "new_jersey_source_reviewed" if source["jurisdiction"].endswith(", NJ") else "supplemental_source_reviewed",
        })

approved_path = ROOT / "sources" / "approved_new_laws.json"
if approved_path.exists():
    approved = read_json(approved_path)
    known_ids = {rule["team_rule_id"] for rule in rules}
    for rule in approved:
        if rule["team_rule_id"] in known_ids:
            raise ValueError(f"duplicate approved rule ID: {rule['team_rule_id']}")
        known_ids.add(rule["team_rule_id"])
        rules.append(rule)

write_json(OUTPUT / "rules.json", {"generated_at_as_of": AS_OF, "extraction_method": "deterministic corpus extraction plus separately identified verified link-only sources", "rules": rules})
write_json(OUTPUT / "extraction_rejections.json", rejections)
automated_candidates = list({candidate["candidate_id"]: candidate for candidate in automated_candidates}.values())
write_json(OUTPUT / "auto_candidates.json", {"status": "unpublished_automatic_review_queue", "count": len(automated_candidates), "candidates": automated_candidates})
print(f"Extracted {len(rules)} evidence-linked reviewed rules; queued {len(automated_candidates)} automatic candidates; rejected {len(rejections)} unsupported reviewed candidates")
