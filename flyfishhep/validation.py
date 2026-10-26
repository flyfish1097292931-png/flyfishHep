"""Strict validation of the v1 executable contract; no scientific truth oracle."""
import json
import math
import re
from pathlib import Path, PurePosixPath

from .exceptions import ContractError

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_JSON_DEPTH = 128
STAGES = {"incubate", "construct", "validate", "write", "suspended"}
STATUSES = {"definition", "cited", "exploratory", "conjectural", "derived", "numerical",
            "checked", "regulator-dependent", "heuristic", "toy-model", "limitation", "unsafe"}
THEORY = {"object", "spacetime_dimension", "signature", "units", "assumptions",
          "boundary_conditions", "observable", "regulator", "limit_order", "normalization"}


def fail(message):
    raise ContractError(message)


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        fail(label + " must be a nonempty string")
    return value


def strings(value, label, nonempty=True):
    if not isinstance(value, list) or (nonempty and not value):
        fail(label + " must be a " + ("nonempty " if nonempty else "") + "list")
    for item in value:
        text(item, label)
    return value


def fields(value, required, label):
    if not isinstance(value, dict):
        fail(label + " must be an object")
    if set(value) != set(required):
        fail(label + " fields mismatch: missing=" + str(sorted(set(required) - set(value)))
             + "; unknown=" + str(sorted(set(value) - set(required))))


def enum(value, choices, label):
    if not isinstance(value, str) or value not in choices:
        fail(label + " has an unsupported value")


def identifier(value, label="id"):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value):
        fail(label + " must be a portable identifier")
    return value


def number(value, label):
    if type(value) not in (int, float):
        fail(label + " must be a finite real number, not a boolean")
    try:
        if not math.isfinite(value):
            fail(label + " must be finite")
    except OverflowError:
        fail(label + " exceeds supported numerical range")
    return value


def relative(value):
    text(value, "path")
    p = PurePosixPath(value)
    if (p.is_absolute() or "\\" in value or ":" in value or "\x00" in value
            or any(part in ("", ".", "..") for part in value.split("/"))):
        fail("path must be a normalized relative POSIX path")
    return p


def safe_path(root, value):
    """Reject traversal and every symlink component, including existing targets."""
    parts = relative(value).parts
    root = Path(root)
    if root.is_symlink():
        fail("symlink root refused")
    candidate = root
    for part in parts:
        candidate = candidate / part
        if candidate.is_symlink():
            fail("symlink path refused: " + value)
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        fail("path escapes its root")
    return candidate


