"""Validate the subset of JSON Schema used by the organizer's rule schema."""

import re

TYPES = {"string": str, "number": (int, float), "array": list, "object": dict,
         "boolean": bool, "null": type(None)}


def validate_rule(rule, schema):
    errors = []
    for field in schema.get("required", []):
        if field not in rule:
            errors.append(f"missing {field}")
    for field, value in rule.items():
        spec = schema.get("properties", {}).get(field)
        if not spec:
            continue
        type_names = spec.get("type", [])
        type_names = [type_names] if isinstance(type_names, str) else type_names
        if type_names and not any(
            (isinstance(value, TYPES[name]) and not (name == "number" and isinstance(value, bool)))
            for name in type_names
        ):
            errors.append(f"{field} has invalid type")
            continue
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"{field} has invalid value")
        if isinstance(value, str):
            if len(value) < spec.get("minLength", 0):
                errors.append(f"{field} is too short")
            if "pattern" in spec and not re.fullmatch(spec["pattern"], value):
                errors.append(f"{field} has invalid format")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in spec and value < spec["minimum"]:
                errors.append(f"{field} below minimum")
            if "maximum" in spec and value > spec["maximum"]:
                errors.append(f"{field} above maximum")
        if isinstance(value, list) and "items" in spec:
            item_type = spec["items"].get("type")
            if item_type and not all(isinstance(item, TYPES[item_type]) for item in value):
                errors.append(f"{field} contains invalid item")
    return errors
