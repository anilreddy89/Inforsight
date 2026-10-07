/**
 * Isolated UI contract tests. The API responses below are explicitly fabricated
 * test fixtures, never application data or evidence of backend acceptance.
 * scripts/local_demo_browser.mjs remains the separate real-backend acceptance.
 */
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import type { Run, Stage } from "../src/api";

const stageIds = [
  "submission", "publication", "ingestion", "snapshot", "score", "rules",
  "allocation", "case", "agent", "decision", "audit",
];
const runId = "run_ui_fixture";

function fixtureRun(completed = 9): Run {
  const stages: Stage[] = stageIds.map((stage, index) => ({
    stage,
    status: index < completed ? "completed" : "waiting",
    producer: `Fixture producer for ${stage}`,
    attempt: index < completed ? 1 : 0,
    ...(index < completed ? {
      started_at: `2026-10-07T12:00:${String(index).padStart(2, "0")}.000Z`,
      completed_at: `2026-10-07T12:00:${String(index).padStart(2, "0")}.100Z`,
      duration_ms: 100,
      input_refs: index ? [`run:${runId}/${stageIds[index - 1]}`] : [],
      output_refs: [`sha256:fixture_${stage}`],
      evidence: { fixture_marker: `${stage}_evidence`, authorized_to_act: false },
    } : { input_refs: [], output_refs: [], evidence: {} }),
  }));
  return {
    correlation_id: runId,
    event_id: "evt_ui_fixture",
    scenario_id: "late-payment",
    status: "AWAITING_REVIEW",
    case_id: "case_ui_fixture",
    case_version: 0,
    created_at: "2026-10-07T12:00:00.000Z",
    updated_at: "2026-10-07T12:00:10.000Z",
    stages,
    artifacts: {},
  };
}

async function mountFixture(page: Page, initial = fixtureRun()) {
  let run = structuredClone(initial);
  let reads = 0;
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
      await route.fulfill({ json: {
        public_mode: false, session_tag: "ui-fixture", csrf_token: null,
        expires_at: null, environment: "local", limits: {},
      } });
    } else if (path.endsWith("/scenarios")) {
      await route.fulfill({ json: {
        environment: "local", external_execution_enabled: false,
        scenarios: [{ scenario_id: "late-payment", title: "UI fixture", description: "Test only", enabled: true }],
      } });
    } else if (path.endsWith(`/runs/${runId}`)) {
      reads++;
      await route.fulfill({ json: run });
    } else {
      await route.fulfill({ status: 404, json: { message: "No fixture for this endpoint" } });
    }
  });
  await page.goto(`/?run=${runId}`);
  await page.getByRole("button", { name: "Transaction flow", exact: true }).click();
  await expect(page.getByTestId("transaction-flow")).toBeVisible();
  return {
    update(next: Run) { run = structuredClone(next); },
    reads: () => reads,
    writes,
  };
}

test("live polling updates recorded status and does not auto-complete waiting stages", async ({ page }) => {
  const initial = fixtureRun(4);
  const score = initial.stages.find((stage) => stage.stage === "score")!;
  score.status = "processing";
  score.started_at = "2026-10-07T12:00:05.000Z";
  const fixture = await mountFixture(page, initial);
  await expect(page.getByTestId("flow-node-score")).toHaveAttribute("data-status", "processing");
  await expect(page.getByTestId("flow-node-rules")).toHaveAttribute("data-status", "waiting");

  const next = fixtureRun(5);
  next.updated_at = "2026-10-07T12:00:20.000Z";
  fixture.update(next);
  await expect(page.getByTestId("flow-node-score")).toHaveAttribute("data-status", "completed");
  await expect.poll(fixture.reads).toBeGreaterThanOrEqual(3);
  await expect(page.getByTestId("flow-node-rules")).toHaveAttribute("data-status", "waiting");
  await expect(page.getByTestId("flow-node-decision")).toHaveAttribute("data-status", "waiting");
  expect(fixture.writes).toEqual([]);
});

