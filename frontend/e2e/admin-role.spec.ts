import { test, expect, loginAs, navigateViaSidebar } from './test-base';

test.describe('Admin Roles Management — Super Admin & Center Admin (UAT)', () => {

  test('TC-ADMIN-01: Super Admin — Dashboard & Quản lý thành viên (/members)', async ({ page }) => {
    await loginAs(page, 'superadmin@cams.com', 'Super@2026!');

    // 1. Kiểm tra Dashboard
    await expect(page).toHaveURL(/.*(\/|$)/);
    await expect(page.locator('h1')).toContainText('Vũ Tổng Quản');
    await expect(page.locator('body')).toContainText(/super_admin/i);

    // 2. Vào Quản lý thành viên (/members)
    await navigateViaSidebar(page, 'Quản lý thành viên', '/members');
    await expect(page).toHaveURL(/.*\/members/);
    await page.waitForLoadState('domcontentloaded');

    // Bảng danh sách thành viên phải hiển thị
    const memberRows = page.locator('tbody tr');
    await expect(memberRows.first()).toBeVisible({ timeout: 15000 });

    // Kiểm tra tính năng chỉnh sửa cơ sở trực thuộc (chỉ Super Admin có quyền đổi Center)
    const editBtn = page.locator('button[title*="Chỉnh sửa"]').or(page.locator('button:has(svg.lucide-edit-2)'));
    if (await editBtn.first().isVisible().catch(() => false)) {
      await editBtn.first().click();
      // Modal chỉnh sửa hiển thị
      const editModal = page.locator('div[role="dialog"]').or(page.getByText(/Chỉnh sửa thành viên|Thông tin thành viên/i));
      await expect(editModal.first()).toBeVisible({ timeout: 5000 });

      // Nút đóng modal
      const closeBtn = page.locator('button:has(svg.lucide-x)').or(page.locator('button:has-text("Hủy")'));
      await closeBtn.first().click();
    }
  });

  test('TC-ADMIN-02: Center Admin — Quản lý lớp học (/classes) & Chi tiết lớp không bị lỗi .forEach', async ({ page }) => {
    await loginAs(page, 'admin@cams.com', 'Admin@2026!');

    // Điều hướng vào trang Lớp học (/classes)
    await navigateViaSidebar(page, 'Lớp học', '/classes');
    await expect(page).toHaveURL(/.*\/classes/);
    await page.waitForLoadState('domcontentloaded');

    // Chờ danh sách lớp xuất hiện
    const classLinks = page.locator('a[href^="/classes/"]');
    await expect(classLinks.first()).toBeVisible({ timeout: 15000 });

    // Nhấp vào chi tiết của lớp học đầu tiên
    await classLinks.first().click();
    await page.waitForURL(/.*\/classes\/[0-9a-fA-F-]+/, { timeout: 15000 });
    await page.waitForLoadState('domcontentloaded');

    // Xác nhận chi tiết lớp hiển thị bình thường, KHÔNG BỊ CRASH LỖI .forEach hay ErrorBoundary
    await expect(page.locator('body')).not.toContainText('Đã xảy ra sự cố hiển thị');
    await expect(page.locator('body')).not.toContainText('is not a function');
    await expect(page.locator('body')).not.toContainText('.forEach');
  });

  test('TC-ADMIN-03: Center Admin — Học phí & Hóa đơn (/invoices)', async ({ page }) => {
    await loginAs(page, 'admin@cams.com', 'Admin@2026!');

    // Lắng nghe API GET /api/invoices/center
    const invoicesPromise = page.waitForResponse(
      (resp) => resp.url().includes('/invoices/center') && resp.status() === 200,
      { timeout: 15000 }
    ).catch(() => null);

    // Vào trang Học phí & Hóa đơn (/invoices)
    await navigateViaSidebar(page, 'Học phí & Hóa đơn', '/invoices');
    await expect(page).toHaveURL(/.*\/invoices/);

    await invoicesPromise;
    await page.waitForLoadState('domcontentloaded');

    // Đảm bảo trang hiển thị bảng hoặc danh sách hóa đơn không có lỗi
    await expect(page.locator('body')).not.toContainText('Đã xảy ra sự cố hiển thị');
  });

});
