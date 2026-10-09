/**
 * Isolated UI contract tests for the architecture explorer. The API responses below
 * are fabricated test fixtures, never application data or backend acceptance.
 * scripts/local_demo_browser.mjs remains the separate real-backend acceptance.
 */
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import type { Audit, Run, Stage } from "../src/api";

const stageIds = [
  "submission", "publication", "ingestion", "snapshot", "score", "rules",
  "allocation", "case", "agent", "decision", "audit",
];
const runId = "run_architecture_fixture";

function fixtureRun(completed: number, processing?: number): Run {
  const stages: Stage[] = stageIds.map((stage, index) => {
    const done = index < completed;
    const active = index === processing;
    return {
      stage,
      status: done ? "completed" : active ? "processing" : "waiting",
      producer: `Fixture producer for ${stage}`,
      attempt: done || active ? 1 : 0,
      ...(done || active ? { started_at: `2026-10-07T12:00:${String(index).padStart(2, "0")}.000Z` } : {}),
      ...(done
        ? {
            completed_at: `2026-10-07T12:00:${String(index).padStart(2, "0")}.100Z`,
            duration_ms: 100,
            input_refs: index ? [`run:${runId}/${stageIds[index - 1]}`] : [],
            output_refs: [`sha256:fixture_${stage}`],
            evidence:
              stage === "publication"
                ? { topic: "inforsight.demo.events.v1", partition: 0, offset: 41, acks: "all", envelope_sha256: "a".repeat(64) }
                : stage === "ingestion"
                  ? { topic: "inforsight.demo.events.v1", partition: 0, offset: 41, consumer_group: "inforsight-demo-journey-v1" }
                  : { fixture_marker: `${stage}_evidence`, authorized_to_act: false },
          }
        : { input_refs: [], output_refs: [], evidence: {} }),
    };
  });
  return {
    correlation_id: runId,
    event_id: "evt_architecture_fixture",
    scenario_id: "late-payment",
    status: completed >= 11 ? "COMPLETED" : completed >= 9 ? "AWAITING_REVIEW" : "PROCESSING",
    case_id: "case_architecture_fixture",
    case_version: completed >= 11 ? 1 : 0,
    created_at: "2026-10-07T12:00:00.000Z",
    updated_at: `2026-10-07T12:00:${String(completed + 10).padStart(2, "0")}.000Z`,
    stages,
    artifacts:
      completed > 4
        ? {
            score: {
              calibrated_probability: 0.2341,
              risk_tier_id: "TIER_2_MODERATE",
              bundle_id: "inforsight-v6-logistic-platt-20260817",
              bundle_version: "1.0.0",
              bundle_digest: "7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656",
              authorized_to_act: false,
            },
          }
        : {},
  };
}

const auditFixture: Audit = {
  valid: true,
  verified_entries: 3,
  head_hash: "c".repeat(64),
  scope: "fixture scope",
  entries: [1, 2, 3].map((sequence) => ({
    sequence,
    event_id: `evt_fixture_journal_${sequence}`,
    event_type: ["submission.completed", "publication.processing", "publication.completed"][sequence - 1],
    stage: sequence === 1 ? "submission" : "publication",
    producer: "Fixture producer",
    occurred_at: `2026-10-07T12:00:0${sequence}.000Z`,
    parent_hash: sequence === 1 ? "0".repeat(64) : "abc".repeat(21) + String(sequence),
    current_hash: "def".repeat(21) + String(sequence),
    payload: { fixture: true, sequence },
  })),
};

async function mount(
  page: Page,
  { publicMode = false, run, audit }: { publicMode?: boolean; run?: Run; audit?: Audit } = {},
) {
  let current = run ? structuredClone(run) : undefined;
  const writes: string[] = [];
  let audits = 0;
  await page.route("**/api/v1/demo/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() !== "GET") {
      writes.push(`${request.method()} ${path}`);
      await route.fulfill({ status: 405, json: { message: "UI fixture rejects writes" } });
      return;
    }
    if (path.endsWith("/session")) {
      await route.fulfill({
        json: {
          public_mode: publicMode,
          session_tag: publicMode ? "fixture_tag" : "local",
          csrf_token: publicMode ? "fixture_csrf" : null,
          expires_at: publicMode ? "2026-10-14T12:00:00Z" : null,
          environment: publicMode ? "public-preview" : "local",
          limits: publicMode
            ? { submissions_per_hour: 12, polls_per_minute: 120, retries_per_hour: 3, concurrent_processing_runs: 2, retained_runs: 12, retention_hours: 24, abandoned_review_hours: 48 }
            : {},
        },
      });
    } else if (path.endsWith("/scenarios")) {
      await route.fulfill({
        json: {
          environment: publicMode ? "public-preview" : "local",
          external_execution_enabled: false,
          scenarios: [{ scenario_id: "late-payment", title: "UI fixture", description: "Test only", enabled: true }],
          safe_inputs: { premium_amount_cents: { minimum: 1000, maximum: 100000 }, delay_days: { minimum: 1, maximum: 45 } },
        },
      });
    } else if (path.endsWith(`/runs/${runId}/audit`) && audit) {
      audits++;
      await route.fulfill({ json: audit });
    } else if (path.endsWith(`/runs/${runId}`) && current) {
      await route.fulfill({ json: current });
    } else {
      await route.fulfill({ status: 404, json: { message: "No fixture for this endpoint" } });
    }
  });
  return {
    writes,
    audits: () => audits,
    update(next: Run) {
      current = structuredClone(next);
    },
  };
}

