# Automated Test suite for the data-contratcs/policy-event.schema.json data contract.
# Purpose:  Provide confidence that the schema is both correctly written and
#           strictly enfoce the rules of the data contract.
#           Rigorous contract test that enforces the integrity of the
#           project's foundational data structure.
# Contains two main test methods that cover the "happy path" and "unhappy path".

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

# Setup and Initialization
CONTRACTS_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = CONTRACTS_DIR / "policy-event.schema.json"
VALID_EXAMPLES = CONTRACTS_DIR / "examples" / "policy-event" / "valid"
INVALID_EXAMPLES = CONTRACTS_DIR / "examples" / "policy-event" / "invalid"
EXPECTED_INVALID_RESULTS = {
    "malformed-occurred-at.json": ("format", ("occurred_at",)),
    "missing-schema-version.json": ("required", ()),
    "non-utc-ingested-at.json": ("pattern", ("ingested_at",)),
    "unexpected-property.json": ("additionalProperties", ()),
    "unsupported-schema-version.json": ("const", ("schema_version",)),
}

# Load the schema json file
def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


class PolicyEventContractTest(unittest.TestCase):
    # Hook method for setting up class fixture before running tests in the class.
    # 1) Loads the policy-event.schema.json file
    # 2) Performs "meta-check" to valdiate that the schema file itself is valid,
    #    well-frmatted JSON schema according to Draft 2020-12 standard.
    #    Makes sure there are no Syntax errors in the schema.
    # 3) Creates a 'validator' that will be used by all the tests in the class
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA_PATH)
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(
            cls.schema,
            format_checker=FormatChecker(),
        )

    # *** Happy Path test ***
    # This test verifies that data you expect to be correct is, in fact, accepted by the schema.
    # 1) It finds all .json files inside the data-contracts/examples/policy-event/valid/ directory.
    # 2) It iterates through each "valid" example file.
    # 3) For each file, it runs the validator and asserts that the list of validation errors is empty.
    # 4) If any "valid" example produces a validation error, the test fails, i
    #    mmediately signaling a problem with either the example or the schema itself.
    def test_valid_examples_match_contract(self) -> None:
        examples = sorted(VALID_EXAMPLES.glob("*.json"))
        self.assertTrue(examples, "At least one valid example is required")

        for example_path in examples:
            with self.subTest(example=example_path.name):
                errors = list(self.validator.iter_errors(load_json(example_path)))
                self.assertEqual(errors, [], self._format_errors(errors))


    # *** Unhappy Path test ***
    # This is the more sophisticated test. It verifies that data you expect to be incorrect is rejected,
    # and more importantly, that it's rejected for the correct reason.
    #
    # 1) It finds all .json files inside the data-contracts/examples/policy-event/invalid/ directory.
    # 2) It first asserts that the set of invalid example files found on disk exactly matches
    #    the files defined in the EXPECTED_INVALID_RESULTS dictionary.
    #    This ensures no invalid examples are missing their expected failure definition.
    # 3) It then iterates through each "invalid" example.
    # 4) It runs the validator and collects the errors.
    # 5) It looks up the expected failure reason (e.g., const, required) and the field path from the
    #    EXPECTED_INVALID_RESULTS dictionary.
    # 6) Finally, it asserts that the list of actual errors contains the specific, expected error.
    #    This confirms not only that the data failed validation, but that it failed precisely where
    #    and how it was designed to fail.
    def test_invalid_examples_are_rejected(self) -> None:
        examples = sorted(INVALID_EXAMPLES.glob("*.json"))
        self.assertEqual(
            {path.name for path in examples},
            set(EXPECTED_INVALID_RESULTS),
            "Every invalid example must declare its expected failure",
        )

        for example_path in examples:
            with self.subTest(example=example_path.name):
                errors = list(self.validator.iter_errors(load_json(example_path)))
                expected_validator, expected_path = EXPECTED_INVALID_RESULTS[
                    example_path.name
                ]
                matching_errors = [
                    error
                    for error in errors
                    if error.validator == expected_validator
                    and tuple(error.absolute_path) == expected_path
                ]
                self.assertTrue(
                    matching_errors,
                    f"{example_path.name} did not fail for {expected_validator} "
                    f"at {expected_path}: {self._format_errors(errors)}",
                )

    @staticmethod
    def _format_errors(errors: list) -> str:
        return "\n".join(error.message for error in errors)


if __name__ == "__main__":
    unittest.main()
