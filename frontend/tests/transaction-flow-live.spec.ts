/** Real local-backend smoke; opt in after `make demo-up`. No response fixtures. */
import { expect, test } from "@playwright/test";
import type { Run } from "../src/api";

test("the transaction graph matches a real persisted demo journey", async ({ page }, testInfo) => {
  test.skip(process.env.INFORSIGHT_FLOW_LIVE !== "1", "Requires the local fictional Docker backend");
  test.setTimeout(120_000);
  await page.goto("/");
  await page.getByRole("button", { name: "Start this case", exact: true }).click();
  await expect(page).toHaveURL(/\?run=run_[a-f0-9]+/);
  const id = new URL(page.url()).searchParams.get("run")!;
  await page.getByRole("button", { name: "Transaction flow", exact: true }).click();
  await expect(page.getByTestId("flow-node-agent")).toHaveAttribute("data-status", /completed|abstained/, { timeout: 90_000 });
  const response = await page.request.get(`/api/v1/demo/runs/${id}`);
  expect(response.ok()).toBeTruthy();
  const persisted: Run = await response.json();
  expect(persisted.status).toBe("AWAITING_REVIEW");
  for (const stage of persisted.stages) {
    await expect(page.getByTestId(`flow-node-${stage.stage}`)).toHaveAttribute("data-status", stage.status);
  }
  await page.getByTestId("flow-node-score").click();
  await page.getByRole("tab", { name: "Output", exact: true }).click();
  await expect(page.getByTestId("flow-inspector")).toContainText("calibrated_probability");
  const screenshot = testInfo.outputPath("real-flow-desktop.png");
  await page.screenshot({ path: screenshot, fullPage: true });
  await testInfo.attach("Real persisted transaction flow", { path: screenshot, contentType: "image/png" });

  const writes: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api/") && request.method() !== "GET")
      writes.push(`${request.method()} ${request.url()}`);
  });
  await page.getByRole("button", { name: "Replay recorded flow", exact: true }).click();
  const pause = page.getByRole("button", { name: "Pause replay", exact: true });
  if (await pause.isVisible()) await pause.click();
  const range = page.getByRole("slider", { name: "Replay position", exact: true });
  await range.focus();
  await page.keyboard.press("End");
  await expect(page.getByTestId("flow-node-decision")).toHaveAttribute("data-status", "waiting");
  await page.getByRole("button", { name: "Return to live", exact: true }).click();
  expect(writes).toEqual([]);
  const after: Run = await (await page.request.get(`/api/v1/demo/runs/${id}`)).json();
  expect(after.case_version).toBe(persisted.case_version);
  expect(after.artifacts.decision).toBeUndefined();
  expect(after.stages).toEqual(persisted.stages);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByTestId("flow-node-score").click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: testInfo.outputPath("real-flow-mobile.png"), fullPage: true });
});
