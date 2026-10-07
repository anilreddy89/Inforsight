/** Declared API fixtures for browser-history behavior, never application evidence. */
import { expect, test, type BrowserContext } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const key = "inforsight.recent-runs.v1";
const run = (id: string) => ({
  correlation_id: id,
  scenario_id: "late-payment",
  status: "COMPLETED",
  created_at: "2026-10-07T12:00:00Z",
  updated_at: "2026-10-07T12:00:01Z",
  stages: [],
  artifacts: { private_payload: { secret: "must-not-be-stored" } },
});
async function setup(context: BrowserContext) {
  let owner = "visitor-history-fixture",
    expired = false;
  const writes: string[] = [];
  await context.route("**/api/v1/demo/**", async (route) => {
    const request = route.request(),
      path = new URL(request.url()).pathname;
    if (request.method() !== "GET") writes.push(`${request.method()} ${path}`);
    if (path.endsWith("/session"))
      return route.fulfill({
        json: {
          public_mode: false,
          session_tag: owner,
          csrf_token: null,
          expires_at: null,
          environment: "local",
          limits: {},
        },
      });
    if (path.endsWith("/scenarios"))
      return route.fulfill({
        json: {
          scenarios: [
            {
              scenario_id: "late-payment",
              title: "A payment falls behind",
              description: "Fixture",
              enabled: true,
            },
          ],
        },
      });
    if (path.endsWith("/runs") && request.method() === "POST")
      return route.fulfill({ json: run("run_new") });
    if (path.includes("/runs/"))
      return expired
        ? route.fulfill({ status: 410, json: { code: "RUN_EXPIRED" } })
        : route.fulfill({ json: run(path.split("/").at(-1)!) });
    return route.fulfill({ status: 404, json: {} });
  });
  return {
    changeOwner: () => {
      owner = "another-visitor";
    },
    expire: () => {
      expired = true;
    },
    writes,
  };
}

test("successful runs survive a new tab, reopen without an ID, and store metadata only", async ({
  page,
  context,
}) => {
  await setup(context);
  await page.goto("/");
  await page
    .getByRole("button", { name: "Start this case", exact: true })
    .click();
  await expect(page).toHaveURL(/run=run_new/);
  await expect
    .poll(() => page.evaluate((k) => localStorage.getItem(k), key))
    .toContain("run_new");
  const saved = await page.evaluate((k) => localStorage.getItem(k), key);
  expect(saved).not.toContain("private_payload");
  expect(saved).not.toContain("secret");
  const other = await context.newPage();
  await other.goto("/");
  await other.getByRole("button", { name: /Recent runs/ }).click();
  const popup = other.getByRole("dialog", { name: "Recent runs", exact: true });
  await expect(popup).toContainText("run_new");
  await expect(popup).toContainText("completed");
  await popup
    .getByRole("button", { name: /Open A payment falls behind/ })
    .click();
  await expect(other).toHaveURL(/run=run_new/);
  await expect(popup).not.toBeVisible();
  await other
    .getByRole("button", { name: "Inforsight home", exact: true })
    .click();
  await other.getByRole("button", { name: /Recent runs/ }).click();
  await expect(popup.locator("li")).toHaveCount(1);
});

