"""Structural alerts only. No compatibility judgments."""
import posixpath
from ucp_pulse.util import canonical, digest
from urllib.parse import unquote, urlsplit


def escape(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def pointers(before, after, path=""):
    if type(before) is not type(after):
        return [path]
    if isinstance(before, dict):
        found = []
        for key in sorted(before.keys() | after.keys()):
            child = path + "/" + escape(key)
            found.extend([child] if key not in before or key not in after else pointers(before[key], after[key], child))
        return found
    if isinstance(before, list):
        found = []
        for index in range(max(len(before), len(after))):
            child = path + "/" + str(index)
            found.extend([child] if index >= min(len(before), len(after)) else pointers(before[index], after[index], child))
        return found
    return [] if before == after else [path]


def references(value):
    if isinstance(value, dict):
        if isinstance(value.get("$ref"), str):
            yield value["$ref"]
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def dependents(documents, changed):
    inverse = {}
    for name, document in documents.items():
        for ref in references(document):
            p = urlsplit(ref)
            if p.scheme or p.netloc:
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(p.path))) if p.path else name
            if target in documents:
                inverse.setdefault(target, set()).add(name)
    seen, pending = set(), [changed]
    while pending:
        for name in inverse.get(pending.pop(), set()):
            if name not in seen and name != changed:
                seen.add(name)
                pending.append(name)
    return sorted(seen)


def fragment(document, pointer):
    value = document
    try:
        for component in pointer.split("/")[1:]:
            key = component.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) else value[key]
    except (KeyError, IndexError, TypeError, ValueError):
        return {"present": False}
    encoded = canonical(value)
    return {"present": True, "digest": digest(value), "json_fragment": encoded[:1000], "truncated": len(encoded) > 1000}


def alerts(before, after):
    result = []
    for name in sorted(before.keys() | after.keys()):
        changes = pointers(before.get(name), after.get(name))
        if not changes:
            continue
        result.append({"file": name, "classification": "unknown", "pointers": changes,
                       "fragments": [{"pointer": p, "before": fragment(before.get(name), p) if name in before else {"present": False}, "after": fragment(after.get(name), p) if name in after else {"present": False}} for p in changes],
                       "annotations": sorted({key for p in changes for key in ("ucp_request", "ucp_response") if key in p.split("/")}),
                       "dependents": sorted(set(dependents(before, name)) | set(dependents(after, name)))})
    return result