test("every view renders from the reference model without a run or writes", async ({ page }) => {
  const api = await mount(page);
  await page.goto("/?view=architecture");
  await expect(page.getByTestId("architecture-explorer")).toBeVisible();
  // The real-backend acceptance relies on exactly one "Planned" label.
  await expect(page.getByText("Planned", { exact: true })).toBeVisible();
  await expect(page.getByTestId("arch-indicator")).toHaveText(/Reference model/);
  for (const lens of ["system", "sequence", "lineage", "lifecycle", "security", "audit", "schema"]) {
    await page.getByTestId(`arch-lens-${lens}`).click();
    await expect(page.getByTestId(`arch-lens-${lens}`)).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId(`arch-canvas-${lens}`)).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`view=architecture.*lens=${lens}|lens=${lens}.*view=architecture`));
  }
  await page.reload();
  await expect(page.getByTestId("arch-canvas-schema")).toBeVisible();
  await page.getByRole("button", { name: "All scenarios" }).click();
  await expect(page).not.toHaveURL(/lens=|view=/);
  expect(api.writes).toEqual([]);
});

test("the system map separates the local stack from the Mac-hosted preview", async ({ page }) => {
  await mount(page);
  await page.goto("/?view=architecture");
  await expect(page.getByTestId("arch-deployment-local")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("arch-node-cloudflare")).toHaveCount(0);
  await expect(page.getByTestId("arch-node-nginx")).toContainText("127.0.0.1:3000");
  await expect(page.getByTestId("arch-step-10")).toContainText("Qualify the stack");

  await page.getByTestId("arch-deployment-public").click();
  await expect(page.getByTestId("arch-node-cloudflare")).toBeVisible();
  await expect(page.getByTestId("arch-node-cloudflared")).toBeVisible();
  await expect(page.getByTestId("arch-node-traffic")).toBeVisible();
  await expect(page.getByTestId("arch-node-nginx")).toContainText("127.0.0.1:3100");
  await expect(page.getByTestId("arch-step-10")).toContainText("Operate the preview");
});

test("public mode keeps one gateway notice and one environment label", async ({ page }) => {
  await mount(page, { publicMode: true });
  await page.goto("/?view=architecture");
  await expect(page.getByText("One public gateway. Isolated visitor sessions.", { exact: true })).toBeVisible();
  await expect(page.getByText("Public preview", { exact: true })).toBeVisible();
  await expect(page.getByText("Planned", { exact: true })).toBeVisible();
  await expect(page.getByTestId("arch-deployment-public")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("arch-node-cloudflare")).toContainText("serving this page");

  await page.getByTestId("arch-lens-security").click();
  await page.getByTestId("arch-node-sec-session").click();
  const inspector = page.getByTestId("arch-inspector");
  await expect(inspector.getByRole("heading", { name: "Signed visitor session" })).toBeVisible();
  await expect(inspector.getByRole("region", { name: "Live evidence" })).toContainText("12 per hour");
});

test("the inspector explains a component and walks its connections", async ({ page }) => {
  await mount(page);
  await page.goto("/?view=architecture");
  await page.getByTestId("arch-node-kafka").click();
  const inspector = page.getByTestId("arch-inspector");
  await expect(inspector.getByRole("heading", { name: "Apache Kafka" })).toBeVisible();
  await expect(inspector).toContainText("inforsight-demo-journey-v1");
  await expect(inspector).toContainText("DemoJourneyWorker.java");
  await inspector.getByRole("button", { name: /Java control plane/ }).click();
  await expect(inspector.getByRole("heading", { name: "Kafka :29092" })).toBeVisible();
  await expect(inspector).toContainText("Java control plane ↔ Apache Kafka");
  await page.getByTestId("arch-edge-label-e-score").click();
  await expect(inspector.getByRole("heading", { name: "HTTP :8000" })).toBeVisible();
  await expect(inspector).toContainText("there is no fallback scorer");
});

