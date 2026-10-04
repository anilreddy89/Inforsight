/** Real public-UI qualification. Network probes drop/delay real replies; never fabricate backend evidence. */
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const require = createRequire(resolve("frontend/package.json"));
const { chromium, expect } = require("@playwright/test");
const { default: AxeBuilder } = require("@axe-core/playwright");
const base = process.env.DEMO_URL || "http://localhost:3000";
const output = resolve("artifacts/local-demo");
await mkdir(output, { recursive: true });
const report = {
  result: "FAIL",
  base_url: base,
  checks: [],
  runs: [],
  console_errors: [],
};
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  reducedMotion: "reduce",
});
const page = await context.newPage();
page.on("pageerror", (error) => report.console_errors.push(error.message));
const record = (check, evidence) => {
  report.checks.push({ check, passed: true, evidence });
  console.log(`PASS ${check}`);
};
const getRun = async (id) =>
  (await context.request.get(`${base}/api/v1/demo/runs/${id}`)).json();
async function accessible(label) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  await writeFile(
    `${output}/axe-${label}.json`,
    JSON.stringify(result.violations, null, 2),
  );
  expect(result.violations, `WCAG A/AA violations on ${label}`).toEqual([]);
  record(`automated accessibility: ${label}`, {
    violations: 0,
    rules_passed: result.passes.length,
  });
}
async function ready() {
  await expect(page.getByTestId("stage-agent")).toHaveAttribute(
    "data-status",
    /completed|abstained/,
    { timeout: 90000 },
  );
}
async function launch() {
  await page.getByRole("button", { name: "Start this case" }).click();
  await expect(page).toHaveURL(/\?run=run_[a-f0-9]+/);
  const id = new URL(page.url()).searchParams.get("run");
  report.runs.push(id);
  await ready();
  return id;
}
try {
  await page.goto(base);
  await expect(
    page.getByRole("button", { name: "Start this case" }),
  ).toBeEnabled();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await page.screenshot({
    path: `${output}/landing-desktop.png`,
    fullPage: true,
  });
  await accessible("landing");
  const radios = page.getByRole("radio");
  await radios.first().focus();
  await page.keyboard.press("ArrowRight");
  await expect(radios.nth(1)).toBeChecked();
  await page.keyboard.press("Home");
  await expect(radios.first()).toBeChecked();
  record("keyboard skip link and scenario radio navigation");
  const id = await launch();
  report.primary_run_id = id;
  const before = await getRun(id);
  expect(before.status).toBe("AWAITING_REVIEW");
  expect(before.artifacts.decision).toBeUndefined();
  for (const stage of before.stages)
    await expect(page.getByTestId(`stage-${stage.stage}`)).toHaveAttribute(
      "data-status",
      stage.status,
    );
  record("UI statuses match persisted backend before human decision", {
    correlation_id: id,
    stages: before.stages,
  });
  await page.screenshot({
    path: `${output}/journey-desktop.png`,
    fullPage: true,
  });
  await accessible("journey");
  await page
    .getByTestId("stage-score")
    .locator(":scope > details > summary")
    .click();
  await page
    .getByTestId("stage-score")
    .getByRole("link", { name: "Policy snapshot" })
    .click();
  await expect(
    page.getByTestId("stage-snapshot").locator(":scope > details"),
  ).toHaveAttribute("open", "");
  record("stage input links navigate to persisted upstream evidence");
  await page.reload();
  await ready();
  expect(new URL(page.url()).searchParams.get("run")).toBe(id);
  record("refresh resumes the same correlation ID");
  await page.getByRole("button", { name: "Case dossier", exact: true }).click();
  await expect(
    page.getByText("What the model sees", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: `${output}/dossier-desktop.png`,
    fullPage: true,
  });
  await accessible("dossier");
  await page.getByRole("button", { name: "Human review", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Record decision" }),
  ).toBeDisabled();
  await page.getByRole("radio", { name: /Approve recommendation/ }).check();
  await page
    .getByLabel("Decision rationale")
    .fill(
      "Fictional browser review: checked released model, eligibility, allocation and cited evidence.",
    );
  await accessible("review");
  await page.getByRole("button", { name: "Record decision" }).click();
  await expect(
    page.getByText("Your decision is recorded", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Inspect the audit trail" }).click();
  await expect(
    page.getByRole("heading", { name: "The recorded audit chain is intact." }),
  ).toBeVisible();
  const after = await getRun(id);
  const audit = await (
    await context.request.get(`${base}/api/v1/demo/runs/${id}/audit`)
  ).json();
  expect(after.status).toBe("COMPLETED");
  expect(after.case_version).toBe(1);
  expect(after.artifacts.decision.decision).toBe("APPROVED");
  expect(after.artifacts.decision.authorized_to_act).toBe(false);
  expect(audit.valid).toBe(true);
  record(
    "public UI human approval persisted and audit independently returned valid",
    { run: after, audit },
  );
  await accessible("audit");
  await page.screenshot({
    path: `${output}/audit-desktop.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Live journey", exact: true }).click();
  for (const stage of after.stages)
    await expect(page.getByTestId(`stage-${stage.stage}`)).toHaveAttribute(
      "data-status",
      stage.status,
    );
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: `${output}/journey-mobile.png`,
    fullPage: true,
  });
  await accessible("mobile");
  expect(
    await page.evaluate(
      () => matchMedia("(prefers-reduced-motion: reduce)").matches,
    ),
  ).toBe(true);
  record("mobile no horizontal overflow and reduced-motion enabled");
  await page.setViewportSize({ width: 1440, height: 1000 });

  // A backend-committed POST whose response is lost must retain its request key after refresh.
  await page.goto(base);
  let lostRun, lostKey;
  await page.route("**/api/v1/demo/runs", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    lostKey = route.request().headers()["idempotency-key"];
    const response = await route.fetch();
    lostRun = (await response.json()).correlation_id;
    await route.abort("connectionreset");
  });
  await page.getByRole("button", { name: "Start this case" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.unroute("**/api/v1/demo/runs");
  await page.reload();
  await expect(
    page.getByText(/An earlier submission is awaiting acknowledgment/),
  ).toBeVisible();
  const resumed = await launch();
  expect(resumed).toBe(lostRun);
  record(
    "lost submission response plus refresh reuses committed request identity",
    { correlation_id: lostRun, idempotency_key: lostKey },
  );

  // Delay actual GET replies beyond the polling interval, then interrupt/reconnect.
  await page.route(`**/api/v1/demo/runs/${resumed}`, async (route) => {
    const response = await route.fetch();
    await new Promise((resolve) => setTimeout(resolve, 2200));
    await route.fulfill({ response });
  });
  await page.reload();
  await ready();
  await expect(page.getByText("Reading live backend state")).toBeVisible();
  await page.unroute(`**/api/v1/demo/runs/${resumed}`);
  await page.route(`**/api/v1/demo/runs/${resumed}`, (route) =>
    route.abort("connectionreset"),
  );
  await expect(
    page.getByText("Connection interrupted", { exact: true }),
  ).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("stage-decision")).toHaveAttribute(
    "data-status",
    "waiting",
  );
  await page.unroute(`**/api/v1/demo/runs/${resumed}`);
  await page.getByRole("button", { name: "Reconnect to this run" }).click();
  await expect(page.getByText("Reading live backend state")).toBeVisible();
  record(
    "slow real replies do not starve polling; disconnected state preserves evidence and recovers",
  );
  await page.getByRole("button", { name: "Human review", exact: true }).click();
  await page.getByRole("radio", { name: /Reject recommendation/ }).check();
  await page
    .getByLabel("Decision rationale")
    .fill("Fictional recovery test: retain review without executing action.");
  await page.route(`**/api/v1/demo/runs/${resumed}/decision`, async (route) => {
    await route.fetch();
    await route.abort("connectionreset");
  });
  await page.getByRole("button", { name: "Record decision" }).click();
  await page.reload();
  await ready();
  await page.unroute(`**/api/v1/demo/runs/${resumed}/decision`);
  await page.getByRole("button", { name: "Human review", exact: true }).click();
  await expect(
    page.getByText("Your decision is recorded", { exact: true }),
  ).toBeVisible();
  const recovered = await getRun(resumed);
  expect(recovered.case_version).toBe(1);
  expect(recovered.artifacts.decision.decision).toBe("REJECTED");
  record(
    "lost decision response plus refresh recovers persisted human decision exactly once",
  );

  await page.goto(base);
  await page.getByRole("radio", { name: /A known legal hold/ }).click();
  const abstained = await launch();
  await expect(page.getByTestId("stage-agent")).toHaveAttribute(
    "data-status",
    "abstained",
  );
  await page.getByRole("button", { name: "Human review", exact: true }).click();
  await expect(
    page.getByRole("radio", { name: /Approve recommendation/ }),
  ).toBeDisabled();
  await page.getByRole("radio", { name: /Reject recommendation/ }).check();
  await page
    .getByLabel("Decision rationale")
    .fill(
      "Known fictional legal hold: reviewed abstention; no authority to act.",
    );
  await page.getByRole("button", { name: "Record decision" }).click();
  await expect(
    page.getByText("Your decision is recorded", { exact: true }),
  ).toBeVisible();
  record("legal-hold abstention is visible and approval unavailable", {
    correlation_id: abstained,
  });
  await page.getByRole("button", { name: "Architecture", exact: true }).click();
  await expect(page.getByText("Planned", { exact: true })).toBeVisible();
  record("architecture labels GCP Planned");
  expect(report.console_errors).toEqual([]);
  report.result = "PASS";
} catch (error) {
  report.error = String(error.stack || error);
  await page
    .screenshot({ path: `${output}/browser-failure.png`, fullPage: true })
    .catch(() => {});
  process.exitCode = 1;
} finally {
  await writeFile(`${output}/browser.json`, JSON.stringify(report, null, 2));
  await browser.close();
  console.log(`Browser ${report.result}: ${output}/browser.json`);
  if (report.error) console.error(report.error);
}
