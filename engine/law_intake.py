"""Generate evidence-bound candidates from an unfamiliar law text.

Candidates require review; this module deliberately never publishes law.
"""

import hashlib
import re

from engine.common import CATEGORIES, normalize

ACTION = re.compile(r"\b(shall|must|may not|cannot|prohibit(?:s|ed)?|unlawful|illegal|limit(?:ed|s)?|require(?:s|d)?|maximum|entitled|may only|annual allowable increase|allowable rent increase|rent ceilings? by \d|no (?:city|landlord|owner|person))\b", re.I)
TRIVIAL = re.compile(r"\b(table of contents|legislature finds|for purposes of this section)\b", re.I)


def segments(text):
    """Split ordinary prose and numbered clauses while retaining exact evidence."""
    # Captured web pages often place navigation immediately before a provision.
    # Prefer a complete source line when available so the evidence span does not
    # accidentally include menu labels and unrelated page chrome.
    for line in text.splitlines():
        cleaned = normalize(line)
        if 30 <= len(cleaned) <= 1800:
            yield cleaned
    for paragraph in re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-Z])", text):
        cleaned = normalize(paragraph)
        if 30 <= len(cleaned) <= 1800:
            yield cleaned
        elif len(cleaned) > 1800:
            for clause in re.split(r";\s+|(?<=\.)\s+(?=[A-Z])", paragraph):
                clause = normalize(clause)
                if 30 <= len(clause) <= 1800:
                    yield clause


def extract_candidates(text, *, jurisdiction, source_url, retrieved_at):
    if not source_url.startswith("https://"):
        raise ValueError("source_url must be HTTPS")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2}))?", retrieved_at):
        raise ValueError("retrieved_at must be a dated ISO value")
    if not (jurisdiction in {"CA", "NJ", "MA"} or re.fullmatch(r"[^,]+, [A-Z]{2}", jurisdiction)):
        raise ValueError("jurisdiction must be a state or 'City, ST'")
    # Some legislature URLs capture the bill's listing/history but not its text.
    # A bill title or committee description is not an operative provision.
    if (re.search(r"^Bill [SH]\.\d+\s*$", text, re.M) and "Bill History" in text
            and "View Text" in text and not re.search(r"\b(?:SECTION|Section)\s+\d+\.", text)):
        return []
    candidates = []
    seen_by_category = {}
    body = normalize(text)
    for paragraph in segments(text):
        if not ACTION.search(paragraph) or TRIVIAL.search(paragraph):
            continue
        categories = [category for category, terms in CATEGORIES.items()
                      if any(term in paragraph.lower() for term in terms)]
        for category in categories:
            if paragraph not in body:
                continue
            # A whole-page paragraph can repeat a cleaner source line. Keep
            # the smallest exact evidence span instead of duplicate candidates.
            if any(quote in paragraph for quote in seen_by_category.get(category, ())):
                continue
            seen_by_category.setdefault(category, []).append(paragraph)
            digest = hashlib.sha256(f"{source_url}\n{category}\n{paragraph}".encode()).hexdigest()[:16]
            candidates.append({
                "candidate_id": digest,
                "category": category,
                "jurisdiction": jurisdiction,
                "source_url": source_url,
                "retrieved_at": retrieved_at,
                "quoted_span": paragraph,
                "review_status": "needs_human_review",
                "review_questions": [
                    "Is this operative law or a proposal, summary, exception or amendment?",
                    "What is the effective date and exact coverage test?",
                    "What exemptions, penalties and state/local interactions apply?",
                ],
            })
    return candidates


def approve_candidate(candidate, source_text, *, title, citation, status,
                      coverage_conditions, effective_date=None, exemptions=None,
                      penalty=None, coverage_spec=None):
    """Turn a reviewed candidate into an engine rule after evidence checks."""
    if candidate["review_status"] != "needs_human_review":
        raise ValueError("candidate is not awaiting review")
    if candidate["quoted_span"] not in normalize(source_text):
        raise ValueError("supporting quotation is absent from source text")
    if status not in {"in_force", "not_yet_effective", "pending", "failed"}:
        raise ValueError("invalid law status")
    if not title.strip() or not citation.strip() or not coverage_conditions.strip():
        raise ValueError("title, citation and coverage conditions require review")
    if status == "not_yet_effective" and not effective_date:
        raise ValueError("future law requires an effective date")
    if effective_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", effective_date):
        raise ValueError("effective date must be YYYY-MM-DD")
    if coverage_spec is not None:
        from engine.coverage import check
        check(coverage_spec, {})
    return {
        "team_rule_id": "NEW-" + candidate["candidate_id"],
        "jurisdiction": candidate["jurisdiction"],
        "level": "city" if ", " in candidate["jurisdiction"] else "state",
        "category": candidate["category"], "status": status,
        "title": title.strip(), "requirement": candidate["quoted_span"],
        "key_value": None, "coverage_conditions": coverage_conditions.strip(),
        "exemptions": exemptions, "penalty": penalty,
        "coverage_spec": coverage_spec,
        "overrides": [], "interaction": None, "effective_date": effective_date,
        "citation": citation.strip(), "source_doc_id": "INTAKE-" + candidate["candidate_id"],
        "source_url": candidate["source_url"], "retrieved_at": candidate["retrieved_at"],
        "quoted_span": candidate["quoted_span"], "confidence": None,
        "conflict_flag": False, "conflict_note": None,
        "review_status": "reviewed_candidate", "extraction_mode": "generic_candidate_reviewed",
    }
