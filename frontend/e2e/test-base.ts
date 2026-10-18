import { test as base, expect, Page } from '@playwright/test';

interface CustomFixtures {
  allowedFailStatusCodes: number[];
}

export const test = base.extend<CustomFixtures>({
  // Cho phép định nghĩa các mã HTTP lỗi được phép xuất hiện (ví dụ [401] khi test cố tình nhập sai mật khẩu)
  allowedFailStatusCodes: [[], { option: true }],

  page: async ({ page, allowedFailStatusCodes }, use, testInfo) => {
    const pageErrors: string[] = [];
    const consoleErrors: string[] = [];
    const apiErrors: string[] = [];

    // 1. Bắt tất cả lỗi runtime JavaScript unhandled trên trang (pageerror)
    page.on('pageerror', (exception) => {
      pageErrors.push(exception.message || String(exception));
    });

    // 2. Bắt tất cả console.error
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Bỏ qua các cảnh báo tài nguyên icon hoặc kết nối dev WebSocket thông thường
        if (
          !text.includes('favicon.ico') &&
          !text.includes('Failed to load resource') &&
          !text.includes('WebSocket connection to')
        ) {
          consoleErrors.push(text);
        }
      }
    });

    // 3. Bắt các API response có status >= 400
    page.on('response', (response) => {
      const status = response.status();
      const url = response.url();
      if (status >= 400) {
        const dynamicAllowed: number[] = (page as any).__allowedFailStatusCodes || [];
        if (!allowedFailStatusCodes.includes(status) && !dynamicAllowed.includes(status)) {
          apiErrors.push(`[${status}] ${response.request().method()} ${url}`);
        }
      }
    });

    // Chạy nội dung test
    await use(page);

    // 4. Kiểm tra đảm bảo không bao giờ xuất hiện màn hình ErrorBoundary: "Đã xảy ra sự cố hiển thị"
    const errorBoundaryHeading = page.locator('h2', { hasText: 'Đã xảy ra sự cố hiển thị' });
    const isBoundaryVisible = await errorBoundaryHeading.isVisible().catch(() => false);
    expect(
      isBoundaryVisible,
      'ErrorBoundary detected! "Đã xảy ra sự cố hiển thị" appeared on page.'
    ).toBeFalsy();

    // 5. Kiểm tra không có pageerror
    expect(
      pageErrors,
      `Uncaught pageerror exceptions found: ${pageErrors.join(' | ')}`
    ).toHaveLength(0);

    // 6. Kiểm tra không có API trả về >= 400 ngoài dự kiến
    expect(
      apiErrors,
      `Unexpected API errors (>= 400) captured: ${apiErrors.join(' | ')}`
    ).toHaveLength(0);
  },
});

export { expect };

/**
 * Đăng nhập vào hệ thống CAMS
 */
export async function loginAs(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.waitForLoadState('domcontentloaded');

  const emailInput = page.locator('input[type="email"]');
  await emailInput.fill(email);

  const passwordInput = page.locator('input[type="password"]');
  await passwordInput.fill(password);

  const submitBtn = page.locator('button[type="submit"]');
  await submitBtn.click();

  // Chờ chuyển hướng khỏi trang login
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });
  await page.waitForLoadState('domcontentloaded');
}

/**
 * Đăng xuất khỏi hệ thống
 */
export async function logout(page: Page) {
  const isMobile = (page.viewportSize()?.width || 1280) < 768;

  if (isMobile) {
    const mobileDrawer = page.locator('aside[aria-label="Mobile Navigation"]');
    const isDrawerVisible = await mobileDrawer.isVisible().catch(() => false);
    if (!isDrawerVisible) {
      await page.locator('button[aria-label="Mở menu điều hướng"]').click();
      await expect(mobileDrawer).toBeVisible({ timeout: 5000 });
    }
    const logoutBtn = mobileDrawer.locator('button', { hasText: 'Đăng xuất' });
    await logoutBtn.click();
  } else {
    const desktopSidebar = page.locator('aside[aria-label="Desktop Navigation"]');
    const logoutBtn = desktopSidebar.locator('button[aria-label="Đăng xuất"]').or(desktopSidebar.locator('button:has-text("Đăng xuất")'));
    await logoutBtn.first().click();
  }

  await page.waitForURL('**/login', { timeout: 10000 });
}

/**
 * Điều hướng qua Sidebar tương thích cả màn hình Desktop và Mobile drawer
 */
export async function navigateViaSidebar(page: Page, label: string, expectedPath?: string) {
  const isMobile = (page.viewportSize()?.width || 1280) < 768;

  if (isMobile) {
    const mobileDrawer = page.locator('aside[aria-label="Mobile Navigation"]');
    const isDrawerVisible = await mobileDrawer.isVisible().catch(() => false);
    if (!isDrawerVisible) {
      const menuBtn = page.locator('button[aria-label="Mở menu điều hướng"]');
      await menuBtn.click();
      await expect(mobileDrawer).toBeVisible({ timeout: 5000 });
    }

    const navLink = mobileDrawer.locator(`a:has-text("${label}")`).first();
    await navLink.click();

    // Drawer tự động đóng sau khi click mục chuyển trang
    await expect(mobileDrawer).not.toBeVisible({ timeout: 5000 });
  } else {
    const desktopSidebar = page.locator('aside[aria-label="Desktop Navigation"]');
    const navLink = desktopSidebar.locator(`a:has-text("${label}")`).first();
    await navLink.click();
  }

  if (expectedPath) {
    await page.waitForURL(`**${expectedPath}*`, { timeout: 10000 });
  }
}

/**
 * Cho phép các mã HTTP lỗi cụ thể cho trang hiện tại (ví dụ [401] khi test mật khẩu sai)
 */
export function allowStatusCodes(page: Page, codes: number[]) {
  (page as any).__allowedFailStatusCodes = codes;
}