test("live binding follows persisted stages and never auto-completes waiting work", async ({ page }) => {
  const api = await mount(page, { run: fixtureRun(4, 4) });
  await page.goto(`/?run=${runId}`);
  await page.getByRole("button", { name: "Architecture", exact: true }).click();
  await expect(page.getByTestId("arch-indicator")).toHaveText(/Live/);
  await expect(page.getByTestId("arch-node-inference")).toHaveAttribute("data-status", "processing");
  await expect(page.getByTestId("arch-node-kafka")).toHaveAttribute("data-status", "recorded");
  await expect(page.getByTestId("arch-node-kafka")).toContainText("offset 41");
  await expect(page.getByTestId("arch-node-postgres")).toHaveAttribute("data-status", "partial");
  await expect(page.getByTestId("arch-node-reviewer")).toHaveAttribute("data-status", "waiting");
  // Follow mode keeps the inspector on the component doing the current work.
  await expect(page.getByTestId("arch-inspector").getByRole("heading", { name: "Inference runtime" })).toBeVisible();
  await expect(page.getByTestId("arch-inspector")).toContainText("Not recorded yet");

  api.update(fixtureRun(5, 5));
  await expect(page.getByTestId("arch-node-inference")).toHaveAttribute("data-status", "recorded");
  await expect(page.getByTestId("arch-node-inference")).toContainText("p = 23.4%");
  await expect(page.getByTestId("arch-node-java")).toHaveAttribute("data-status", "processing");
  await expect(page.getByTestId("arch-node-reviewer")).toHaveAttribute("data-status", "waiting");
  await page.waitForTimeout(1800);
  await expect(page.getByTestId("arch-node-reviewer")).toHaveAttribute("data-status", "waiting");
  expect(api.writes).toEqual([]);
});

test("the sequence diagram numbers every message and reflects stage status", async ({ page }) => {
  await mount(page, { run: fixtureRun(4, 4) });
  await page.goto(`/?run=${runId}&view=architecture&lens=sequence`);
  await expect(page.getByTestId("arch-canvas-sequence")).toBeVisible();
  await expect(page.locator('[data-testid^="arch-message-"]')).toHaveCount(42);
  await expect(page.getByTestId("arch-band-publication")).toHaveAttribute("data-status", "recorded");
  await expect(page.getByTestId("arch-band-score")).toHaveAttribute("data-status", "processing");
  await expect(page.getByTestId("arch-band-decision")).toHaveAttribute("data-status", "waiting");
  await page.getByTestId("arch-message-13").click();
  const inspector = page.getByTestId("arch-inspector");
  await expect(inspector).toContainText("MESSAGE 13 OF 42");
  await expect(inspector).toContainText("Java worker → Kafka · Kafka event");
  await expect(page.getByTestId("arch-message-13")).toHaveAttribute("aria-pressed", "true");
});

