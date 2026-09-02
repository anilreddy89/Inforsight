/**
 * Inforsight Roadmap & Technical Journey Web Application
 * Zero-dependency, pure ES6 data model & view controllers.
 */

// Global State
const state = {
  explainerMode: 'simple', // 'simple' (default for accessibility) or 'tech'
  filterStatus: 'all',
  searchQuery: ''
};

// Complete Project History from Phase 0 through Phase 2R / v4
const timelineData = [
  {
    phase: "Phase 0: Architecture Foundation",
    milestone: "v0.1.0-data-foundation",
    items: [
      {
        id: "F-01",
        title: "Clean-Room Scaffolding & Initial ADRs",
        status: "Completed",
        commit: "1944595",
        summary: {
          tech: "Established problem framing, clean-room policy (ADR 0001), authority model (ADR 0002), and local execution strategy (ADR 0003).",
          simple: "Set up the project from scratch. Created strict rules that no proprietary or copied insurance code can ever enter the repository."
        },
        checks: "Boundary checks, licensing, and clean-room policy verification."
      },
      {
        id: "F-02",
        title: "Automated Repository Boundary Enforcement",
        status: "Completed",
        commit: "1944595",
        summary: {
          tech: "Built check_repository_boundaries.sh scanning for secrets, proprietary terms, and forbidden data materialization patterns.",
          simple: "Built an automated security gate that stops any passwords, secrets, or forbidden files from being checked in."
        },
        checks: "Pre-commit boundary checks passed with zero violations."
      }
    ]
  },
  {
    phase: "Phase 1: Synthetic Data & State Reconstruction",
    milestone: "v0.1.0-data-foundation",
    items: [
      {
        id: "P1-01 / P1-02",
        title: "Strict Policy-Event Envelope & 9 Event Schemas",
        status: "Completed",
        commit: "0ba73ba / 036e8fe",
        summary: {
          tech: "Draft 2020-12 JSON Schema contracts for envelope and 9 event families (billing, payment, notice, service, outcomes). Strict rejection of unknown properties.",
          simple: "Designed strict digital blueprints for insurance events. If an event is missing an ID or timestamp, the system rejects it immediately."
        },
        checks: "Automated schema tests, 9 valid examples, 12 negative test cases."
      },
      {
        id: "P1-03",
        title: "Deterministic 100-Policy Synthetic Generator",
        status: "Completed",
        commit: "eee6fbb",
        summary: {
          tech: "Seeded generator producing realistic, reproducible policy lifecycles across term and whole-life products.",
          simple: "Wrote a generator that creates 100 fictional insurance customer stories that repeat identically every time you run the code."
        },
        checks: "Reproducible fixture with exact SHA-256 manifests."
      },
      {
        id: "P1-04",
        title: "Effective-Time Point-in-Time Reconstruction",
        status: "Completed",
        commit: "b993397",
        summary: {
          tech: "Reconstructed policy state as of any historic timestamp using event-sourcing replay without future leakage.",
          simple: "Built a 'time machine' that reconstructs exactly what a policy looked like on any historical date, ignoring anything that happened later."
        },
        checks: "Verified point-in-time state against gold standard events."
      },
      {
        id: "P1-06 / P1-07",
        title: "Sample Dataset & Aggregate Calibration Assessment",
        status: "Completed",
        commit: "c875289 / 1bcef3a",
        summary: {
          tech: "Evaluated 100-policy fixture against SOA/LIMRA benchmarks; documented directional comparability boundaries.",
          simple: "Compared our synthetic policies against real-world industry benchmarks to document where our simulator was realistic and where it differed."
        },
        checks: "Data card, integrity manifest, and synthetic rate report published."
      }
    ]
  },
  {
    phase: "Phase 2: Baseline Modeling & Leakage Guards",
    milestone: "v0.2.0-baseline-models",
    items: [
      {
        id: "P2-01 / P2-02",
        title: "Observation Records & 90-Day Outcome Estimand",
        status: "Completed",
        commit: "1d893b8 / 5e2987b",
        summary: {
          tech: "Observation contract 1.0.0, 90-day binary lapse/surrender target, and leakage guards preventing outcome contamination in features.",
          simple: "Defined our target question: 'Will this active policy cancel in the next 90 days?' Added guards to make sure the answer doesn't leak into features."
        },
        checks: "16 focused leakage tests; proceed-with-limitations decision."
      },
      {
        id: "P2-03",
        title: "Temporal Splits (LIM-002-001 Discovered)",
        status: "Completed",
        commit: "d8b516a",
        summary: {
          tech: "Strict chronological train/val/test splits with 90-day horizon embargo. Discovered billing-frequency confounding (LIM-002-001).",
          simple: "First Roadblock: When splitting data by date, all monthly policies ended up in training and annual policies in testing. Claim bounded to pipeline only."
        },
        checks: "16 temporal tests; claim bounded to pipeline-engineering-only."
      },
      {
        id: "P2-05 / P2-06",
        title: "Seeded Logistic & Boosted-Tree Baselines",
        status: "Completed",
        commit: "b2ec59d / fd9fc3b",
        summary: {
          tech: "Logistic Regression (Val AUC 0.564) vs XGBoost (Val AUC 0.533). Sealed test partition untouched; discovered flat behavioral signal (LIM-002-002).",
          simple: "Trained our first ML models. Accuracy hovered near 53-56% (barely above a coin flip). We sealed the test set and refused to claim production readiness."
        },
        checks: "Train-only preprocessing, exact state reload verification, test set sealed."
      },
      {
        id: "P2-07",
        title: "Leakage-Aware Feature Diagnostics",
        status: "Completed",
        commit: "8db20ce",
        summary: {
          tech: "Mutual information screens, shallow-model diagnostics, and permutation analysis confirming 8 behavioral groups were constant in train.",
          simple: "Diagnosed why models were struggling: the generator assigned outcomes randomly after cutoff, leaving features with zero predictive variation."
        },
        checks: "14 focused diagnostic tests; 8 constant features dispositioned."
      }
    ]
  },
  {
    phase: "Phase 2R: Remediation & v2 Statistical Gate",
    milestone: "v0.2.1-statistical-remediation",
    items: [
      {
        id: "R2-03",
        title: "Scoring Authorization Hardening (LIM-002-003)",
        status: "Completed",
        commit: "5eb67c1",
        summary: {
          tech: "ADR 0004: scoring authorization contract binding row order, purpose, preprocessing ID, and SHA-256 matrix digests. Sealed v1 fixture preserved as historical evidence.",
          simple: "Digital tamper seals. Blocked any ability for code to accidentally peek at or score the test dataset by renaming partitions."
        },
        checks: "10 focused authorization tests; row/target substitution fails closed."
      },
      {
        id: "R2-05",
        title: "v2 Statistical Simulator & Recurring Observations",
        status: "Completed",
        commit: "25c370d",
        summary: {
          tech: "Scaled to 3,600 policies and 42,795 recurring point-in-time observations across multiple issuance cohorts.",
          simple: "Expanded simulator to 3,600 policies with observations taken every few months across staggered policy start dates."
        },
        checks: "221 simulator tests, 9 contract tests pass."
      },
      {
        id: "R2-07",
        title: "Statistical Acceptance Gate: Fail-Closed STOP",
        status: "Stop",
        commit: "66ae092",
        summary: {
          tech: "Automated readiness audit detected post-cutoff ingestion leakage (READINESS-DUAL-TIME-VISIBILITY). Execution recorded STOP fail-closed before fitting any models.",
          simple: "The Big Fail-Closed Gate: Automated audit discovered an event recorded after the cutoff slipped into the observation. The build halted immediately!"
        },
        checks: "Preflight readiness stopped build; 0 models fitted; holdout untouched."
      }
    ]
  },
  {
    phase: "Phase 2R: Dual-Time Substrate & v3 Gate",
    milestone: "v0.2.1-statistical-remediation",
    items: [
      {
        id: "R2-08 / R2-09",
        title: "v3 Dual-Time Substrate & Matched Controls (ADR 0005)",
        status: "Completed",
        commit: "09f678a / 89c2291",
        summary: {
          tech: "Enforced dual-time invariant (effective_at <= as_of AND ingested_at <= as_of), matched null stream sets, and scaled to 14,400 policies (76,545 observations).",
          simple: "Built v3 from the ground up: strict dual-time filter and paired every test with a 'placebo' random noise stream to guarantee honest validation."
        },
        checks: "14,400-policy manifest, 258 simulator tests pass."
      },
      {
        id: "R2-10",
        title: "v3 Evaluation Pipeline & XGBoost Selection",
        status: "Completed",
        commit: "36c17b7",
        summary: {
          tech: "Evaluated 1,498 selection episodes across 787 policies; XGBoost selected over logistic (AUC 0.542 vs 0.529). Final holdout remains not_materialized.",
          simple: "Ran candidate model selection on v3. XGBoost slightly edged out logistic regression, but both were still near 54% accuracy."
        },
        checks: "State reload verified; final holdout not materialized."
      },
      {
        id: "R2-11",
        title: "v3 Acceptance Protocol 2.2.0: REDESIGN Decision",
        status: "Redesign",
        commit: "76c8cd3",
        summary: {
          tech: "20 signal/null seed pairs evaluated across 3 folds. Signal AUC (0.519) failed to beat target 0.65 (0/20 passed). Recorded REDESIGN without holdout tuning.",
          simple: "The Redesign Gate: Across 20 test seeds, the model only achieved 51.9% accuracy vs 50.7% on the placebo. Instead of fudging numbers, we declared Redesign."
        },
        checks: "20/20 pairs pass readiness; 0/20 pass recovery threshold; final holdout sealed."
      }
    ]
  },
  {
    phase: "Phase 2R: v4 Diagnostic Boundary & Freeze",
    milestone: "v0.2.1-statistical-remediation",
    items: [
      {
        id: "R2-12",
        title: "v4 Signal-Recovery Diagnostic Boundary (ADR 0006)",
        status: "Completed",
        commit: "ea9cf1f",
        summary: {
          tech: "Predeclared 6 formal hypotheses (oracle separability, driver support, transform parity, episode dilution, candidate learning, temporal stability).",
          simple: "Scientific Method: Formulated 6 strict hypotheses to diagnose why v3 models failed before writing a single line of redesign code."
        },
        checks: "Contract 1.0.0 and ADR 0006 freeze diagnostic rules."
      },
      {
        id: "R2-13",
        title: "Diagnostic Execution & v4 Design Freeze (ADR 0007)",
        status: "Completed",
        commit: "7c4a1a7",
        summary: {
          tech: "Diagnosed weak observable-oracle separability (AUC 0.533) and near-constant rolling payments. ADR 0007 froze v4 redesign (doubled coefficients, halved frailty).",
          simple: "Root Cause Found! The theoretical maximum accuracy of v3 was only 53.3%. In v4, we doubled signal strength and halved random noise so the AI has real patterns to find."
        },
        checks: "All 20 seeds evaluated; H1 and H2 supported; ADR 0007 approved."
      },
      {
        id: "R2-14",
        title: "v4 Substrate Implementation & Development Qualification",
        status: "Planned",
        commit: "Current Work",
        summary: {
          tech: "Implementing contract 4.0.0 and protocol 3.0.0 with single-pass qualification gates.",
          simple: "Currently implementing the v4 simulator with the updated signal strength, scheduled payments, and qualification gates."
        },
        checks: "Next active engineering increment."
      }
    ]
  }
];

