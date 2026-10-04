/** Real public-UI qualification. Network probes drop/delay real replies; never fabricate backend evidence. */
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const require = createRequire(resolve("frontend/package.json"));
const { chromium, expect } = require("@playwright/test");
const { default: AxeBuilder } = require("@axe-core/playwright");
const base = process.env.DEMO_URL || "http://localhost:3000";
const output = resolve(process.env.DEMO_OUTPUT || "artifacts/local-demo");
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
const getRun = async (id) => {
  const response = await context.request.get(`${base}/api/v1/demo/runs/${id}`);
  expect(response.status()).toBe(200);
  return response.json();
};
let visitor;
async function publicIsolation(id) {
  if (!visitor.public_mode) return;
  const sessionCookie = (await context.cookies(base)).find((cookie) => cookie.name === "__Host-inforsight_session");
  expect(sessionCookie, "signed visitor cookie").toBeTruthy();
  expect(sessionCookie.httpOnly).toBe(true);
  expect(sessionCookie.sameSite).toBe("Strict");
  if (new URL(base).protocol === "https:") expect(sessionCookie.secure).toBe(true);
  record("public visitor uses protected cookie and private responses", {
    cookie_name: sessionCookie.name,
    http_only: sessionCookie.httpOnly,
    same_site: sessionCookie.sameSite,
    secure: sessionCookie.secure,
    expires_at: visitor.expires_at,
    limits: visitor.limits,
  });
  const other = await browser.newContext();
  try {
    const otherSession = await (await other.request.get(`${base}/api/v1/demo/session`)).json();
    expect(otherSession.session_tag).not.toBe(visitor.session_tag);
    for (const suffix of ["", "/audit"])
      expect((await other.request.get(`${base}/api/v1/demo/runs/${id}${suffix}`)).status()).toBe(404);
    const headers = { "X-Demo-CSRF": otherSession.csrf_token, Origin: new URL(base).origin };
    expect((await other.request.post(`${base}/api/v1/demo/runs/${id}/retry`, { headers, data: {} })).status()).toBe(404);
    expect((await other.request.post(`${base}/api/v1/demo/runs/${id}/decision`, {
      headers,
      data: { decision: "REJECTED", expected_case_version: 0, idempotency_key: crypto.randomUUID(), rationale: "Must be denied to another visitor." },
    })).status()).toBe(404);
    const otherPage = await other.newPage();
    await otherPage.goto(`${base}/?run=${id}`);
    await expect(otherPage.getByText("This run is unavailable in this browser", { exact: true })).toBeVisible();
    await expect(otherPage.getByTestId("stage-score")).toHaveCount(0);
    record("another visitor cannot read, review, retry, or resume a copied correlation ID", { correlation_id: id, denied_status: 404 });
  } finally {
    await other.close();
  }
  const noCsrf = await context.request.post(`${base}/api/v1/demo/runs`, {
    headers: { "Idempotency-Key": crypto.randomUUID(), Origin: new URL(base).origin }, data: { scenario_id: "late-payment", overrides: {} },
  });
  expect(noCsrf.status()).toBe(403);
  const crossOrigin = await context.request.post(`${base}/api/v1/demo/runs`, {
    headers: { "Idempotency-Key": crypto.randomUUID(), "X-Demo-CSRF": visitor.csrf_token, Origin: "https://untrusted.invalid" }, data: { scenario_id: "late-payment", overrides: {} },
  });
  expect(crossOrigin.status()).toBe(403);
  for (const path of ["/api/v1/demo/reset", "/api/v1/health", "/api/v1/score"])
    expect((await context.request.get(`${base}${path}`)).status()).toBe(404);
  record("public gateway rejects missing CSRF, cross-origin writes and non-demo service routes");
}
async function publicLimitState(id) {
  if (!visitor.public_mode || process.env.DEMO_BROWSER_LIMITS !== "1") return;
  let limited;
  let retryAfter = 0;
  const bound = Number(visitor.limits.polls_per_minute ?? 120) * 2 + 3;
  for (let attempt = 0; attempt < 2; attempt++) {
    for (let index = 0; index < bound; index++) {
      const response = await context.request.get(`${base}/api/v1/demo/runs/${id}`);
      if (response.status() === 429) { limited = response; break; }
      expect(response.status()).toBe(200);
      // Pace real requests below the gateway limit to test the durable session limit.
      await page.waitForTimeout(65);
    }
    expect(limited, "real session poll budget must be enforced").toBeTruthy();
    retryAfter = Number(limited.headers()["retry-after"]);
    if (retryAfter > 3) break;
    // At a fixed-window boundary a short rejection can end before the next UI read.
    // Repeat against the next real window so the visible paused state is observable.
    await page.waitForTimeout((retryAfter + 1) * 1000);
    limited = undefined;
  }
  expect(retryAfter).toBeGreaterThan(0);
  await expect(page.getByText("Polling paused by service", { exact: true })).toBeVisible({ timeout: 10000 });
  await expect(page.getByTestId("stage-agent")).toHaveAttribute("data-status", "completed");
  await expect(page.getByTestId("stage-decision")).toHaveAttribute("data-status", "waiting");
  await page.screenshot({ path: `${output}/rate-limit-evidence.png`, fullPage: true });
  record("real session rate limit pauses polling without changing persisted stages", { retry_after_seconds: retryAfter, correlation_id: id });
  await expect(page.getByText("Reading live backend state", { exact: true })).toBeVisible({ timeout: retryAfter * 1000 + 20000 });
  record("polling honors server Retry-After and recovers");
}
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
  const sessionResponse = await context.request.get(`${base}/api/v1/demo/session`);
  expect(sessionResponse.status()).toBe(200);
  visitor = await sessionResponse.json();
  report.public_mode = visitor.public_mode;
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
  await publicIsolation(id);
  await publicLimitState(id);
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
  const resumedSession = await (await context.request.get(`${base}/api/v1/demo/session`)).json();
  expect(resumedSession.session_tag).toBe(visitor.session_tag);
  record("refresh resumes the same correlation ID and visitor session");
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
  if (visitor.public_mode) {
    await expect(page.getByText("Public preview", { exact: true })).toBeVisible();
    await expect(page.getByText("One public gateway. Isolated visitor sessions.", { exact: true })).toBeVisible();
    record("public architecture explains private services and Mac availability");
  }
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
