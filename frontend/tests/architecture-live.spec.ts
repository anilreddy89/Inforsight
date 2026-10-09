/** Real local-backend smoke; opt in after `make demo-up`. No response fixtures. */
import { expect, test } from "@playwright/test";
import type { Run } from "../src/api";

test("the architecture explorer binds to a real persisted journey", async ({ page }) => {
  test.skip(process.env.INFORSIGHT_FLOW_LIVE !== "1", "Requires the local fictional Docker backend");
  test.setTimeout(120_000);
  await page.goto("/");
  await page.getByRole("button", { name: "Start this case", exact: true }).click();
  await expect(page).toHaveURL(/\?run=run_[a-f0-9]+/);
  const id = new URL(page.url()).searchParams.get("run")!;
  await page.getByRole("button", { name: "Architecture", exact: true }).click();
  await expect(page.getByTestId("arch-node-runtime")).toContainText(/agent: (draft for review|abstain)/, { timeout: 90_000 });

  const response = await page.request.get(`/api/v1/demo/runs/${id}`);
  expect(response.ok()).toBeTruthy();
  const persisted: Run = await response.json();
  expect(persisted.status).toBe("AWAITING_REVIEW");
  const publication = persisted.stages.find((stage) => stage.stage === "publication")!;
  await expect(page.getByTestId("arch-node-kafka")).toContainText(`offset ${publication.evidence?.offset}`);
  await expect(page.getByTestId("arch-node-kafka")).toHaveAttribute("data-status", "recorded");
  await expect(page.getByTestId("arch-node-inference")).toHaveAttribute("data-status", "recorded");
  await expect(page.getByTestId("arch-node-reviewer")).toHaveAttribute("data-status", "waiting");

  await page.getByTestId("arch-lens-sequence").click();
  for (const stage of persisted.stages) {
    const expected = stage.status === "completed" ? "recorded" : stage.status;
    await expect(page.getByTestId(`arch-band-${stage.stage}`)).toHaveAttribute("data-status", expected);
  }
  await page.getByTestId("arch-lens-lifecycle").click();
  await expect(page.getByTestId("arch-node-lc-awaiting")).toHaveAttribute("data-status", "current");
});