// Roadblocks & Design Pivots Data
const roadblocksData = [
  {
    id: "LIM-002-001",
    type: "rb-guard",
    title: "Billing Frequency Confounded with Observation Time",
    phase: "Discovered in Phase 2.03",
    adr: "ADR 0004 / 0005",
    trap: {
      tech: "All policies were issued in one initial batch, and observation cutoff occurred at first billing. Monthly policies entered train, quarterly entered embargo, semiannual entered val, and annual entered test.",
      simple: "All policies started on Day 1, and were evaluated on their first bill. That meant all monthly policies were in the training set and all yearly policies in the test set. Models couldn't tell time apart from policy type!"
    },
    pivot: {
      tech: "Introduced multi-cohort issuance spread across years, recurring point-in-time observation windows, and required all billing frequencies in all chronological folds.",
      simple: "Staggered policy start dates across years and checked on policies repeatedly. Now every time period contains a fair mix of monthly, quarterly, and annual policies."
    }
  },
  {
    id: "LIM-002-002",
    type: "rb-redesign",
    title: "Simulator Lacked Pre-Cutoff Feature-Conditioned Risk",
    phase: "Discovered in Review after Phase 2.07",
    adr: "ADR 0004 / 0005 / 0007",
    trap: {
      tech: "The v1 generator assigned lapse/surrender outcomes independently of customer attributes or historical events. Features had near-zero true mutual information with the target.",
      simple: "The initial simulator decided who canceled purely at random after the cutoff date. The ML models had literally nothing real to learn from, resulting in 53% coin-flip accuracy."
    },
    pivot: {
      tech: "Designed a multi-hazard frailty model with registered beta coefficients for behavioral drivers (billing frequency, arrears, service contacts) and explicit oracle probabilities.",
      simple: "Replaced flat random assignment with a realistic hazard formula: missed payments and service complaints increase risk of cancellation, giving models true signal to discover."
    }
  },
  {
    id: "LIM-002-003",
    type: "rb-guard",
    title: "Test Matrix Relabeling During Adversarial Review",
    phase: "Discovered in Review after Phase 2.07",
    adr: "ADR 0004 & Scoring Auth Contract",
    trap: {
      tech: "Scoring APIs previously authorized predictions based on a caller-supplied partition string. A reviewer was able to generate test predictions by relabeling the test matrix as 'validation'.",
      simple: "A security hole in our test code: anyone could sneak a peek at test set predictions simply by renaming the input variable to 'validation'."
    },
    pivot: {
      tech: "Implemented cryptographic scoring authorization contracts that verify row count, row order, fitted preprocessor ID, purpose, and exact SHA-256 matrix digests before computing scores.",
      simple: "Added digital tamper seals. If anyone tries to modify, reorder, or rename the dataset, the scoring engine immediately throws an integrity exception."
    }
  },
  {
    id: "LIM-002-004",
    type: "rb-stop",
    title: "Post-Cutoff Ingestion Leakage in v2 Preflight",
    phase: "Discovered in R2-07 Readiness Gate",
    adr: "ADR 0005 Dual-Time Substrate",
    trap: {
      tech: "The v2 corpus builder computed behavior features before verifying ingestion timestamps. An event with ingested_at > as_of leaked into cutoff features, failing READINESS-DUAL-TIME-VISIBILITY.",
      simple: "Future Paperwork Leak: An event that officially happened before the cutoff wasn't entered into the computer until AFTER the cutoff. The code accidentally counted it anyway."
    },
    pivot: {
      tech: "The automated gate halted fail-closed (STOP decision). ADR 0005 introduced the dual-time invariant: E.effective_at <= as_of AND E.ingested_at <= as_of for every feature.",
      simple: "Instead of ignoring the bug, the system automatically stopped the pipeline. We redesigned the engine so events are only visible if both the event AND the computer entry happened in the past."
    }
  }
];