test("a missing stage stays waiting and its inspector discloses missing evidence", async ({ page }) => {
  const run = fixtureRun(4);
  run.stages = run.stages.filter((stage) => stage.stage !== "score");
  const fixture = await mountFixture(page, run);
  await expect(page.locator('[data-testid^="flow-node-"]')).toHaveCount(11);
  const missing = page.getByTestId("flow-node-score");
  await expect(missing).toHaveAttribute("data-status", "waiting");
  await missing.click();
  await page.getByRole("tab", { name: "Output", exact: true }).click();
  await expect(page.getByTestId("flow-inspector")).toContainText("This stage is not present in the run response.");
  await expect.poll(fixture.reads).toBeGreaterThanOrEqual(3);
  await expect(missing).toHaveAttribute("data-status", "waiting");
});

for (const status of ["failed", "abstained"] as const) {
  test(`the ${status} outcome remains explicit with its recorded reason`, async ({ page }) => {
    const run = fixtureRun(9);
    const agent = run.stages.find((stage) => stage.stage === "agent")!;
    agent.status = status;
    agent.evidence = { reason_codes: ["FIXTURE_MISSING_TRUSTED_EVIDENCE"], authorized_to_act: false };
    if (status === "failed") agent.error = { code: "FIXTURE_UPSTREAM_UNAVAILABLE", retryable: true };
    await mountFixture(page, run);
    const node = page.getByTestId("flow-node-agent");
    await expect(node).toHaveAttribute("data-status", status);
    await node.click();
    await page.getByRole("tab", { name: "Output", exact: true }).click();
    await expect(page.getByTestId("flow-inspector")).toContainText("FIXTURE_MISSING_TRUSTED_EVIDENCE");
    if (status === "failed")
      await expect(page.getByTestId("flow-inspector")).toContainText("FIXTURE_UPSTREAM_UNAVAILABLE");
    await expect(page.getByTestId("flow-node-decision")).toHaveAttribute("data-status", "waiting");
  });
}

test("component and handoff selection expose the linked input and recorded output", async ({ page }) => {
  await mountFixture(page);
  await page.getByTestId("flow-node-score").click();
  await page.getByRole("tab", { name: "Input", exact: true }).click();
  const inspector = page.getByTestId("flow-inspector");
  await expect(inspector).toContainText(`run:${runId}/snapshot`);
  await expect(inspector).toContainText("snapshot_evidence");
  await page.getByRole("tab", { name: "Output", exact: true }).click();
  await expect(inspector).toContainText("score_evidence");
  await expect(inspector).toContainText("sha256:fixture_score");
  await page.getByTestId("flow-edge-snapshot-score").click();
  await expect(inspector).toContainText("snapshot_evidence");
});

test("replay freezes evidence while live reads continue, and never posts workflow actions", async ({ page }) => {
  const fixture = await mountFixture(page);
  await page.getByRole("button", { name: "Replay recorded flow", exact: true }).click();
  // Reduced-motion users start paused; pause animated playback if it is active.
  const pause = page.getByRole("button", { name: "Pause replay", exact: true });
  if (await pause.isVisible()) await pause.click();
  const range = page.getByRole("slider", { name: "Replay position", exact: true });
  await range.focus();
  await page.keyboard.press("Home");
  await expect(range).toHaveValue("0");
  await page.keyboard.press("End");
  await expect(range).toHaveValue("8");
  await expect(page.getByTestId("flow-node-agent")).toHaveAttribute("aria-pressed", "true");

  const readsBefore = fixture.reads();
  const completed = fixtureRun(11);
  completed.updated_at = "2026-10-07T12:01:00.000Z";
  completed.status = "COMPLETED";
  fixture.update(completed);
  await expect.poll(fixture.reads).toBeGreaterThan(readsBefore);
  await expect(page.getByTestId("flow-node-decision")).toHaveAttribute("data-status", "waiting");
  await expect(page.getByTestId("flow-node-audit")).toHaveAttribute("data-status", "waiting");
  await page.getByRole("button", { name: "Return to live", exact: true }).click();
  await expect(page.getByTestId("flow-node-decision")).toHaveAttribute("data-status", "completed");
  await expect(page.getByTestId("flow-node-audit")).toHaveAttribute("data-status", "completed");
  expect(fixture.writes).toEqual([]);
});