def read_bytes(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        fail("missing or non-regular file: " + path.name)
    if path.stat().st_size > MAX_FILE_BYTES:
        fail("file exceeds local evidence size limit: " + path.name)
    with path.open("rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        fail("file grew beyond local evidence size limit")
    return data


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("duplicate JSON key: " + key)
        result[key] = value
    return result


def parse_json(data):
    try:
        result = json.loads(data, object_pairs_hook=_unique,
                          parse_float=lambda token: number(float(token), "JSON number"),
                          parse_constant=lambda token: fail("nonfinite JSON literal: " + token))
    except RecursionError as exc:
        raise ContractError("JSON depth exceeds limit of " + str(MAX_JSON_DEPTH)) from exc
    except ContractError:
        raise
    except ValueError as exc:
        raise ContractError("invalid JSON: " + str(exc)) from exc
    # Count containers, not scalar leaves; never recurse over decoded input.
    pending = [(result, 1)]
    while pending:
        value, depth = pending.pop()
        if isinstance(value, (dict, list)):
            if depth > MAX_JSON_DEPTH:
                fail("JSON depth exceeds limit of " + str(MAX_JSON_DEPTH))
            children = value.values() if isinstance(value, dict) else value
            pending.extend((child, depth + 1) for child in children
                           if isinstance(child, (dict, list)))
    return result


def read_json(path):
    return parse_json(read_bytes(path))


def validate_spec(spec):
    fields(spec, {"schema_version", "id", "title", "stage", "domain", "question", "theory",
                  "claim", "sources", "protocol", "authorization"}, "project")
    if type(spec["schema_version"]) is not int or spec["schema_version"] != 1:
        fail("unsupported schema_version")
    identifier(spec["id"])
    for key in ("title", "domain", "question"):
        text(spec[key], key)
    enum(spec["stage"], STAGES, "stage")
    fields(spec["theory"], THEORY, "theory")
    for key, value in spec["theory"].items():
        if key == "assumptions":
            strings(value, "theory.assumptions")
        else:
            text(value, "theory." + key)
    claim = spec["claim"]
    fields(claim, {"statement", "status", "scope", "limitations", "forbidden_inferences"}, "claim")
    enum(claim["status"], STATUSES, "claim.status")
    for key in ("statement", "scope"):
        text(claim[key], "claim." + key)
    for key in ("limitations", "forbidden_inferences"):
        strings(claim[key], "claim." + key)
    sources = spec["sources"]
    if not isinstance(sources, list):
        fail("sources must be a list")
    ids = set()
    for source in sources:
        fields(source, {"id", "identifier", "revision", "locator", "relation", "verification"}, "source")
        identifier(source["id"], "source id")
        if source["id"] in ids:
            fail("duplicate source id")
        ids.add(source["id"])
        for key in ("identifier", "revision", "locator"):
            text(source[key], "source." + key)
        enum(source["relation"], {"background", "antecedent", "competitor", "limitation"}, "source.relation")
        enum(source["verification"], {"metadata-only", "read", "reproduced", "unknown"}, "source.verification")
    p = spec["protocol"]
    fields(p, {"mode", "inputs", "command", "timeout_seconds", "outputs", "metrics",
               "disconfirming", "independence", "failure_interpretation"}, "protocol")
    enum(p["mode"], {"exploratory", "confirmatory"}, "protocol.mode")
    for key in ("disconfirming", "independence", "failure_interpretation"):
        text(p[key], "protocol." + key)
    for key in ("inputs", "outputs"):
        strings(p[key], "protocol." + key)
        if len({x.casefold() for x in p[key]}) != len(p[key]):
            fail("duplicate or case-colliding " + key)
        for name in p[key]:
            relative(name)
            if name.split("/")[0] in {".flyfishhep", ".git", ".env"} or name == "project.json":
                fail("reserved input/output path")
        for name in p[key]:
            if any(other != name and other.startswith(name + "/") for other in p[key]):
                fail("overlapping file and directory paths")
    if "result.json" not in p["outputs"]:
        fail("outputs must include result.json")
    command = strings(p["command"], "protocol.command")
    if (len(command) < 2 or command[0] != "{python}" or command[1] not in p["inputs"]
            or not command[1].endswith(".py")):
        fail("command must invoke {python} and a declared .py input")
    for arg in command[1:]:
        if ("{" in arg or "}" in arg) and arg != "{output}":
            fail("unsupported command placeholder")
        if arg.startswith(("/", "~")) or "\x00" in arg:
            fail("absolute/personal command argument refused")
    timeout = number(p["timeout_seconds"], "timeout_seconds")
    if not 0 < timeout <= 3600:
        fail("timeout_seconds must be in (0, 3600]")
    if not isinstance(p["metrics"], list) or not p["metrics"]:
        fail("protocol.metrics must be nonempty; an empty check cannot pass")
    keys = set()
    for rule in p["metrics"]:
        fields(rule, {"key", "op", "threshold"}, "criterion")
        identifier(rule["key"], "metric key")
        if rule["key"] in keys:
            fail("duplicate criterion key")
        keys.add(rule["key"])
        enum(rule["op"], {"le", "ge", "eq"}, "criterion.op")
        number(rule["threshold"], "criterion.threshold")
    auth = spec["authorization"]
    fields(auth, {"execution", "network", "publication"}, "authorization")
    if (auth["execution"] != "local-reviewed-only" or auth["network"] is not False
            or auth["publication"] != "human-only"):
        fail("v0.1 requires local-reviewed-only / no network / human-only publication")
    return spec
