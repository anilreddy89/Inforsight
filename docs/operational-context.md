# Real-World Life Insurance Conservation & Mathematical Formulation

## 1. Executive Summary

This document provides the operational and mathematical context for **Inforsight**:
1. **The Real-World Operational Reality**: How life insurance policyholder retention ("conservation") works in practice, why customer service and agents proactively telephone customers about missed payments, the economic mechanics of commission chargebacks, and the step-by-step outreach ladder.
2. **The Mathematical Architecture Finalized in Phase 2**: The exact formulations behind the Generation v6 bounded hazard simulator (ADR 0012) and the Platt-calibrated logistic scoring pipeline (Phase 2.08 / Phase 2.10 / Phase 2.11).

---

## 2. Real-World Life Insurance Conservation Operations

### 2.1 Why Life Insurance Lapses Are Unique

Unlike consumer subscription services (streaming platforms, gym memberships, software subscriptions), a life insurance lapse carries severe, often irreversible consequences for both the customer and the insurance carrier:

- **The Accidental Lapse Epidemic**: Industry studies show that a large portion of life insurance lapses are unintended. Common causes include expired credit cards, closed checking accounts, bank routing changes, miscommunication between spouses, or address changes during relocation.
- **Irreversible Coverage Loss**: If a policyholder cancels a digital subscription, they can reactivate it anytime at the prevailing price. If a 45-year-old lets a 20-year term life policy lapse, they cannot simply "restart" it. Getting a new policy requires applying at an older age, undergoing full medical underwriting (blood/urine tests, attending physician statements), and facing significantly higher premiums or potential medical uninsurability due to acquired conditions (e.g., hypertension, diabetes, cardiac events).
- **The "Reinstatement" Barrier**: If a policy lapses past its statutory grace period, reinstating coverage requires submitting an application for reinstatement, answering health questionnaires ("evidence of insurability"), and paying all missed back-premiums with interest. Intercepting a payment hiccup *during* the grace period avoids this costly administrative barrier.
- **Regulatory Mandates & Vulnerable Adult Protection**: State insurance laws (such as California Insurance Code § 10113.71 / SB 568 and New York Insurance Law § 3211) mandate a minimum 30-day (often 60-day) grace period and require carriers to allow policyholders to designate a secondary notification contact (e.g., an adult child or trusted contact) before termination, preventing accidental lapses due to cognitive decline or hospitalization.

### 2.2 Why Customer Service and Agents Make Direct Phone Calls

Outbound calling is a core operational function in life insurance, driven by distinct economic and organizational incentives:

#### A. The Agency Distribution Channel & Commission Chargebacks
* Most individual life insurance policies are sold through career agents or independent brokers.
* **First-Year Commission Structure**: Agents typically receive an upfront commission equal to 50% to 100%+ of the policy's first-year annual premium.
* **The Commission Chargeback**: Under standard agent contracts, if a policy lapses within the first 12 to 24 months, the insurer claws back the unearned commission from the agent on a pro-rata or full basis.
* **Proactive Outreach**: When a premium payment fails, the carrier’s administration system automatically notifies the writing agent via their portal. Agents have an urgent financial and relational incentive to pick up the phone:
  > *"Hi Anil, this is Sarah from ABC Life. I saw that your monthly autopay didn't go through on Monday—did your bank issue a new card recently? Let's get that updated so your family's coverage stays fully protected."*

#### B. The Dedicated Carrier Conservation Department & "Orphan" Policies
* If the writing agent has retired, changed agencies, or left the industry, the policy becomes an **"orphan policy."**
* Carriers operate dedicated in-house **Conservation / Policy Retention Units**. These specialized teams work outbound queues to contact policyholders whose accounts are in arrears or grace status.
* Customer retention has massive return on investment: Customer Acquisition Cost (CAC) for an individual life policy averages \$800–\$1,500+. Preserving an existing in-force policy costs a fraction of acquiring a replacement customer.

---

### 2.3 The 4-Stage Conservation Outreach Ladder

Carriers employ an escalating, multi-channel workflow to resolve payment issues without overwhelming policyholders:

```
[Day 1–5]   Stage 1: Automated Payment Retries & Digital Notifications (Email / SMS)
      │
      ▼
[Day 10–15] Stage 2: Statutory Grace Period Notice (Certified Mail) & Agent Dashboard Alert
      │
      ▼
[Day 20–28] Stage 3: Outbound Human Telephone Call (Agent or In-House Conservation Caseworker)
      │
      ▼
[Day 30–60] Stage 4: Formal Lapse Processing & Reinstatement Kit Dispatch
```

