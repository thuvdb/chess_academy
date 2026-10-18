import { test, expect, loginAs, logout, navigateViaSidebar } from './test-base';

test.describe('Student & Parent Roles (UAT)', () => {

  test('TC-STUDENT-01: Học sinh vào làm bài tập cờ (/practice), Bảng xếp hạng (/leaderboard), Giải đấu (/tournaments)', async ({ page }) => {
    await loginAs(page, 'student1@cams.com', 'Student@2026!');

    // 1. Kiểm tra Luyện tập bài tập cờ (/practice)
    await navigateViaSidebar(page, 'Luyện tập', '/practice');
    await expect(page).toHaveURL(/.*\/practice/);
    await page.waitForLoadState('domcontentloaded');

    // Bàn cờ hoặc giao diện tương tác bài tập cờ hiển thị
    await expect(page.locator('body')).not.toContainText('Đã xảy ra sự cố hiển thị');

    // 2. Kiểm tra Bảng xếp hạng (/leaderboard)
    await navigateViaSidebar(page, 'Bảng xếp hạng', '/leaderboard');
    await expect(page).toHaveURL(/.*\/leaderboard/);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toContainText('Đã xảy ra sự cố hiển thị');

    // 3. Kiểm tra Giải đấu cờ (/tournaments)
    await navigateViaSidebar(page, 'Giải đấu', '/tournaments');
    await expect(page).toHaveURL(/.*\/tournaments/);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toContainText('Đã xảy ra sự cố hiển thị');

    await logout(page);
  });

  test('TC-PARENT-01: Phụ huynh đăng nhập, xem tiến độ & kiểm tra hóa đơn (/invoices)', async ({ page }) => {
    await loginAs(page, 'parent1@cams.com', 'Parent@2026!');

    // 1. Kiểm tra Dashboard của Phụ huynh
    await expect(page).toHaveURL(/.*(\/|$)/);
    await expect(page.locator('body')).toContainText(/Phạm Văn Cha|parent/i);

    // 2. Vào mục Học phí & Hóa đơn (/invoices)
    await navigateViaSidebar(page, 'Học phí & Hóa đơn', '/invoices');
    await expect(page).toHaveURL(/.*\/invoices/);
    await page.waitForLoadState('domcontentloaded');

    // Trang hóa đơn tải thành công không gặp lỗi
    await expect(page.locator('body')).not.toContainText('Đã xảy ra sự cố hiển thị');

    await logout(page);
  });

});
