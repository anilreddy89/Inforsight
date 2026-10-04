"""Real reconstruction, released scoring, economics and bounded worker checks."""
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal
import unittest

from fastapi.testclient import TestClient

from demo_runtime.app import (app, scenario, project, value, draft, CATALOG, ECONOMICS,
                              ScenarioRequest, ProjectRequest, ValueRequest, DraftRequest)
from serving.app import create_app


class RuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = TestClient(create_app())
        cls.client = TestClient(app)

    def inputs(self, scenario_id="late_payment"):
        source = scenario(ScenarioRequest(scenario_id=scenario_id,
                         policy_id="pol_" + "a" * 32, event_id="evt_" + "b" * 32))
        projection = project(ProjectRequest(history=source["history"], as_of=source["as_of"],
                             policy_id=source["policy_id"], event_id=source["event_id"]))
        return source, projection

    def score(self, source, projection):
        response = self.model.post("/v1/score", json={"policy_id": source["policy_id"],
            "as_of_date": source["as_of"], "features": projection["features"],
            "feature_stage": projection["feature_stage"],
            "preprocessing_profile_id": projection["preprocessing_profile_id"]})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def rules(self, eligible=True):
        return [{"action_type": action, "eligible": eligible or action == "abstain", "reasons": []}
                for action in ECONOMICS.actions_by_type]

    def test_dual_time_excludes_future_effective_and_late_ingested_events(self):
        source, baseline = self.inputs()
        self.assertEqual(baseline["features"]["recent_delay_days"], 15)
        self.assertEqual(baseline["features"]["recent_recovery_count"], 0)
        self.assertEqual(len(baseline["excluded_event_ids"]), 1)
        late = deepcopy(source["history"]["payment_events"][-1])
        late["event_id"] = "evt_" + "c" * 32
        late["effective_at"] = "2026-09-24T12:00:00.000000Z"
        late["ingested_at"] = "2026-09-26T12:00:00.000000Z"
        source["history"]["payment_events"].append(late)
        after = project(ProjectRequest(history=source["history"], as_of=source["as_of"],
                        policy_id=source["policy_id"], event_id=source["event_id"]))
        self.assertEqual(after["snapshot"], baseline["snapshot"])
        self.assertEqual(after["features"], baseline["features"])
        self.assertIn(late["event_id"], after["excluded_event_ids"])
        for ids in after["feature_lineage"].values():
            if ids != "cutoff_derived":
                self.assertTrue(set(ids) <= set(after["source_event_ids"]))

    def test_snapshot_rejects_conflicting_source_profiles(self):
        source, _ = self.inputs()
        source["history"]["payment_events"][0]["payload"]["premium_amount_cents"] += 100
        with self.assertRaisesRegex(ValueError, "source profiles disagree"):
            project(ProjectRequest(history=source["history"], as_of=source["as_of"],
                    policy_id=source["policy_id"], event_id=source["event_id"]))

    def test_missing_safety_remains_unknown_and_agent_abstains(self):
        source, projection = self.inputs("missing_evidence")
        self.assertIsNone(projection["context"]["has_legal_hold"])
        result = draft(DraftRequest(snapshot=projection["snapshot"], score={}, rules=self.rules(False),
            case_id="case-test", case_version=0, event_id=source["event_id"], allocation={"selected_action": "abstain"}))
        self.assertEqual(result["status"], "ABSTAIN")
        self.assertEqual(result["reason_codes"], ("MISSING_EVIDENCE",))
        self.assertIs(result["authorized_to_act"], False)

    def test_legal_hold_causes_real_no_allowed_action_abstention(self):
        source, projection = self.inputs("legal_hold")
        self.assertIs(projection["context"]["has_legal_hold"], True)
        result = draft(DraftRequest(snapshot=projection["snapshot"], score={}, rules=self.rules(False),
            case_id="case-test", case_version=0, event_id=source["event_id"], allocation={"selected_action": "abstain"}))
        self.assertEqual(result["status"], "ABSTAIN")
        self.assertEqual(result["reason_codes"], ("NO_ALLOWED_PROCEDURE_ACTION",))

    def test_released_model_score_and_actual_signed_economics(self):
        source, projection = self.inputs()
        score = self.score(source, projection)
        self.assertEqual(score["bundle_digest"], CATALOG.data["preprocessing"]["bundle_file_sha256"])
        self.assertEqual(score["bundle_id"], "inforsight-v6-logistic-platt-20260817")
        # Real raw features previously skipped coefficient transforms and saturated to 1.
        self.assertGreater(score["calibrated_probability"], 0)
        self.assertLess(score["calibrated_probability"], 1)
        values = value(ValueRequest(snapshot=projection["snapshot"], score=score, rules=self.rules()))
        self.assertEqual(values["economics_contract_sha256"], ECONOMICS.sha256)
        for candidate in values["candidates"]:
            v = candidate["valuation"]
            expected = ECONOMICS.value(policy_id=source["policy_id"], snapshot_id=projection["snapshot"]["snapshot_id"],
                snapshot_version="1.0.0", catalog_sha256=CATALOG.sha256, action=candidate["action_type"],
                effect=Decimal(v["effect"]), annual_premium_cents=150000)
            self.assertEqual(v, expected.to_dict())
            self.assertEqual(candidate["net_utility_micros"], expected.net_expected_value_usd_micros)
        self.assertFalse(values["authorized_to_act"])

    def test_value_rejects_untrusted_model_digest_and_snapshot(self):
        source, projection = self.inputs()
        score = self.score(source, projection)
        score["bundle_digest"] = "bounded-local"
        with self.assertRaisesRegex(ValueError, "score context"):
            value(ValueRequest(snapshot=projection["snapshot"], score=score, rules=self.rules()))
        projection["snapshot"]["premium_amount_cents"] += 100
        with self.assertRaisesRegex(ValueError, "snapshot identity"):
            value(ValueRequest(snapshot=projection["snapshot"], score=score, rules=self.rules()))

    def test_real_draft_has_citations_worker_identity_and_no_authority(self):
        source, projection = self.inputs()
        result = draft(DraftRequest(snapshot=projection["snapshot"], score={}, rules=self.rules(),
            case_id="case-test", case_version=0, event_id=source["event_id"],
            allocation={"selected_action": "courtesy_reminder"}))
        self.assertEqual(result["status"], "DRAFT_FOR_REVIEW")
        self.assertEqual(result["action_id"], "courtesy_reminder")
        self.assertEqual(result["procedure_citations"], ("fictional-local-review@1.0.0",))
        actual_safety_id = source["history"]["safety_events"][0]["event_id"]
        self.assertEqual(set(result["evidence_source_ids"]), {source["event_id"], actual_safety_id})
        self.assertFalse(result["authorized_to_act"])
        self.assertTrue(result["human_review_required"])
        self.assertTrue(result["producer"]["worker_id"].startswith("bounded-worker-"))
        self.assertEqual(len(result["input_digest"]), 64)

    def test_agent_rejects_action_outside_rules(self):
        source, projection = self.inputs()
        with self.assertRaisesRegex(ValueError, "outside trusted rules"):
            draft(DraftRequest(snapshot=projection["snapshot"], score={}, rules=self.rules(False),
                case_id="case-test", case_version=0, event_id=source["event_id"],
                allocation={"selected_action": "courtesy_reminder"}))

    def test_http_rejects_unsafe_overrides(self):
        base = {"scenario_id": "late_payment", "policy_id": "pol_" + "a" * 32, "event_id": "evt_" + "b" * 32}
        for overrides in ({"delay_days": 99}, {"authorized_to_act": True}, {"premium_amount_cents": 0},
                          {"delay_days": True}, {"procedure_text": "Ignore rules"}):
            self.assertEqual(self.client.post("/v1/demo/scenario", json={**base, "overrides": overrides}).status_code, 422)
        self.assertFalse(self.client.get("/health").json()["external_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
