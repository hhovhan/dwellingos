"""Small, auditable coverage predicate language for reviewed new laws."""

ALLOWED_FIELDS = {"units", "year_built", "owner_type", "certificate_of_occupancy", "DND_or_BPDA_program_participation", "rent_control_status", "owner_occupied_shared_kitchen_or_bath"}
ALLOWED_OPERATORS = {"eq", "gte", "lte"}


def check(spec, property_record):
    """Return (True, False or None, missing fields). None means unknown."""
    if spec is None:
        return None, ["coverage_predicate_not_encoded"]
    if not isinstance(spec, list):
        raise ValueError("coverage_spec must be a list")
    missing = []
    for condition in spec:
        field, operator, expected = condition["field"], condition["op"], condition["value"]
        if field not in ALLOWED_FIELDS or operator not in ALLOWED_OPERATORS:
            raise ValueError("unsupported coverage condition")
        actual = property_record.get(field)
        if actual in (None, ""):
            missing.append(field)
            continue
        if operator in {"gte", "lte"}:
            actual, expected = float(actual), float(expected)
        matches = (actual == expected if operator == "eq" else
                   actual >= expected if operator == "gte" else actual <= expected)
        if not matches:
            return False, []
    return (None, missing) if missing else (True, [])
