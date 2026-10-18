import { test, expect, loginAs, logout, navigateViaSidebar, allowStatusCodes } from './test-base';

test.describe('Authentication & Profile Management (UAT)', () => {

  test('TC-AUTH-01: Đăng nhập và đăng xuất thành công với các vai trò', async ({ page }) => {
    // 1. Center Admin
    await loginAs(page, 'admin@cams.com', 'Admin@2026!');
    await expect(page).toHaveURL(/.*(\/|$)/);
    await expect(page.locator('body')).toContainText(/Nguyễn Quản Trị|center_admin/i);
    await logout(page);

    // 2. Teacher
    await loginAs(page, 'teacher1@cams.com', 'Teacher@2026!');
    await expect(page).toHaveURL(/.*(\/|$)/);
    await expect(page.locator('body')).toContainText(/Trần Văn Giáo|teacher/i);
    await logout(page);

    // 3. Student
    await loginAs(page, 'student1@cams.com', 'Student@2026!');
    await expect(page).toHaveURL(/.*(\/|$)/);
    await expect(page.locator('body')).toContainText(/Phạm Minh Học|student/i);
    await logout(page);

    // 4. Parent
    await loginAs(page, 'parent1@cams.com', 'Parent@2026!');
    await expect(page).toHaveURL(/.*(\/|$)/);
    await expect(page.locator('body')).toContainText(/Phạm Văn Cha|parent/i);
    await logout(page);
  });

  test('TC-AUTH-02: Cố tình nhập sai mật khẩu hiển thị thông báo lỗi 401', async ({ page }) => {
    // Cho phép mã lỗi 400 hoặc 401 đối với test case kiểm thử mật khẩu sai
    allowStatusCodes(page, [400, 401]);

    await page.goto('/login');
    await page.locator('input[type="email"]').fill('admin@cams.com');
    await page.locator('input[type="password"]').fill('MatKhauSai@999!');
    await page.locator('button[type="submit"]').click();

    // Vẫn ở lại trang /login và xuất hiện thông báo lỗi
    await expect(page).toHaveURL(/.*\/login/);
    const toastError = page.locator('div[role="status"]').or(page.getByText(/Login failed|không chính xác|Invalid credentials/i));
    await expect(toastError.first()).toBeVisible({ timeout: 10000 });
  });

  test('TC-AUTH-03: Kiểm tra checkbox "Nhớ mật khẩu" (Remember me) lưu email và tự điền khi tải lại trang', async ({ page }) => {
    await page.goto('/login');
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    const rememberCheckbox = page.locator('input[name="remember-me"]');

    await expect(rememberCheckbox).toBeVisible();
    await emailInput.fill('teacher1@cams.com');
    await passwordInput.fill('Teacher@2026!');
    await rememberCheckbox.check();
    await expect(rememberCheckbox).toBeChecked();

    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*(\/|$)/);

    // Đăng xuất và quay lại trang login
    await logout(page);
    await page.goto('/login');

    // Email phải được tự động điền từ localStorage và checkbox vẫn được chọn
    await expect(emailInput).toHaveValue('teacher1@cams.com');
    await expect(rememberCheckbox).toBeChecked();
  });

  test('TC-PROFILE-01: Cập nhật Full Name, Số điện thoại khi để trống Username (200 OK)', async ({ page }) => {
    await loginAs(page, 'student1@cams.com', 'Student@2026!');

    // Điều hướng vào trang Profile
    await navigateViaSidebar(page, 'Hồ sơ cá nhân', '/profile');
    await expect(page).toHaveURL(/.*\/profile/);

    // Điền Full Name mới, Số điện thoại mới và để trống Username
    const fullNameInput = page.locator('input[name="full_name"]').or(page.locator('label:has-text("Full Name") + input'));
    const phoneInput = page.locator('input[name="phone"]').or(page.locator('label:has-text("Phone") + input'));
    const usernameInput = page.locator('input[name="username"]').or(page.locator('label:has-text("Username") + input'));

    await fullNameInput.fill('Phạm Minh Học (UAT Verified)');
    await phoneInput.fill('0987654321');
    await usernameInput.fill(''); // ĐỂ TRỐNG USERNAME

    // Lắng nghe API PUT /api/users/me phải trả về 200 OK
    const updatePromise = page.waitForResponse(
      (resp) => resp.url().includes('/users/me') && resp.request().method() === 'PUT' && resp.status() === 200
    );

    // Nhấp nút Save Profile
    await page.locator('button:has-text("Save Profile")').click();
    await updatePromise;

    // Toast thành công xuất hiện
    await expect(page.getByText(/Profile updated successfully/i)).toBeVisible({ timeout: 10000 });
  });

  test('TC-PROFILE-02: Upload avatar gọi đúng endpoint /api/users/me/avatar', async ({ page }) => {
    await loginAs(page, 'student1@cams.com', 'Student@2026!');
    await navigateViaSidebar(page, 'Hồ sơ cá nhân', '/profile');

    // Chuẩn bị buffer ảnh 1x1 PNG giả lập
    const pngBuffer = Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
      'base64'
    );

    // Lắng nghe network call POST /api/users/me/avatar
    const uploadPromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/users/me/avatar') &&
        resp.request().method() === 'POST' &&
        resp.status() === 200,
      { timeout: 15000 }
    );

    // Gán file vào input[type="file"]
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'avatar_test.png',
      mimeType: 'image/png',
      buffer: pngBuffer,
    });
    await fileInput.evaluate((el: HTMLInputElement) => {
      el.dispatchEvent(new Event('change', { bubbles: true }));
    });

    const uploadResponse = await uploadPromise;
    const json = await uploadResponse.json();
    expect(json).toHaveProperty('avatar_url');

    // Xác nhận toast upload thành công
    await expect(page.getByText(/Avatar uploaded successfully/i).first()).toBeVisible({ timeout: 10000 });
  });

});
