"""Local project and evidence operations. No network or model dependencies."""
import json
import re
from pathlib import Path


from .exceptions import ContractError  # Re-export for existing callers.


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(json_bytes(value))


def initialize(path, project_id, domain="qft-eft"):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", project_id):
        raise ContractError("id must be a portable nonempty identifier")
    root = Path(path)
    if root.exists() or root.is_symlink():
        raise ContractError("init requires a new path; existing work is never overwritten")
    spec = {
        "schema_version": 1, "id": project_id, "title": project_id,
        "stage": "incubate", "domain": domain, "question": "",
        "theory": {key: ([] if key == "assumptions" else "") for key in
                   ("object", "spacetime_dimension", "signature", "units", "assumptions",
                    "boundary_conditions", "observable", "regulator", "limit_order", "normalization")},
        "claim": {"statement": "", "status": "exploratory", "scope": "",
                  "limitations": [], "forbidden_inferences": []},
        "sources": [],
        "protocol": {"mode": "exploratory", "inputs": [], "command": [],
                     "timeout_seconds": 30, "outputs": ["result.json"], "metrics": [],
                     "disconfirming": "", "independence": "", "failure_interpretation": ""},
        "authorization": {"execution": "local-reviewed-only", "network": False,
                          "publication": "human-only"}}
    root.mkdir(parents=True, exist_ok=False)
    write_new(root / "project.json", spec)
    return {"project_id": project_id, "state": "draft", "executable": False,
            "next": "Define the question and theory; a draft cannot freeze or run."}


from .validation import read_bytes, read_json, safe_path, validate_spec
import hashlib
import tempfile
import shutil


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_snapshot(root):
    root = Path(root)
    raw = read_bytes(safe_path(root, "project.json"))
    from .validation import parse_json
    spec = validate_spec(parse_json(raw))
    inputs = {name: read_bytes(safe_path(root, name)) for name in spec["protocol"]["inputs"]}
    manifest = {"schema_version": 1, "spec_sha256": digest(raw),
                "inputs": {name: digest(data) for name, data in sorted(inputs.items())}}
    freeze_id = digest(json_bytes(manifest))
    return spec, raw, inputs, manifest, freeze_id


def validate_project(root):
    spec, _, _, _, freeze_id = source_snapshot(root)
    return {"status": "valid_contract", "project_id": spec["id"], "freeze_id": freeze_id,
            "scientific_status": spec["claim"]["status"], "scientific_validity": "not_assessed"}


def inventory(directory):
    """Hash a complete tree; no symlinks or special files are evidence."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ContractError("missing or symlink evidence directory")
    result = {}
    for item in sorted(directory.rglob("*")):
        name = item.relative_to(directory).as_posix()
        checked = safe_path(directory, name)
        if checked.is_dir():
            continue
        result[name] = digest(read_bytes(checked))
    return result


def load_freeze(root, freeze_id):
    if not re.fullmatch(r"[0-9a-f]{64}", freeze_id):
        raise ContractError("invalid freeze ID")
    directory = safe_path(root, ".flyfishhep/freezes/" + freeze_id)
    manifest = read_json(safe_path(directory, "manifest.json"))
    if digest(json_bytes(manifest)) != freeze_id:
        raise ContractError("frozen manifest digest mismatch")
    if set(manifest) != {"schema_version", "spec_sha256", "inputs"} or manifest["schema_version"] != 1:
        raise ContractError("invalid frozen manifest")
    raw = read_bytes(safe_path(directory, "project.json"))
    if digest(raw) != manifest["spec_sha256"]:
        raise ContractError("frozen project digest mismatch")
    spec = validate_spec(read_json(directory / "project.json"))
    expected = manifest["inputs"]
    if not isinstance(expected, dict) or set(expected) != set(spec["protocol"]["inputs"]):
        raise ContractError("frozen input inventory mismatch")
    if inventory(safe_path(directory, "inputs")) != expected:
        raise ContractError("frozen input digest mismatch")
    return spec, directory, manifest


def freeze_project(root):
    root = Path(root)
    spec, raw, inputs, manifest, freeze_id = source_snapshot(root)
    directory = safe_path(root, ".flyfishhep/freezes/" + freeze_id)
    if directory.exists():
        load_freeze(root, freeze_id)
        return {"freeze_id": freeze_id, "state": "reused", "scientific_status": spec["claim"]["status"]}
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="pending-", dir=str(directory.parent)))
    try:
        (staging / "project.json").write_bytes(raw)
        for name, data in inputs.items():
            target = safe_path(staging / "inputs", name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        write_new(staging / "manifest.json", manifest)
        staging.rename(directory)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    load_freeze(root, freeze_id)
    return {"freeze_id": freeze_id, "state": "frozen", "scientific_status": spec["claim"]["status"]}
