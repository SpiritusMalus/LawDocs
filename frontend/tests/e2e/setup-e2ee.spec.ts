import { test, expect, type Page } from "@playwright/test";

// Mock navigator.clipboard so setPhraseCopied(true) fires in the component.
async function mockClipboard(page: Page) {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: () => Promise.resolve() },
      configurable: true,
      writable: true,
    });
  });
}

// Intercept the backend call so the test doesn't need an actual server.
async function mockSetupE2eeApi(page: Page) {
  await page.route("**/api/auth/setup-e2ee", (route) => {
    route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
}

test.describe("setup-e2ee page", () => {
  test("shows recovery phrase after page load", async ({ page }) => {
    await mockClipboard(page);
    await mockSetupE2eeApi(page);

    await page.goto("/setup-e2ee?next=/dashboard");

    // Heading appears once key generation completes
    await expect(page.getByRole("heading", { name: "Настройте защиту документов" })).toBeVisible();

    // Recovery phrase is rendered in a monospace element
    const phraseEl = page.locator("p.font-mono");
    await expect(phraseEl).toBeVisible();
    const phrase = await phraseEl.textContent();
    expect(phrase).toMatch(/\S+ — \S+ — \S+ — \S+/);
  });

  test("copy + confirm enables the Continue button", async ({ page }) => {
    await mockClipboard(page);
    await mockSetupE2eeApi(page);

    await page.goto("/setup-e2ee?next=/dashboard");
    await expect(page.getByRole("heading", { name: "Настройте защиту документов" })).toBeVisible();

    const phraseEl = page.locator("p.font-mono");
    await expect(phraseEl).toBeVisible();
    const phrase = await phraseEl.textContent() ?? "";

    // Click copy button → confirmation input appears
    await page.getByRole("button", { name: /Скопировать фразу/ }).click();
    const input = page.getByPlaceholder("Вставьте фразу сюда…");
    await expect(input).toBeVisible();

    // Continue is disabled until phrase confirmed
    await expect(page.getByRole("button", { name: "Продолжить" })).toBeDisabled();

    // Type the phrase
    await input.fill(phrase.trim());
    await expect(page.locator("text=✓ Фраза подтверждена")).toBeVisible();
    await expect(page.getByRole("button", { name: "Продолжить" })).toBeEnabled();
  });

  test("submits keys to API and shows done state", async ({ page }) => {
    await mockClipboard(page);
    await mockSetupE2eeApi(page);

    // Prevent redirect after done so we can assert the success message
    await page.route("**", (route) => route.continue());

    await page.goto("/setup-e2ee?next=/setup-e2ee"); // next loops back; avoids external nav

    await expect(page.getByRole("heading", { name: "Настройте защиту документов" })).toBeVisible();

    const phraseEl = page.locator("p.font-mono");
    const phrase = await phraseEl.textContent() ?? "";

    await page.getByRole("button", { name: /Скопировать фразу/ }).click();
    await page.getByPlaceholder("Вставьте фразу сюда…").fill(phrase.trim());
    await page.getByRole("button", { name: "Продолжить" }).click();

    await expect(page.locator("text=Защита настроена")).toBeVisible({ timeout: 10_000 });
  });
});