| Stage | Timeline | Channel | Operational Actions |
| :--- | :---: | :---: | :--- |
| **Stage 1: Billing Hiccup** | Days 1–5 | Automated | System initiates scheduled payment retries (dunning logic); triggers transactional email/SMS notifying customer of payment decline. |
| **Stage 2: Statutory Notice** | Days 10–15 | Physical Mail & Agent Portal | Carrier issues legally required written Notice of Grace Period with exact lapse date. Alert pushed to writing agent's dashboard. |
| **Stage 3: Outbound Human Outreach** | **Days 20–28** | **Direct Phone Call** | **The critical intervention window.** Conservation caseworkers or agents call the policyholder to identify root cause (banking change vs. financial hardship) and offer solutions (updating ACH, changing billing cadence, applying cash value, or restructuring face amount). |
| **Stage 4: Post-Lapse Recovery** | Days 31–60+ | Mail & Specialist Phone | Policy enters lapsed status. Reinstatement package mailed; specialized late-stage caseworkers attempt reinstatement before evidence of insurability requirements expire. |

---

## 3. Mathematical Architecture Finalized in Phase 2

### 3.1 The Generation v6 Bounded Sigmoid Hazard Link (ADR 0012)

#### The Root Problem: The Proportional Hazards Trilemma
In Generations v1 through v5 of the simulation engine, event hazards were modeled using an unconstrained exponential link:
$$\lambda(t) = \lambda_0(t) \cdot \exp\left(X\beta + u\right)$$

In an additive log-hazard specification, parameter scaling presents a mathematical deadlock:
1. Scaling $\beta$ large enough to generate realistic discriminative signal ($\text{AUC} \ge 0.70$) causes the exponential term to blow up in the upper tail, driving monthly lapse hazards to $0.25\text{--}0.45$/month. This empties synthetic cohorts prematurely and distorts probability calibration.
2. Restricting $\beta$ small enough to keep monthly hazard below the actuarial maximum ($\lambda_{\text{total}} < 0.20$/month) compresses the score distribution ($\sigma < 0.35$), leaving the candidate ML model unable to distinguish high-risk from low-risk policies ($\text{AUC} \approx 0.52\text{--}0.59$).
3. A systematic grid search across 320 parameter combinations in Phase 2R.14BB confirmed that **0 of 320 configurations** could satisfy both constraints simultaneously.

#### The Mathematical Solution: Bounded Sigmoid Formulation
Phase 2R.14C and ADR 0012 resolved this by replacing the exponential link with a **Bounded Sigmoid (Logistic) Hazard Link**:

$$\lambda_{\text{lapse}}(t) = \lambda_{\max, \text{lapse}} \cdot \sigma\left(z_{\text{lapse}}(t)\right)$$
$$\lambda_{\text{surrender}}(t) = \lambda_{\max, \text{surrender}} \cdot \sigma\left(z_{\text{surrender}}(t)\right)$$

where:
$$\sigma(z) = \frac{1}{1 + \exp\left(-\text{clip}(z, -15.0, 15.0)\right)} \in (0, 1)$$
$$\lambda_{\max, \text{lapse}} = 0.10, \quad \lambda_{\max, \text{surrender}} = 0.05$$

#### Proof of the Upper Hazard Invariant
Because the standard logistic function $\sigma(z)$ is strictly bounded in $(0, 1)$ for all $z \in \mathbb{R}$:
$$\lambda_{\text{total}}(t) = \lambda_{\text{lapse}}(t) + \lambda_{\text{surrender}}(t) < 0.10 + 0.05 = \mathbf{0.1500} < 0.2000 \quad \forall X \in \mathbb{R}^d, u \in \mathbb{R}$$

This guaranteed that the maximum possible monthly event hazard can never exceed **0.1500** by mathematical construction, completely decoupling discriminative signal strength from upper-tail hazard explosion.

---

### 3.2 Production Inference & Probability Calibration Pipeline

The final model bundle (`docs/experiments/phase-02-10-model-bundle.json`) scores policy observations through a deterministic two-stage pipeline:

