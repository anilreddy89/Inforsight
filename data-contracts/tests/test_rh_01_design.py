"""Validate RH-01D design artifacts without replaying or evaluating corpora."""
import copy
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / 'data-contracts/rh/v1'
sys.path.insert(0, str(ROOT / 'simulator/src'))
from inforsight_simulator.rules.engine import get_standard_action_catalog


def read(name):
    return json.loads((DESIGN / name).read_text())


class RH01DesignTest(unittest.TestCase):
    def test_catalog_schema_and_historical_pins(self):
        catalog = read('semantic-catalog.json')
        schema = read('semantic-catalog.schema.json')
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        validator.validate(catalog)
        changed = copy.deepcopy(catalog)
        changed['risk_tiers'][0]['max'] = .2
        self.assertFalse(validator.is_valid(changed))
        profile = catalog['preprocessing']
        for path, digest in [('dictionary_path', 'dictionary_sha256'),
                             ('bundle_path', 'bundle_file_sha256')]:
            self.assertEqual(sha256((ROOT / profile[path]).read_bytes()).hexdigest(), profile[digest])
        bundle = json.loads((ROOT / profile['bundle_path']).read_text())
        dictionary = json.loads((ROOT / profile['dictionary_path']).read_text())
        self.assertEqual(profile['bundle_preprocessor'], bundle['preprocessor'])
        self.assertEqual(profile['feature_contracts'], dictionary['features'])

    def test_exact_action_units_match_existing_baseline(self):
        catalog = read('semantic-catalog.json')
        self.assertEqual(len(catalog['actions']), 5)
        for actual, baseline in zip(catalog['actions'], get_standard_action_catalog()):
            self.assertEqual(actual['action_id'], baseline.action_id)
            self.assertEqual(actual['direct_cost_cents'], round(baseline.direct_cost_usd * 100))
            self.assertEqual(actual['personnel_seconds'], round(baseline.personnel_hours * 3600))
            self.assertEqual(actual['channel'], baseline.channel)

    def test_tiers_cover_boundaries_without_overlap(self):
        tiers = read('semantic-catalog.json')['risk_tiers']
        for probability, expected in [(0, 1), (.099, 1), (.1, 2), (.25, 3), (.5, 4), (1, 4)]:
            matches = [t['severity_rank'] for t in tiers if t['min_inclusive'] <= probability
                       and (probability < t['max'] or (t['max_inclusive'] and probability == t['max']))]
            self.assertEqual(matches, [expected])

    def test_fixture_visibility_and_source_arithmetic(self):
        cases = read('acceptance-fixtures.json')['cases']
        self.assertEqual(len({c['id'] for c in cases}), len(cases))
        for case in cases:
            expected = case['expected']
            if 'visible_ids' not in expected:
                continue
            cutoff = datetime.fromisoformat(case['as_of'].replace('Z', '+00:00'))
            visible = [e for e in case['events']
                       if datetime.fromisoformat(e['effective_at'].replace('Z', '+00:00')) <= cutoff
                       and datetime.fromisoformat(e['ingested_at'].replace('Z', '+00:00')) <= cutoff]
            visible.sort(key=lambda e: (e['effective_at'], e.get('occurred_at', ''), e['event_id']))
            with self.subTest(case=case['id']):
                self.assertEqual([e['event_id'] for e in visible], expected['visible_ids'])
                if 'tenure_days' in expected:
                    issuance = datetime.fromisoformat(visible[0]['effective_at'].replace('Z', '+00:00'))
                    self.assertEqual((cutoff - issuance).days, expected['tenure_days'])
                if 'annual_premium_cents' in expected:
                    payload = visible[0]['payload']
                    periods = read('semantic-catalog.json')['billing_periods_per_year']
                    self.assertEqual(payload['premium_amount_cents'] * periods[payload['billing_frequency']], expected['annual_premium_cents'])

    def test_snapshot_schema_rejects_fabricated_safety_and_grace(self):
        schema = read('domain-snapshot.schema.json')
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        snapshot = {
            'snapshot_version': '1.0.0', 'catalog_version': '1.0.0', 'catalog_sha256': '0' * 64,
            'source_profile': 'v6-policy-events/6.0.0', 'snapshot_id': '1' * 64,
            'policy_id': 'fictional-policy', 'as_of': '2026-01-20T00:00:00.000000Z',
            'issued_at': '2020-01-01T00:00:00.000000Z', 'product_type': 'fictional_term_life',
            'status': 'unknown', 'billing_frequency': 'monthly', 'premium_amount_cents': 10000,
            'currency': 'USD', 'annual_premium_cents': 120000, 'tenure_days': 2211,
            'in_grace_period': None, 'days_in_grace': None, 'grace_entered_at': None,
            'days_past_due': None, 'coverage_amount_cents': None, 'total_premiums_paid_cents': None,
            'safety': {k: None for k in schema['properties']['safety']['properties']},
            'provenance': [{'event_id': 'issued', 'event_sha256': '2' * 64}],
            'field_evidence': {'issuance': ['issued'], 'status': [], 'grace': [], 'days_past_due': []},
        }
        validator.validate(snapshot)
        for field, value in [('in_grace_period', False), ('days_in_grace', 0), ('coverage_amount_cents', 25000000)]:
            changed = copy.deepcopy(snapshot)
            changed[field] = value
            self.assertFalse(validator.is_valid(changed), field)
        changed = copy.deepcopy(snapshot)
        changed['safety']['has_legal_hold'] = False
        self.assertFalse(validator.is_valid(changed))


if __name__ == '__main__':
    unittest.main()
