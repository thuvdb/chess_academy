const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  let errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push('CONSOLE ERROR: ' + msg.text());
  });
  page.on('pageerror', err => errors.push('PAGE ERROR: ' + err.message));

  await page.goto('http://localhost:3000/login');
  await page.fill('input[type="email"]', 'admin@cams.vn');
  await page.fill('input[type="password"]', 'password');
  await page.click('button[type="submit"]');

  await page.waitForTimeout(2000);

  await page.goto('http://localhost:3000/classes');
  await page.waitForTimeout(2000);

  await page.goto('http://localhost:3000/assignments');
  await page.waitForTimeout(2000);

  fs.writeFileSync('browser_errors.txt', errors.join('\n') || 'No errors');
  await browser.close();
})();