test("the audit chain loads verified rows only when the visitor asks", async ({ page }) => {
  const api = await mount(page, { run: fixtureRun(11), audit: auditFixture });
  await page.goto(`/?run=${runId}&view=architecture&lens=audit`);
  await expect(page.getByTestId("arch-entry-21")).toBeVisible();
  await expect(page.getByTestId("arch-entry-1")).toContainText("parent = genesis");
  expect(api.audits()).toBe(0);
  await page.getByRole("button", { name: "Load and verify this run's chain" }).click();
  await expect(page.getByText(/This run's chain verified: 3 entries/)).toBeVisible();
  await expect(page.getByTestId("arch-entry-21")).toHaveCount(0);
  await expect(page.getByTestId("arch-check-hash")).toContainText("passed");
  await page.getByTestId("arch-entry-2").click();
  await expect(page.getByTestId("arch-inspector")).toContainText("current_hash");
  expect(api.audits()).toBe(1);
  expect(api.writes).toEqual([]);
});

test("the walkthrough steps through the dataflow without network writes", async ({ page }) => {
  const api = await mount(page);
  await page.goto("/?view=architecture");
  await page.getByRole("button", { name: "Walk through", exact: true }).click();
  // Reduced motion starts paused; the visitor advances it.
  await expect(page.getByTestId("arch-walk-position")).toHaveText("1 / 10");
  await expect(page.getByTestId("arch-inspector")).toContainText("STEP 1 OF 10");
  await page.getByRole("button", { name: "Next walkthrough step" }).click();
  await expect(page.getByTestId("arch-walk-position")).toHaveText("2 / 10");
  await expect(page.getByTestId("arch-inspector").getByRole("heading", { name: "Submit a fictional event" })).toBeVisible();
  await expect(page.getByTestId("arch-node-java")).toHaveClass(/is-step/);
  await expect(page.getByTestId("arch-node-inference")).toHaveClass(/is-muted/);
  await page.getByTestId("arch-step-5").click();
  await expect(page.getByTestId("arch-walk-position")).toHaveText("5 / 10");
  await page.getByTestId("arch-node-inference").click();
  await expect(page.getByTestId("arch-inspector").getByRole("heading", { name: "Inference runtime" })).toBeVisible();
  await page.getByRole("button", { name: "Exit" }).click();
  await expect(page.getByTestId("arch-walk-position")).toHaveCount(0);
  expect(api.writes).toEqual([]);
});

test("keyboard navigation, reduced motion, and automated accessibility", async ({ page }) => {
  await mount(page, { run: fixtureRun(4, 4) });
  await page.goto(`/?run=${runId}&view=architecture`);
  const first = page.getByTestId("arch-lens-system");
  await first.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByTestId("arch-lens-sequence")).toBeFocused();
  await expect(page.getByTestId("arch-lens-sequence")).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("End");
  await expect(page.getByTestId("arch-lens-schema")).toBeFocused();
  await page.keyboard.press("Home");
  await expect(page.getByTestId("arch-lens-system")).toBeFocused();

  await page.getByTestId("arch-node-reviewer").focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByTestId("arch-node-spa")).toBeFocused();
  await expect(page.getByTestId("arch-node-spa")).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".arch-packet")).toHaveCount(0);

  for (const lens of ["system", "sequence", "lineage", "lifecycle", "security", "audit", "schema"]) {
    await page.getByTestId(`arch-lens-${lens}`).click();
    const results = await new AxeBuilder({ page })
      .include('[data-testid="architecture-explorer"]')
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(results.violations, `${lens} accessibility`).toEqual([]);
  }
});

test("visitors can find the explorer from the header, hero, showcase and footer", async ({ page }) => {
  await mount(page);
  await page.goto("/");
  const header = page.getByRole("button", { name: /^Architecture explorer/ });
  await expect(header).toBeVisible();
  await expect(header).toContainText("New");
  await expect(page.getByRole("button", { name: "Explore the architecture" })).toBeVisible();
  const teaser = page.getByTestId("architecture-teaser");
  await expect(teaser.locator('[data-testid^="teaser-lens-"]')).toHaveCount(7);
  const landing = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(landing.violations, "landing accessibility").toEqual([]);

  await page.getByTestId("teaser-lens-sequence").click();
  await expect(page.getByTestId("arch-lens-sequence")).toHaveAttribute("aria-selected", "true");
  await expect(page).toHaveURL(/lens=sequence/);
  await expect(header).toHaveAttribute("aria-current", "page");
  await expect(header).not.toContainText("New");

  await page.getByRole("button", { name: "All scenarios" }).click();
  await expect(page.getByTestId("architecture-teaser")).toBeVisible();
  await expect(header).not.toContainText("New");
  await page.getByRole("button", { name: "Explore the architecture" }).click();
  await expect(page.getByTestId("arch-canvas-system")).toBeVisible();
  await page.getByRole("button", { name: "All scenarios" }).click();
  await page.getByRole("button", { name: "System architecture" }).click();
  await expect(page.getByTestId("arch-canvas-system")).toBeVisible();
});

test("a running case invites the visitor into its live architecture", async ({ page }) => {
  await mount(page, { run: fixtureRun(4, 4) });
  await page.goto(`/?run=${runId}`);
  const tab = page.getByRole("button", { name: "Architecture", exact: true });
  await expect(tab).toContainText("New");
  await page.getByRole("button", { name: "Open the live architecture" }).click();
  await expect(page.getByTestId("arch-indicator")).toHaveText(/Live/);
  await expect(tab).toHaveAttribute("aria-current", "page");
  await expect(tab).not.toContainText("New");
  await expect(page.getByTestId("arch-node-inference")).toHaveAttribute("data-status", "processing");
});

test("the explorer stays inside a narrow mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mount(page);
  await page.goto("/");
  await expect(page.getByRole("button", { name: /^Architecture explorer/ })).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth),
  ).toBeLessThanOrEqual(0);
  await page.getByRole("button", { name: /^Architecture explorer/ }).click();
  await expect(page.getByTestId("arch-canvas-system")).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
  await page.getByRole("button", { name: "Zoom in" }).click();
  await page.getByTestId("arch-lens-sequence").click();
  await expect(page.getByTestId("arch-canvas-sequence")).toBeVisible();
  const after = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(after).toBeLessThanOrEqual(0);
});
