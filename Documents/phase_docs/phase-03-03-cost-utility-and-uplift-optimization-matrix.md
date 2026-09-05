# Phase 3.03 — Cost-Utility and Uplift Optimization Matrix

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 3 — Policy Conservation Decision Engine & Intervention Orchestration |
| Sequence | 03 |
| Change tracker ID | `P3-03` |
| GitHub issue | [#110](https://github.com/anilreddy89/Inforsight/issues/110) |
| Issue title | `[Implementation] P3-03: Cost-utility and uplift optimization matrix` |
| Branch | `feat/110-p3-03-cost-utility-optimization` |
| Pull request | [#111](https://github.com/anilreddy89/Inforsight/pull/111) |
| Status | Complete (Merged as `a1e97cb`) |
| Milestone | [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4) |
| Priority | Milestone blocking / Foundational |
| Classification | Core Engine / Optimization / Economics |
| Strict predecessor | Phase 3.02 (`1177394`, issue #108, PR #109) |
| Governing predecessor decisions | ADR 0001 (Clean Room), ADR 0002 (Separate Risk Perception from Action Eligibility), ADR 0003 (Local Deterministic Execution) |
| Target release tag | `v0.3.0-decision-engine` |
| Enables | P3-05 (Bounded Case Intelligence Assistant), P3-07 (Interactive Conservation Dashboard), P3-08 (Counterfactual Simulation & Off-Policy Evaluation) |
| Blocks | P3-05, P3-07, P3-08 |
| Last reviewed | 2026-09-05 |

---

## 1. Executive Summary and Problem Statement

### 1.1 Context & Authority Boundary
Phase 3.01 established the formal taxonomy for conservation interventions (`courtesy_reminder`, `grace_period_consultation`, `specialist_phone_outreach`, `payment_method_remediation`, `abstain`), and Phase 3.02 delivered the pure deterministic rules engine producing the immutable `EligibleActionSet` for any given policy context under **ADR 0002**.

While Phase 3.02 answers **"What actions are legally and operationally permissible?"**, Phase 3.03 answers **"Which eligible action generates the highest net economic value, and how should scarce casework capacity be allocated across an entire portfolio?"**

### 1.2 The Economic Optimization Challenge
In real-world life insurance conservation:
1. **Caseworker Scarcity**: Licensed retention specialists are a constrained and expensive operational resource ($65.00 direct cost, 1.0 hr per call). A carrier cannot phone call every at-risk policyholder.
2. **Uplift Heterogeneity**: Not all high-risk policyholders respond to outreach. Contacting a customer who is determined to cancel regardless ("Lost Cause") wastes capacity that could salvage a persuadable customer.
3. **Harm Prevention ("Sleeping Dogs")**: For certain customers, outreach irritates or reminds them of an unneeded recurring cost, accelerating policy cancellation.
4. **Net Economic Utility**: Interventions must only be recommended when the expected economic value of saving the policy strictly exceeds the direct cost and opportunity cost of casework time.

---

## 2. Mathematical Formulation & Uplift Matrix

### 2.1 The Four Uplift Quadrants
For each eligible policy $i$ and intervention candidate $a$, the customer behavioral response is segmented into four canonical treatment quadrants:

| Quadrant | Risk Profile $\hat{p}_i$ | Treatment Effect $\tau_a(X_i)$ | Operational Policy | Recommended Action |
| :--- | :---: | :---: | :--- | :--- |
| **Persuadables** | High ($\hat{p} \ge 0.35$) | Positive ($\tau_a > 0$) | Maximize specialist queue allocation | `specialist_phone_outreach` / `grace_period_consultation` |
| **Lost Causes** | High ($\hat{p} \ge 0.35$) | Near-Zero ($\tau_a \approx 0$) | Suppress high-touch calls; low-cost digital dunning | `courtesy_reminder` or `abstain` |
| **Sure Things** | Low ($\hat{p} < 0.20$) | Near-Zero ($\tau_a \approx 0$) | Avoid unnecessary expense; allow self-cure | `abstain` (or low-cost auto reminder) |
| **Sleeping Dogs** | Any | Negative ($\tau_a < 0$) | Hard prohibition against proactive outreach | Strict `abstain` |

### 2.2 Expected Net Utility Formulation
For policy $i$, candidate action $a \in \mathcal{A}_{\text{eligible}}(i)$, and baseline non-intervention:

$$\mathbb{E}[\Delta U(i, a)] = \tau_a(X_i) \cdot V_{\text{policy}}(i) - c(a)$$

where:
- $V_{\text{policy}}(i)$: Present preserved value of the policy (annual premium in cents or customer lifetime value).
- $\tau_a(X_i) = P(\text{lapse} \mid \text{control}) - P(\text{lapse} \mid a)$: Absolute risk reduction (treatment uplift) resulting from intervention $a$.
- $c(a)$: Direct monetary cost of executing action $a$ (from `conservation-action.schema.json`).

#### Non-Negativity Decision Rule
If $\max_{a \in \mathcal{A}_{\text{eligible}}} \mathbb{E}[\Delta U(i, a)] \le 0$, the optimal recommendation defaults to:
$$a^* = \text{abstain}, \quad \mathbb{E}[\Delta U] = 0$$

### 2.3 Constrained Portfolio Allocation (Greedy Knapsack)
Given a portfolio of $N$ policies evaluated at an observation cutoff:
$$\max \sum_{i=1}^N \mathbb{E}[\Delta U(i, a_i)]$$
subject to:
1. **Action Eligibility**: $a_i \in \mathcal{A}_{\text{eligible}}(i) \quad \forall i$.
2. **Specialist Call Capacity**: $\sum_{i=1}^N \mathbf{1}_{\{a_i \in \mathcal{A}_{\text{specialist}}\}} \le K_{\text{specialist}}$.
3. **Total Financial Budget**: $\sum_{i=1}^N c(a_i) \le B_{\text{total}}$.

The portfolio solver ranks candidates by efficiency ratio:
$$\rho(i, a) = \frac{\mathbb{E}[\Delta U(i, a)]}{\text{resource\_cost}(a)}$$
with deterministic, lexicographical tie-breaking by `(expected_utility DESC, policy_id ASC)`.

---

## 3. Architecture & Module Design

### 3.1 Directory Structure
```text
simulator/src/inforsight_simulator/optimization/
├── __init__.py               # Public exports: UtilityMatrix, UpliftOptimizer, etc.
├── models.py                 # Dataclasses: ActionUtility, OptimalRecommendation, PortfolioAllocation
├── uplift.py                 # Uplift quadrant classifier and treatment effect estimation
├── utility.py                # Net expected utility calculation E[ΔU]
└── solver.py                 # Knapsack / greedy capacity-constrained queue allocation
```

### 3.2 Key Data Structures

#### `ActionUtility`
```python
@dataclass(frozen=True)
class ActionUtility:
    action_type: str
    is_eligible: bool
    treatment_effect: float  # Tau_a(X)
    gross_benefit_usd: float # Tau_a * V_policy
    direct_cost_usd: float   # c(a)
    net_utility_usd: float   # Gross benefit - direct cost
    uplift_quadrant: str     # PERSUADABLE, LOST_CAUSE, SURE_THING, SLEEPING_DOG
```

#### `OptimalRecommendation`
```python
@dataclass(frozen=True)
class OptimalRecommendation:
    policy_id: str
    recommended_action: str
    expected_net_utility_usd: float
    uplift_quadrant: str
    rank_score: float
    authorized_to_act: bool = False  # Hard ADR 0002 boundary
```

#### `PortfolioAllocation`
```python
@dataclass(frozen=True)
class PortfolioAllocation:
    as_of: datetime
    total_budget_usd: float
    specialist_capacity: int
    allocated_specialist_count: int
    allocated_cost_usd: float
    net_portfolio_value_usd: float
    recommendations: tuple[OptimalRecommendation, ...]
```

---

## 4. Acceptance Criteria

- [x] Optimization engine ingests `EligibleActionSet` from P3-02; disqualified actions are strictly prohibited from recommendation.
- [x] Policies are classified deterministically into the 4 uplift quadrants based on risk and treatment responsiveness.
- [x] Negative expected net utility ($\mathbb{E}[\Delta U] \le 0$) defaults strictly to `abstain`.
- [x] Portfolio allocation strictly respects specialist queue limits ($K_{\text{specialist}}$) without overflow.
- [x] Priority ranking and allocation are 100% byte-deterministic across identical input portfolios.
- [x] "Lost Causes" are diverted away from scarce specialist call queues.
- [x] Recommendations maintain ADR 0002 non-authority marker (`authorized_to_act: false`).
- [x] Unit and optimization property tests pass (`simulator/tests/test_optimization.py`).
- [x] Repository boundary and clean-room checks pass.

---

## 5. Execution Command Reference

```bash
# Run optimization test suite
.venv/bin/python3 -m unittest simulator/tests/test_optimization.py

# Run full repository checks
make check
./scripts/check_repository_boundaries.sh
```

---

## 6. Verification Scorecard (Verified)

| Check | Target Standard | Status |
| :--- | :--- | :--- |
| **Eligibility Adherence** | 0% recommendation of disqualified actions | Verified (100%) |
| **Uplift Quadrant Classification** | Accurate partition of 4 behavioral profiles | Verified (100%) |
| **Non-Negative Utility Invariant** | 100% abstention when net utility <= 0 | Verified (100%) |
| **Queue Capacity Conformance** | Allocated specialist calls <= K_specialist | Verified (100%) |
| **Deterministic Tie-Breaking** | Identical rankings across runs | Verified (100%) |
| **ADR 0002 Non-Authority** | `authorized_to_act == False` on all outputs | Verified (100%) |
| **Simulator Test Suite** | All tests pass | Verified (9/9 optimization tests) |
| **Repository Boundaries** | Zero secret or IP leaks | Verified |

