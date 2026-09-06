"""A validator for the subset of JSON Schema the voice and bands schemas use.

The schema files stay the single source of truth, and the CLI adds no
dependency. Errors name the path of the field that failed.
"""
import json
import re

_TYPES = {"string": str, "integer": int, "number": (int, float),
          "boolean": bool, "array": list, "object": dict}


def _type_ok(value, name):
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    return isinstance(value, _TYPES[name])


def _deref(node, root):
    ref = node.get("$ref")
    if not ref:
        return node
    target = root
    for part in ref.lstrip("#/").split("/"):
        target = target[part]
    return target


def validate_against(value, node, root, path, errors):
    node = _deref(node, root)
    if "oneOf" in node:
        attempts = []
        for branch in node["oneOf"]:
            sub = []
            validate_against(value, branch, root, path, sub)
            if not sub:
                return
            attempts.append(sub)
        # Report the branch that came closest, so the message names one field.
        errors.extend(min(attempts, key=len))
        return
    if "const" in node and value != node["const"]:
        errors.append(f"{path}: expected {json.dumps(node['const'])}, "
                      f"got {json.dumps(value)}")
        return
    if "enum" in node and value not in node["enum"]:
        errors.append(f"{path}: expected one of {', '.join(map(str, node['enum']))}, "
                      f"got {json.dumps(value)}")
        return
    if "type" in node and not _type_ok(value, node["type"]):
        errors.append(f"{path}: expected {node['type']}, "
                      f"got {type(value).__name__}")
        return
    if isinstance(value, str):
        if "pattern" in node and not re.match(node["pattern"], value):
            errors.append(f"{path}: {json.dumps(value)} does not match "
                          f"{node['pattern']}")
        if "minLength" in node and len(value) < node["minLength"]:
            errors.append(f"{path}: must not be empty")
    if isinstance(value, list):
        if "minItems" in node and len(value) < node["minItems"]:
            errors.append(f"{path}: needs at least {node['minItems']} item(s)")
        if "items" in node:
            for i, item in enumerate(value):
                validate_against(item, node["items"], root, f"{path}[{i}]", errors)
    if isinstance(value, dict):
        props = node.get("properties", {})
        for key in node.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required field '{key}'")
        for key, item in value.items():
            if key in props:
                validate_against(item, props[key], root, f"{path}.{key}", errors)
            elif node.get("additionalProperties") is False:
                errors.append(f"{path}: unknown field '{key}'")
            elif isinstance(node.get("additionalProperties"), dict):
                validate_against(item, node["additionalProperties"], root,
                          f"{path}.{key}", errors)
