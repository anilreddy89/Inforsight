/**
 * Isolated UI contract tests for the model development timeline. The API responses
 * below are fabricated test fixtures, never application data or backend acceptance.
 */
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import type { Run } from "../src/api";

const runId = "run_model_timeline_fixture";
const stageIds = [
  "submission", "publication", "ingestion", "snapshot", "score", "rules",
  "allocation", "case", "agent", "decision", "audit",
];
const milestoneIds = ["groundwork", "v1", "v2", "v3", "v4", "v5", "v6", "release"];
const recordBase = "https://github.com/anilreddy89/Inforsight/blob/v0.2.0-risk-model/";

const completedRun: Run = {
  correlation_id: runId,
  event_id: "evt_model_timeline_fixture",
  scenario_id: "late-payment",
  status: "COMPLETED",
  case_id: "case_model_timeline_fixture",
  case_version: 1,
  created_at: "2026-10-07T12:00:00.000Z",
  updated_at: "2026-10-07T12:00:20.000Z",
  stages: stageIds.map((stage, index) => ({
    stage,
    status: "completed",
    producer: `Fixture producer for ${stage}`,
    attempt: 1,
    started_at: `2026-10-07T12:00:${String(index).padStart(2, "0")}.000Z`,
    completed_at: `2026-10-07T12:00:${String(index).padStart(2, "0")}.100Z`,
    duration_ms: 100,
    input_refs: [],
    output_refs: [`sha256:fixture_${stage}`],
    evidence: { fixture_marker: `${stage}_evidence`, authorized_to_act: false },
  })),
  artifacts: {
    score: {
      calibrated_probability: 0.2341,
      risk_tier_id: "TIER_2_MODERATE",
      bundle_id: "inforsight-v6-logistic-platt-20260817",
      bundle_version: "1.0.0",
      bundle_digest: "7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656",
      authorized_to_act: false,
    },
  },
};

async function mount(page: Page, { run }: { run?: Run } = {}) {
  const writes: string[] = [];
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
        json: { public_mode: false, session_tag: "local", csrf_token: null, expires_at: null, environment: "local", limits: {} },
      });
    } else if (path.endsWith("/scenarios")) {
      await route.fulfill({
        json: {
          environment: "local",
          external_execution_enabled: false,
          scenarios: [{ scenario_id: "late-payment", title: "UI fixture", description: "Test only", enabled: true }],
          safe_inputs: { premium_amount_cents: { minimum: 1000, maximum: 100000 }, delay_days: { minimum: 1, maximum: 45 } },
        },
      });
    } else if (path.endsWith(`/runs/${runId}`) && run) {
      await route.fulfill({ json: run });
    } else {
      await route.fulfill({ status: 404, json: { message: "No fixture for this endpoint" } });
    }
  });
  return { writes };
}

const overflow = (page: Page) =>
  page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

test("the timeline walks from groundwork to the released model without writes", async ({ page }) => {
  const api = await mount(page);
  await page.goto("/?view=model");
  const timeline = page.getByTestId("model-timeline");
  await expect(timeline.getByRole("heading", { level: 1 })).toHaveText(
    "Six generations to one model we could defend.",
  );
  await expect(timeline.locator('[data-testid^="model-step-"]')).toHaveCount(milestoneIds.length);
  for (const [index, id] of milestoneIds.entries()) {
    await expect(timeline.locator(".model-steps > li").nth(index)).toHaveAttribute("data-testid", `model-step-${id}`);
  }
  await expect(timeline.locator('[data-testid^="model-chip-"]')).toHaveCount(7);
  await expect(page.getByTestId("model-step-v5")).toContainText("Stopped: infeasible");
  await expect(page.getByTestId("model-step-v5")).toContainText("0 of 320 feasible");
  await expect(page.getByTestId("model-step-v6")).toContainText("AUC 0.7031 · 20/20 seeds");
  await expect(page.getByTestId("model-step-release")).toContainText("Released");
  await expect(timeline.getByRole("list", { name: "Development in numbers" }).getByRole("listitem")).toHaveCount(6);
  await expect(timeline).toContainText("They do not establish real-world predictive performance");

  // Every milestone cites its record, pinned to the release tag.
  for (const id of milestoneIds) {
    await expect(page.getByTestId(`model-step-${id}`).locator(".model-step-foot a")).not.toHaveCount(0);
  }
  // The v6 verdict links its protocol amendment as well as its decision.
  await expect(page.getByTestId("model-step-v6").locator(".model-step-foot a")).toHaveCount(2);
  await expect(page.getByTestId("model-step-v6")).toContainText("Protocol 3.0.0 returned redesign");
  const records = timeline.locator(".model-step-foot a");
  await expect(records).toHaveCount(milestoneIds.length + 1);
  for (const record of await records.all()) {
    expect(await record.getAttribute("href")).toMatch(new RegExp(`^${recordBase.replace(/[.]/g, "\\.")}[\\w./-]+\\.md$`));
    await expect(record).toHaveAttribute("target", "_blank");
    await expect(record).toHaveAttribute("rel", /noopener/);
  }
  expect(api.writes).toEqual([]);
});

