import { expect, test, type Page } from "@playwright/test";

/**
 * E2E: support flow (TASK-040) — read-only console + audited impersonation.
 * Fixtures come from scripts/seed_e2e.py: e2e_support (agent),
 * e2e_site_root (site_admin — unimpersonatable), e2e_stu_a2 (student).
 * Password for every fixture: E2ePass!2026. Persian-first UI selectors.
 */

const PASSWORD = "E2ePass!2026";

async function login(page: Page, username: string) {
  for (let attempt = 0; attempt < 3; attempt++) {
    await page.goto("/login", { waitUntil: "load" });
    if (new URL(page.url()).pathname === "/app") return;
    await expect(page.getByLabel("نام کاربری")).toBeVisible({ timeout: 15_000 });
    await page.getByLabel("نام کاربری").fill(username);
    await page.getByLabel("رمز عبور").fill(PASSWORD);
    await page.getByRole("button", { name: "ورود" }).click();
    try {
      await expect(page).toHaveURL(/\/app/, { timeout: 30_000 });
      return;
    } catch {
      // click lost pre-hydration on a cold route — retry
    }
  }
  throw new Error(`Login failed after 3 attempts for ${username}`);
}

async function logout(page: Page) {
  await page.getByRole("button", { name: "پروفایل" }).click();
  await page.getByRole("menuitem", { name: "خروج" }).click();
  await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });
}

test.describe("support console (read-only + audited impersonation)", () => {
  test("agent searches, impersonates a student, banner + no admin surfaces; admin targets refused; audit event visible to site_admin", async ({ page }) => {
    // --- Support agent logs in and opens the console ---
    await login(page, "e2e_support");
    await page.getByRole("link", { name: "پشتیبانی" }).click();
    await expect(page).toHaveURL(/\/app\/support/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "کنسول پشتیبانی" })).toBeVisible({ timeout: 25_000 });

    // Read-only visibility: institutions render.
    await expect(page.getByText("E2E Alpha")).toBeVisible({ timeout: 15_000 });

    // --- Search finds the student, and the site_admin too ---
    await page.getByPlaceholder("جستجوی کاربران (نام کاربری یا نام)").fill("e2e_stu_a2");
    await page.getByRole("button", { name: "جستجو" }).click();
    const studentRow = page.locator("li", { hasText: "e2e_stu_a2" }).first();
    await expect(studentRow).toBeVisible({ timeout: 15_000 });

    // --- Impersonating a site_admin is refused in the UI ---
    await page.getByPlaceholder("جستجوی کاربران (نام کاربری یا نام)").fill("e2e_site_root");
    await page.getByRole("button", { name: "جستجو" }).click();
    const rootRow = page.locator("li", { hasText: "e2e_site_root" }).first();
    await expect(rootRow).toBeVisible({ timeout: 15_000 });
    await rootRow.getByRole("button", { name: "ورود به حساب" }).click();
    // The Alert component renders role="status" (ui.tsx) — match by text.
    await expect(page.getByText("Support cannot impersonate administrative accounts.")).toBeVisible({ timeout: 15_000 });
    // Still on the support page — no identity swap happened (no banner).
    await expect(page).toHaveURL(/\/app\/support/);
    await expect(page.getByText(/Viewing as|جلسه پشتیبانی/)).toHaveCount(0);

    // --- Impersonate the student: banner + normal dashboard ---
    await page.getByPlaceholder("جستجوی کاربران (نام کاربری یا نام)").fill("e2e_stu_a2");
    await page.getByRole("button", { name: "جستجو" }).click();
    await expect(studentRow).toBeVisible({ timeout: 15_000 });
    await studentRow.getByRole("button", { name: "ورود به حساب" }).click();

    // Banner appears with the target username.
    await expect(page.getByText(/Viewing as e2e_stu_a2|جلسه پشتیبانی/)).toBeVisible({ timeout: 20_000 });
    // Landed on the NORMAL dashboard — the student's home, no admin link.
    await expect(page).toHaveURL(/\/app\/?$/, { timeout: 20_000 });
    await expect(page.getByRole("link", { name: "پنل مدرسه" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "پنل سایت" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "پشتیبانی" })).toHaveCount(0);

    // Exit impersonation via the banner — back to the agent's console.
    await page.locator("[role=status]", { hasText: /Viewing as|جلسه پشتیبانی/ }).getByRole("button", { name: "خروج" }).click();
    await expect(page.getByText(/Viewing as|جلسه پشتیبانی/)).toHaveCount(0, { timeout: 15_000 });

    // Manual attempt at an admin surface with the (now exited) impersonated
    // context: navigation ends the in-memory session; the deep-link must
    // still be refused for this non-admin identity.
    await page.goto("/app/school-admin", { waitUntil: "load" });
    await expect(page).not.toHaveURL(/school-admin/, { timeout: 15_000 });
    // The support agent's own session is restored — nav link back.
    await expect(page.getByRole("link", { name: "پشتیبانی" })).toBeVisible({ timeout: 15_000 });

    await logout(page);

    // --- site_admin sees the impersonation.start audit event ---
    await login(page, "e2e_site_root");
    await page.getByRole("link", { name: "پنل سایت" }).click();
    await expect(page).toHaveURL(/\/app\/site-admin/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "مدیریت کل سایت" })).toBeVisible({ timeout: 25_000 });
    await page.getByPlaceholder("عملیات").fill("impersonation.start");
    await expect(page.getByText("impersonation.start").first()).toBeVisible({ timeout: 20_000 });
    // actor:support + target:student recorded.
    await expect(page.getByText(/actor:\d+/).first()).toBeVisible();
  });
});