```
[Raw Observations] ──> [Standard Scaling & One-Hot Encoding] (27 cols)
                                    │
                                    ▼
                     [Linear Dot Product: z = β₀ + βᵀX]
                                    │
                                    ▼
             [Platt Scaling Calibration: p̂ = σ(A·z + B)]
                                    │
                                    ▼
                  [Capacity-Constrained Queue Triage]
```

#### Stage 1: Point-in-Time Preprocessing & Linear Predictor
The model ingests 17 point-in-time features (13 numeric features standard-scaled and 4 categorical features one-hot encoded, expanding to dimension $D = 27$):
$$z = \beta_0 + \sum_{j=1}^{27} \beta_j X_j$$
where $\beta_0 = -0.7107$ and $\beta \in \mathbb{R}^{27}$ are frozen weights trained via $L_2$-regularized Logistic Regression ($C=1.0$, `liblinear`, seed `20260817`).

#### Stage 2: Post-Hoc Platt Scaling Calibration
Raw logistic regression scores can exhibit slight miscalibration under class imbalance and $L_2$ shrinkage. In Phase 2.08, a univariate Platt calibrator was fit over the linear logits on an independent calibration partition (8,560 policies, seed `20280201`):

$$\hat{p} = \sigma\left(A \cdot z + B\right) = \frac{1}{1 + \exp\left(-(A \cdot z + B)\right)}$$

where:
$$A = 0.961849, \quad B = -0.033420$$

This transformation:
- Preserves relative ranking and ROC AUC exactly ($\Delta \text{AUC} \le 10^{-6}$).
- Achieved an **Expected Calibration Error (ECE) of 0.0115** (1.15% average deviation across 10 quantile bins, beating the $\le 0.0300$ contract gate).
- Delivered a **calibration slope of 0.9498** (conforming to the governed $[0.85, 1.15]$ requirement).

---

## 4. Operational Triage Queues & Resource Allocation

### 4.1 Why the Default 0.50 Threshold Fails in Production

A standard machine learning classifier defaults to a decision threshold of $\hat{p} \ge 0.50$. In life insurance conservation:
- Baseline lapse prevalence is approximately **7% to 10% annually** (~2% to 3% quarterly).
- A model with an unadjusted 0.50 decision boundary flags virtually zero policies, rendering the system operationally useless.
- Conversely, lowering the threshold arbitrarily to 0.10 flags tens of thousands of policies, completely overwhelming call center capacity.

### 4.2 Capacity-Constrained Review Queues

Inforsight structures calibrated probabilities into operational review queues aligned with realistic staffing budgets:

$$\mathbb{E}[\text{Net Benefit}] = \sum_{i \in \text{Queue}} \left( \hat{p}_i \cdot P(\text{Cure} \mid \text{Call}) \cdot \text{CLV}_i - C_{\text{call}} \right)$$

| Operational Queue | Model Cutoff | Population Share | Out-of-Sample Precision | Out-of-Sample Lift | Number Needed to Review (NNR) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Top 1% Triage** | $\hat{p} \ge 0.4542$ | Top 1% (88 policies) | **34.09%** | **2.23×** | **2.93** |
| **Top 5% Priority** | $\hat{p} \ge 0.3459$ | Top 5% (439 policies) | **35.31%** | **2.31×** | **2.83** |
| **Top 20% Screening** | $\hat{p} \ge 0.2402$ | Top 20% (1,756 policies) | **30.24%** | **1.98×** | **3.31** |

* **Lift of 2.31×** means caseworkers reviewing the Top 5% queue intercept **over 2.3 times more true lapses** than random outreach.
* **NNR of 2.83** means a conservation specialist needs to contact fewer than 3 policyholders to prevent one policy termination, maximizing caseworker efficiency.

---

## 5. Governance & Action Authority (ADR 0002)

To maintain strict regulatory compliance and ethical standards, model outputs adhere to a 4-tier separation of authority:
1. **Tier 1 (Perception Layer)**: The ML model outputs risk probabilities $\hat{p}$ and SHAP attributions solely for situational awareness. It possesses **zero autonomous execution authority**.
2. **Tier 2 (Deterministic Policy Rules)**: Business logic verifies operational prerequisites (e.g., active grace period, no opt-out flag, communication frequency caps, licensed jurisdiction).
3. **Tier 4 (Licensed Human Review)**: Every customer intervention (phone call, restructured premium plan, grace extension) requires explicit review and execution by a licensed human conservation specialist.