test("paused replay can leave an unrecorded inspection using the scrubber and step controls", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await mountFixture(page);
  await page.getByRole("button", { name: "Replay recorded flow", exact: true }).click();
  await page.getByRole("button", { name: "Pause replay", exact: true }).click();
  await page.getByTestId("flow-node-audit").click();
  await expect(page.getByTestId("flow-node-audit")).toHaveAttribute("aria-pressed", "true");

  const range = page.getByRole("slider", { name: "Replay position", exact: true });
  await range.focus();
  await page.keyboard.press("End");
  await expect(page.getByTestId("flow-node-agent")).toHaveAttribute("aria-pressed", "true");
  await expect(range).toHaveAttribute("aria-valuetext", /9 of 9: Prepare review/);
  await page.getByTestId("flow-node-audit").click();
  await page.getByRole("button", { name: "Previous replay step", exact: true }).click();
  await expect(page.getByTestId("flow-node-case")).toHaveAttribute("aria-pressed", "true");
  await page.getByTestId("flow-node-audit").click();
  await page.getByRole("button", { name: "Next replay step", exact: true }).click();
  await expect(page.getByTestId("flow-node-agent")).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".flow-packet")).toHaveCount(0);
  const runningEdges = await page.locator(".flow-connections").evaluate((root) =>
    root.getAnimations({ subtree: true }).filter((animation) =>
      animation.playState === "running" && animation.effect?.getTiming().iterations === Infinity,
    ).length,
  );
  expect(runningEdges, "Pausing playback must stop edge motion even without reduced motion").toBe(0);
});

test("the flow deep link survives home and browser back, and review clears the flow query", async ({ page }) => {
  await mountFixture(page);
  await expect(page).toHaveURL(new RegExp(`run=${runId}.*view=flow`));
  await page.getByRole("button", { name: "Inforsight home", exact: true }).click();
  await expect(page).not.toHaveURL(/run=|view=flow/);
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`run=${runId}.*view=flow`));
  await expect(page.getByTestId("transaction-flow")).toBeVisible();
  await page.getByTestId("flow-node-decision").click();
  await page.getByRole("button", { name: "Continue to human review", exact: true }).click();
  await expect(page).not.toHaveURL(/view=flow/);
  await expect(page.getByRole("button", { name: "Record decision", exact: true })).toBeVisible();
  await expect(page.getByTestId("transaction-flow")).toHaveCount(0);
});

test("keyboard selection, reduced motion, and automated accessibility", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const run = fixtureRun(4);
  run.stages[4].status = "processing";
  run.stages[4].started_at = "2026-10-07T12:00:05.000Z";
  await mountFixture(page, run);
  const node = page.getByTestId("flow-node-score");
  await node.focus();
  await page.keyboard.press("Enter");
  await expect(node).toHaveAttribute("aria-pressed", "true");
  const input = page.getByRole("tab", { name: "Input", exact: true });
  await input.focus();
  await page.keyboard.press("Enter");
  await expect(input).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Output", exact: true })).toBeFocused();
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  await testInfo.attach("axe violations", {
    body: JSON.stringify(results.violations, null, 2), contentType: "application/json",
  });
  expect(results.violations.map((violation) => ({
    rule: violation.id,
    targets: violation.nodes.map((node) => node.target),
  }))).toEqual([]);
  const animations = await page.getByTestId("transaction-flow").evaluate((root) =>
    root.getAnimations({ subtree: true }).filter((animation) =>
      animation.playState === "running" && animation.effect?.getTiming().iterations === Infinity,
    ).length,
  );
  expect(animations, "Reduced motion must suppress continuous flow animation").toBe(0);
  expect(errors).toEqual([]);
});

test("graph zoom stays inside the page on a narrow mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mountFixture(page);
  const initialWidth = (await page.getByTestId("flow-node-score").boundingBox())!.width;
  for (let index = 0; index < 3; index++)
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  await expect(page.getByTestId("flow-node-score")).toBeVisible();
  expect((await page.getByTestId("flow-node-score").boundingBox())!.width).toBeGreaterThan(initialWidth);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.getByRole("button", { name: "Fit to view", exact: true }).click();
  await page.getByTestId("flow-node-agent").click();
  await expect(page.getByTestId("flow-inspector")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});