test("empty popup supports Escape, restores focus, and passes accessibility", async ({
  page,
  context,
}) => {
  await setup(context);
  await page.goto("/");
  const trigger = page.getByRole("button", {
    name: "Recent runs",
    exact: true,
  });
  await trigger.click();
  const popup = page.getByRole("dialog", { name: "Recent runs", exact: true });
  await expect(popup).toContainText("Your next case starts your history");
  await expect(
    popup.getByRole("button", { name: "Close recent runs" }),
  ).toBeFocused();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(popup).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test("history respects visitor changes and recovers from damaged storage", async ({
  page,
  context,
}) => {
  const fixture = await setup(context);
  await page.goto("/?run=run_old_visitor");
  await expect
    .poll(() => page.evaluate((k) => localStorage.getItem(k), key))
    .toContain("run_old_visitor");
  fixture.changeOwner();
  await page.goto("/");
  await page.getByRole("button", { name: /Recent runs/ }).click();
  await expect(page.getByRole("dialog")).not.toContainText("run_old_visitor");
  await page.keyboard.press("Escape");
  await page.evaluate((k) => localStorage.setItem(k, "{broken"), key);
  await page.reload();
  await page
    .getByRole("button", { name: "Start this case", exact: true })
    .click();
  await expect
    .poll(() => page.evaluate((k) => localStorage.getItem(k), key))
    .toContain("run_new");
});

test("search, removal, cross-tab synchronization and retention errors never delete backend runs", async ({
  page,
  context,
}) => {
  const fixture = await setup(context);
  await page.goto("/?run=run_keep");
  await expect
    .poll(() => page.evaluate((k) => localStorage.getItem(k), key))
    .toContain("run_keep");
  await page.goto("/?run=run_expired");
  await expect
    .poll(() => page.evaluate((k) => localStorage.getItem(k), key))
    .toContain("run_expired");
  await page
    .getByRole("button", { name: "Inforsight home", exact: true })
    .click();
  await page.getByRole("button", { name: /Recent runs/ }).click();
  await page.getByRole("searchbox", { name: "Find a run" }).fill("expired");
  await expect(page.getByRole("dialog").locator("li")).toHaveCount(1);
  fixture.expire();
  await page
    .getByRole("button", {
      name: "Open A payment falls behind, run_expired",
      exact: true,
    })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "retention period has ended",
  );
  await page
    .getByRole("button", { name: "Inforsight home", exact: true })
    .click();
  await page.getByRole("button", { name: /Recent runs/ }).click();
  await expect(page.getByRole("dialog")).toContainText("Removed by retention");
  await page
    .getByRole("button", {
      name: "Remove run_expired from recent runs",
      exact: true,
    })
    .click();
  await expect(page.getByRole("dialog").locator("li")).toHaveCount(1);
  const other = await context.newPage();
  await other.goto("/");
  await other.getByRole("button", { name: /Recent runs/ }).click();
  await other
    .getByRole("button", { name: "Clear recent history", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "Your next case starts your history",
  );
  expect(fixture.writes).toEqual([]);
});

test("history is bounded, deduplicated, ordered, and accessible on mobile", async ({
  page,
  context,
}) => {
  await setup(context);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.evaluate((k) => {
    const runs = Array.from({ length: 25 }, (_, i) => ({
      correlation_id: `run_${i}`,
      scenario_id: "late-payment",
      status: "COMPLETED",
      created_at: "2026-10-07T12:00:00Z",
      updated_at: "2026-10-07T12:00:01Z",
      last_opened_at: `2026-10-07T12:00:${String(i).padStart(2, "0")}Z`,
    }));
    localStorage.setItem(
      k,
      JSON.stringify({
        version: 1,
        owner: "visitor-history-fixture",
        runs: [...runs, runs[0], { malformed: true }],
      }),
    );
  }, key);
  await page.reload();
  await page.getByRole("button", { name: /Recent runs/ }).click();
  const popup = page.getByRole("dialog");
  await expect(popup.locator("li")).toHaveCount(20);
  await expect(popup.locator("li").first()).toContainText("run_24");
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.getByRole("searchbox").fill("no-match");
  await expect(popup).toContainText("No matching runs");
});

test("blocked storage retains in-tab history and discloses its limits", async ({
  page,
  context,
}) => {
  await setup(context);
  await page.addInitScript((k) => {
    const get = Storage.prototype.getItem,
      set = Storage.prototype.setItem;
    Storage.prototype.getItem = function (name) {
      if (name === k) throw new Error("Storage unavailable");
      return get.call(this, name);
    };
    Storage.prototype.setItem = function (name, value) {
      if (name === k) throw new Error("Storage unavailable");
      return set.call(this, name, value);
    };
  }, key);
  await page.goto("/?run=run_memory");
  await expect(
    page.getByText("Persisted record loaded", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Inforsight home", exact: true })
    .click();
  await page.getByRole("button", { name: /Recent runs/ }).click();
  await expect(page.getByRole("dialog")).toContainText("run_memory");
  await expect(page.getByRole("dialog")).toContainText(
    "Browser storage is unavailable",
  );
});