// ============================================================
// CONTROLLER & VIEW RENDERING
// ============================================================

function initApp() {
  bindEvents();
  renderTimeline();
  renderRoadblocks();
  updateExplainerTexts();
}

function bindEvents() {
  // Explainer mode buttons
  const btnTech = document.getElementById('btnModeTech');
  const btnSimple = document.getElementById('btnModeSimple');

  btnTech.addEventListener('click', () => setExplainerMode('tech'));
  btnSimple.addEventListener('click', () => setExplainerMode('simple'));

  // Tab switching
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const targetTab = tab.dataset.tab;
      showTab(targetTab);
    });
  });

  // Timeline filters
  const searchInput = document.getElementById('timelineSearch');
  const filterSelect = document.getElementById('timelineFilterStatus');

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value.toLowerCase();
      renderTimeline();
    });
  }

  if (filterSelect) {
    filterSelect.addEventListener('change', (e) => {
      state.filterStatus = e.target.value;
      renderTimeline();
    });
  }
}

function setExplainerMode(mode) {
  state.explainerMode = mode;
  document.getElementById('btnModeTech').classList.toggle('active', mode === 'tech');
  document.getElementById('btnModeSimple').classList.toggle('active', mode === 'simple');
  updateExplainerTexts();
  renderTimeline();
  renderRoadblocks();
}

