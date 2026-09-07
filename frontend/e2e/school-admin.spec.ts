import { expect, test, type Page } from "@playwright/test";

/**
 * E2E: school_admin flow through the real UI.
 *
 * Fixtures (scripts/seed_e2e.py, ephemeral SQLite):
 * - Institution A "E2E Alpha": admin_a, teacher_a, students stu_a1
 *   (pre-assigned to "Alpha Pre-seeded") + stu_a2, one class.
 * - Institution B "E2E Beta": admin_b, teacher_b, stu_b1, one class.
 *
 * Password for every fixture: E2ePass!2026
 *
 * NOTE: the product is Persian-first — the UI renders fa (RTL) unless
 * localStorage `sp_lang` says otherwise. These specs therefore assert the
 * default-language strings (نام کاربری / ورود / کلاس‌ها / ...). Switching
 * the language mid-test would also cover the fa⇄en flip, but that is
 * visual-QA territory (docs/redesign/08-visual-qa.md), not this spec.
 */

const PASSWORD = "E2ePass!2026";

/** Class names render twice: as list-row paragraphs AND as <option> text
 * inside every member's class Select. Scope name assertions to <p> so the
 * member dropdowns don't inflate the match count. */
const classText = (page: Page, name: string) => page.locator("p", { hasText: name });

function attachDiagnostics(page: Page): string[] {
  const consoleErrors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") consoleErrors.push(m.text());
  });
  page.on("requestfailed", (r) =>
    consoleErrors.push(`REQFAIL: ${r.url()} ${r.failure()?.errorText}`),
  );
  page.on("response", (r) => {
    if (r.status() >= 400) {
      console.log(`HTTP ${r.status()} ${r.request().method()} ${r.url()}`);
    }
  });
  return consoleErrors;
}

async function login(page: Page, username: string, consoleErrors: string[]) {
  // Retry: on a slow/failed click the URL stays /login and we go again.
  for (let attempt = 0; attempt < 3; attempt++) {
    await page.goto("/login", { waitUntil: "load" });
    // Middleware bounces already-authed users from /login to /app — a
    // slow first-compile login can land here on a retry after the
    // toHaveURL window expired. Treat it as success.
    if (new URL(page.url()).pathname === "/app") return;
    // Fail fast per attempt instead of letting fill() eat the test timeout.
    await expect(page.getByLabel("نام کاربری")).toBeVisible({ timeout: 10_000 });
    await page.getByLabel("نام کاربری").fill(username);
    await page.getByLabel("رمز عبور").fill(PASSWORD);
    await page.getByRole("button", { name: "ورود" }).click();
    try {
      await expect(page).toHaveURL(/\/app/, { timeout: 30_000 });
      return;
    } catch {
      const alerts = await page.locator("[role=alert]").allTextContents();
      console.log(`login attempt ${attempt + 1} for ${username} failed. url=${page.url()} alerts=${JSON.stringify(alerts)} console=${consoleErrors.slice(-5).join(" | ")}`);
    }
  }
  throw new Error(`Login failed after 3 attempts for ${username}. url=${page.url()} console=${consoleErrors.slice(-10).join(" | ")}`);
}

async function logout(page: Page) {
  await page.getByRole("button", { name: "پروفایل" }).click();
  // Radix DropdownMenu items expose role="menuitem", not "button".
  await page.getByRole("menuitem", { name: "خروج" }).click();
  await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });
}

async function goToSchoolAdmin(page: Page, consoleErrors: string[], expectedClass: string) {
  // Hydration on a cold dev-compiled route can swallow the first click,
  // and Turbopack's first SSR pass may throw ("clientReferenceManifest")
  // and render nothing — a reload after the compile finishes fixes both.
  // The page-level role gate still applies to the deep-link fallback.
  for (let attempt = 0; attempt < 4; attempt++) {
    if (attempt === 0) {
      await page.getByRole("link", { name: "پنل مدرسه" }).click();
    } else {
      await page.goto("/app/school-admin", { waitUntil: "load" });
    }
    try {
      await expect(page).toHaveURL(/\/app\/school-admin/, { timeout: 10_000 });
    } catch {
      continue; // bounced to /app or click lost — retry
    }
    try {
      // Wait past hydration AND data load: only once the admin's own class
      // renders are later in-page interactions safe from swallowed clicks.
      await expect(classText(page, expectedClass)).toBeVisible({ timeout: 25_000 });
      return;
    } catch {
      console.log(
        `school-admin load attempt ${attempt + 1} failed. url=${page.url()} ` +
        `body=${JSON.stringify((await page.locator("body").innerText().catch(() => "")).slice(0, 300))} ` +
        `console=${consoleErrors.slice(-4).join(" | ")}`,
      );
    }
  }
  throw new Error("Could not load /app/school-admin with data");
}

