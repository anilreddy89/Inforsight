"""Policy-event validator shared by simulator tests."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPOSITORY_ROOT / "data-contracts"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def policy_event_validator() -> Draft202012Validator:
    envelope = load_json(CONTRACTS_DIR / "policy-event.schema.json")
    payloads = [
        load_json(path)
        for path in sorted((CONTRACTS_DIR / "payloads").glob("*.schema.json"))
    ]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in payloads
    )
    return Draft202012Validator(
        envelope,
        registry=registry,
        format_checker=FormatChecker(),
    )
