import { test, expect, loginAs, navigateViaSidebar } from './test-base';

test.describe('Teacher Role Flows (UAT)', () => {

  test('TC-TEACHER-01: Kiểm tra Sidebar hiển thị Tiếng Việt & có mục "Quét AI bàn cờ"', async ({ page }) => {
    await loginAs(page, 'teacher1@cams.com', 'Teacher@2026!');

    const isMobile = (page.viewportSize()?.width || 1280) < 768;
    const navContainer = isMobile
      ? page.locator('aside[aria-label="Mobile Navigation"]')
      : page.locator('aside[aria-label="Desktop Navigation"]');

    if (isMobile) {
      await page.locator('button[aria-label="Mở menu điều hướng"]').click();
      await expect(navContainer).toBeVisible({ timeout: 5000 });
    }

    // 1. Kiểm tra mục bắt buộc "Quét AI bàn cờ" (AI Scanner) xuất hiện
    await expect(navContainer.locator('a:has-text("Quét AI bàn cờ")')).toBeVisible();

    // 2. Kiểm tra các mục Tiếng Việt chuẩn khác
    await expect(navContainer.locator('a:has-text("Lớp học")')).toBeVisible();
    await expect(navContainer.locator('a:has-text("Lịch học")')).toBeVisible();
    await expect(navContainer.locator('a:has-text("Kho bài tập cờ")')).toBeVisible();
    await expect(navContainer.locator('a:has-text("Bài tập về nhà")')).toBeVisible();

    // 3. Phân quyền: Giáo viên KHÔNG THỂ thấy menu quản lý trung tâm/hệ thống
    await expect(navContainer.locator('a:has-text("Quản lý thành viên")')).toHaveCount(0);
    await expect(navContainer.locator('a:has-text("Gói học phí")')).toHaveCount(0);

    if (isMobile) {
      // Đóng drawer
      await page.locator('button[aria-label="Đóng menu"]').click();
      await expect(navContainer).not.toBeVisible();
    }
  });

  test('TC-TEACHER-02: Xem danh sách lớp & chi tiết lớp học (/classes)', async ({ page }) => {
    await loginAs(page, 'teacher1@cams.com', 'Teacher@2026!');

    await navigateViaSidebar(page, 'Lớp học', '/classes');
    await expect(page).toHaveURL(/.*\/classes/);
    await page.waitForLoadState('domcontentloaded');

    // Chờ danh sách lớp học hiển thị
    const classLinks = page.locator('a[href^="/classes/"]');
    await expect(classLinks.first()).toBeVisible({ timeout: 15000 });

    // Nhấp vào xem chi tiết lớp học
    await classLinks.first().click();
    await page.waitForURL(/.*\/classes\/[0-9a-fA-F-]+/, { timeout: 15000 });
    await page.waitForLoadState('domcontentloaded');

    // Kiểm tra không có thông báo lỗi hiển thị
    await expect(page.locator('body')).not.toContainText('Đã xảy ra sự cố hiển thị');
  });

  test('TC-TEACHER-03: Lịch học (/schedule)', async ({ page }) => {
    await loginAs(page, 'teacher1@cams.com', 'Teacher@2026!');

    await navigateViaSidebar(page, 'Lịch học', '/schedule');
    await expect(page).toHaveURL(/.*\/schedule/);
    await page.waitForLoadState('domcontentloaded');

    // Trang lịch học hiển thị lịch hoặc thời khóa biểu tuần
    await expect(page.locator('body')).not.toContainText('Đã xảy ra sự cố hiển thị');
  });

  test('TC-TEACHER-04: Kho bài tập cờ (/puzzles) và Quản lý bài tập (/assignments)', async ({ page }) => {
    await loginAs(page, 'teacher1@cams.com', 'Teacher@2026!');

    // 1. Vào Kho bài tập cờ (/puzzles)
    await navigateViaSidebar(page, 'Kho bài tập cờ', '/puzzles');
    await expect(page).toHaveURL(/.*\/puzzles/);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toContainText('Đã xảy ra sự cố hiển thị');

    // 2. Vào Bài tập về nhà (/assignments)
    await navigateViaSidebar(page, 'Bài tập về nhà', '/assignments');
    await expect(page).toHaveURL(/.*\/assignments/);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toContainText('Đã xảy ra sự cố hiển thị');
  });

  test('TC-TEACHER-05: Trang Quét AI bàn cờ (/scanner) mở ổn định & kiểm tra phóng to ảnh', async ({ page }) => {
    await loginAs(page, 'teacher1@cams.com', 'Teacher@2026!');

    await navigateViaSidebar(page, 'Quét AI bàn cờ', '/scanner');
    await expect(page).toHaveURL(/.*\/scanner/);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toContainText('Đã xảy ra sự cố hiển thị');

    // Kiểm tra giao diện quét tài liệu hiển thị tiêu đề và khu vực Scan Jobs
    await expect(page.getByText(/AI Chessboard Scanner|Scan Jobs/i).first()).toBeVisible();

    // Nếu có job scan đã tồn tại, click chọn job để kiểm tra nút phóng to
    const jobButtons = page.locator('div.max-h-\\[calc\\(100vh-280px\\)\\] button');
    if (await jobButtons.count() > 0) {
      await jobButtons.first().click();
      await page.waitForTimeout(1000);

      const zoomButtons = page.locator('button[aria-label="Phóng to ảnh bàn cờ"]');
      if (await zoomButtons.count() > 0) {
        await zoomButtons.first().click();
        const zoomModal = page.locator('div[role="dialog"][aria-label="Phóng to ảnh bàn cờ"]');
        await expect(zoomModal).toBeVisible();
        await expect(zoomModal.getByText(/Ảnh gốc trích xuất từ PDF/i)).toBeVisible();

        // Đóng modal bằng nút đóng
        await zoomModal.locator('button[aria-label="Đóng phóng to ảnh"]').click();
        await expect(zoomModal).not.toBeVisible();
      }
    }
  });

});