test("a generation chip jumps to and highlights its milestone", async ({ page }) => {
  await mount(page);
  await page.goto("/?view=model");
  await page.getByTestId("model-chip-v5").click();
  const step = page.getByTestId("model-step-v5");
  await expect(step).toBeFocused();
  await expect(step).toHaveClass(/is-highlighted/);
  await expect(step).toBeInViewport();
  await expect(step).not.toHaveClass(/is-highlighted/, { timeout: 4000 });
  await expect(step).toBeFocused();
});

test("visitors reach the timeline from the landing band, header and footer", async ({ page }) => {
  await mount(page);
  await page.goto("/");
  const band = page.getByTestId("model-band");
  await expect(band.getByRole("heading", { name: "Six generations. Five stopped by evidence. One released." })).toBeVisible();
  await expect(band.locator('[data-testid^="model-chip-"]')).toHaveCount(7);

  await band.getByRole("button", { name: "See the model timeline" }).click();
  await expect(page.getByTestId("model-timeline")).toBeVisible();
  await expect(page).toHaveURL(/view=model/);
  const header = page.getByRole("button", { name: "Model timeline", exact: true });
  await expect(header).toHaveAttribute("aria-current", "page");
  await page.reload();
  await expect(page.getByTestId("model-timeline")).toBeVisible();
  await page.getByRole("button", { name: "All scenarios" }).click();
  await expect(band).toBeVisible();
  await expect(page).not.toHaveURL(/view=/);
  await expect(header).not.toHaveAttribute("aria-current", "page");

  await band.getByTestId("model-chip-v3").click();
  await expect(page.getByTestId("model-step-v3")).toBeFocused();
  await expect(page.getByTestId("model-step-v3")).toHaveClass(/is-highlighted/);
  await page.getByRole("button", { name: "All scenarios" }).click();

  await header.click();
  await expect(page.getByTestId("model-timeline")).toBeVisible();
  await page.getByRole("button", { name: "All scenarios" }).click();
  await page.getByRole("button", { name: "How the model was built" }).click();
  await expect(page.getByTestId("model-timeline")).toBeVisible();
});

test("a case dossier links to the model history and Back returns to the case", async ({ page }) => {
  const api = await mount(page, { run: completedRun });
  await page.goto(`/?run=${runId}`);
  await page.getByRole("button", { name: "Case dossier", exact: true }).click();
  await page.getByRole("button", { name: "How this model was built" }).click();
  await expect(page.getByTestId("model-timeline")).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`run=${runId}.*view=model|view=model.*run=${runId}`));
  await page.getByRole("button", { name: "Back to your case" }).click();
  await expect(page.getByRole("button", { name: "Case dossier", exact: true })).toHaveAttribute("aria-current", "page");
  await expect(page.getByText("What the model sees", { exact: true })).toBeVisible();

  // The released-model panel hands over to the architecture's lineage lens.
  await page.getByRole("button", { name: "Model timeline", exact: true }).click();
  await page.getByRole("button", { name: "See how it scores a case" }).click();
  await expect(page.getByTestId("arch-lens-lineage")).toHaveAttribute("aria-selected", "true");
  await page.getByRole("button", { name: "Model timeline", exact: true }).click();
  await page.getByRole("button", { name: "Back to the architecture" }).click();
  await expect(page.getByTestId("arch-canvas-lineage")).toBeVisible();
  expect(api.writes).toEqual([]);
});

test("the timeline passes automated accessibility checks and fits a phone", async ({ page }) => {
  await mount(page);
  await page.goto("/?view=model");
  await expect(page.getByTestId("model-step-release")).toBeVisible();
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(results.violations, "model timeline accessibility").toEqual([]);

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("button", { name: "Model timeline", exact: true })).toBeVisible();
  expect(await overflow(page)).toBeLessThanOrEqual(0);
  await page.getByRole("button", { name: "All scenarios" }).click();
  await expect(page.getByTestId("model-band")).toBeVisible();
  expect(await overflow(page)).toBeLessThanOrEqual(0);
  const landing = await new AxeBuilder({ page })
    .include('[data-testid="model-band"]')
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(landing.violations, "model band accessibility").toEqual([]);
});