test.describe("school_admin dashboard (institution-scoped)", () => {
  test("admin of A sees only A, manages classes/assignments, B stays invisible", async ({ page }) => {
    // --- Institution A's admin: full happy path ---
    const consoleErrors = attachDiagnostics(page);
    await login(page, "e2e_admin_a", consoleErrors);
    await goToSchoolAdmin(page, consoleErrors, "Alpha Pre-seeded");

    // Only A's people are visible.
    await expect(page.getByText("Stu Alpha One")).toBeVisible();
    await expect(page.getByText("Stu Alpha Two")).toBeVisible();
    await expect(page.getByText("Teacher Alpha")).toBeVisible();
    await expect(page.getByText("Stu Beta One")).toHaveCount(0);
    await expect(page.getByText("Teacher Beta")).toHaveCount(0);

    // Only A's class is listed (pre-seeded).
    await expect(classText(page, "Alpha Pre-seeded")).toBeVisible();
    await expect(classText(page, "Beta Pre-seeded")).toHaveCount(0);

    // Create a class (fa UI: "نام کلاس" / "پایه تحصیلی" / "+ ایجاد").
    await page.getByLabel("نام کلاس").fill("Alpha E2E New");
    await page.getByLabel("پایه تحصیلی (اختیاری)").fill("11");
    await page.getByRole("button", { name: "ایجاد" }).click();
    await expect(classText(page, "Alpha E2E New")).toBeVisible({ timeout: 10_000 });

    // Rename it. Clicking Edit replaces the row's text with inputs, so the
    // row must be re-located by position, not by its (now-gone) name text.
    const classRows = page.locator("ul > li").filter({ has: page.getByRole("button", { name: "ویرایش" }) });
    const newClassRow = classRows.filter({ hasText: "Alpha E2E New" }).first();
    await newClassRow.getByRole("button", { name: "ویرایش" }).click();
    // While editing, the row renders the inline form — find it by the input.
    const editRow = page.locator("li").filter({ has: page.getByRole("button", { name: "ذخیره" }) });
    const nameInput = editRow.locator("input").first();
    await expect(nameInput).toHaveValue("Alpha E2E New", { timeout: 10_000 });
    await nameInput.fill("Alpha E2E Renamed");
    await editRow.getByRole("button", { name: "ذخیره" }).click();
    await expect(classText(page, "Alpha E2E Renamed")).toBeVisible({ timeout: 10_000 });
    await expect(classText(page, "Alpha E2E New")).toHaveCount(0);

    // Assign stu_a2 to the renamed class via the row Select.
    const stuA2Row = page.locator("li", { hasText: "Stu Alpha Two" }).first();
    const stuA2Select = stuA2Row.locator("select");
    await stuA2Select.selectOption({ label: "Alpha E2E Renamed" });
    await expect(stuA2Select).toHaveValue(/^\d+$/, { timeout: 10_000 });
    const assignedClassId = await stuA2Select.inputValue();

    // Re-load proves the assignment persisted.
    await page.reload();
    const stuA2After = page.locator("li", { hasText: "Stu Alpha Two" }).first();
    await expect(stuA2After.locator("select")).toHaveValue(assignedClassId, { timeout: 15_000 });

    // The page URL carries no resource IDs — the tenancy boundary lives in
    // the API, so cross-tenant rejection is exercised the other direction:
    // after switching to admin B below, no A content may appear anywhere.
    await expect(page.getByText(/E2E Beta|Admin Beta|Stu Beta One|Teacher Beta|Beta Pre-seeded/)).toHaveCount(0);

    await logout(page);

    // --- Institution B's admin: A is nowhere ---
    await login(page, "e2e_admin_b", consoleErrors);
    await goToSchoolAdmin(page, consoleErrors, "Beta Pre-seeded");

    await expect(page.getByText("Stu Beta One")).toBeVisible();
    await expect(page.getByText("Teacher Beta")).toBeVisible();
    await expect(classText(page, "Beta Pre-seeded")).toBeVisible();

    await expect(page.getByText("Stu Alpha One")).toHaveCount(0);
    await expect(page.getByText("Stu Alpha Two")).toHaveCount(0);
    await expect(page.getByText("Teacher Alpha")).toHaveCount(0);
    await expect(classText(page, "Alpha Pre-seeded")).toHaveCount(0);
    await expect(classText(page, "Alpha E2E Renamed")).toHaveCount(0);

    await logout(page);
  });

  test("non-school_admin user is bounced from /app/school-admin", async ({ page }) => {
    // teacher_a is a signed-in member of A but has no admin rights: the
    // page must bounce them to the dashboard (UI gate mirrors API 403).
    const consoleErrors2 = attachDiagnostics(page);
    await login(page, "e2e_teacher_a", consoleErrors2);
    await page.goto("/app/school-admin");
    await expect(page).not.toHaveURL(/school-admin/);
    await expect(page).toHaveURL(/\/app$/);
  });
});