function updateExplainerTexts() {
  const dynamicElements = document.querySelectorAll('.text-dynamic');
  dynamicElements.forEach(el => {
    const text = el.getAttribute(`data-${state.explainerMode}`);
    if (text) {
      el.textContent = text;
    }
  });
}

function showTab(tabId) {
  state.activeTab = tabId;
  const panels = document.querySelectorAll('.tab-panel');
  panels.forEach(p => p.classList.remove('active'));
  const targetPanel = document.getElementById(`tab-${tabId}`);
  if (targetPanel) {
    targetPanel.classList.add('active');
  }
}

function renderTimeline() {
  const container = document.getElementById('timelineContainer');
  if (!container) return;

  container.innerHTML = '';

  timelineData.forEach(phaseGroup => {
    // Filter items
    const filteredItems = phaseGroup.items.filter(item => {
      const matchStatus = state.filterStatus === 'all' || item.status === state.filterStatus;
      const textToSearch = (item.title + ' ' + item.summary.tech + ' ' + item.summary.simple + ' ' + item.id).toLowerCase();
      const matchSearch = !state.searchQuery || textToSearch.includes(state.searchQuery);
      return matchStatus && matchSearch;
    });

    if (filteredItems.length === 0) return;

    const groupEl = document.createElement('div');
    groupEl.className = 'timeline-phase-group';

    groupEl.innerHTML = `
      <div class="timeline-phase-header">
        <div class="timeline-phase-dot"></div>
        <div>
          <div class="phase-title-text">${phaseGroup.phase}</div>
          <div class="phase-meta">Milestone: <code>${phaseGroup.milestone}</code></div>
        </div>
      </div>
      <div class="phase-nodes">
        ${filteredItems.map(item => `
          <div class="timeline-node-card">
            <div class="node-top-row">
              <span class="node-id">${item.id}</span>
              <span class="badge badge-${item.status.toLowerCase()}">${item.status}</span>
            </div>
            <div class="node-title">${item.title}</div>
            <div class="node-desc">
              ${state.explainerMode === 'simple' ? item.summary.simple : item.summary.tech}
            </div>
            <div class="node-foot">
              <span>Commit / PR: <a href="https://github.com/anilreddy89/Inforsight" target="_blank" class="node-link">${item.commit}</a></span>
              <span>•</span>
              <span>Verification: ${item.checks}</span>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    container.appendChild(groupEl);
  });
}

function renderRoadblocks() {
  const container = document.getElementById('roadblocksContainer');
  if (!container) return;

  container.innerHTML = roadblocksData.map(rb => `
    <div class="roadblock-card ${rb.type}">
      <div class="roadblock-header">
        <div>
          <div class="roadblock-id">${rb.id} • ${rb.phase}</div>
          <h3 class="roadblock-title">${rb.title}</h3>
        </div>
        <span class="badge badge-version">${rb.adr}</span>
      </div>

      <div class="roadblock-cols">
        <div class="rb-col rb-trap">
          <div class="rb-col-title">
            <span>⚠️</span> The Roadblock / Trap
          </div>
          <p class="text-dynamic">
            ${state.explainerMode === 'simple' ? rb.trap.simple : rb.trap.tech}
          </p>
        </div>

        <div class="rb-col rb-pivot">
          <div class="rb-col-title">
            <span>💡</span> The Engineering Pivot (ADR)
          </div>
          <p class="text-dynamic">
            ${state.explainerMode === 'simple' ? rb.pivot.simple : rb.pivot.tech}
          </p>
        </div>
      </div>
    </div>
  `).join('');
}

// Boot application
document.addEventListener('DOMContentLoaded', initApp);

