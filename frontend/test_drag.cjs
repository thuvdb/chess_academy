const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('dialog', dialog => dialog.accept());

  console.log("Navigating to login...");
  await page.goto('http://localhost:3001/login');
  
  await page.fill('input[type="email"]', 'teacher@cams.vn');
  await page.fill('input[type="password"]', '123456');
  await page.click('button[type="submit"]');

  await page.waitForTimeout(2000);

  console.log("Navigating to practice...");
  await page.goto('http://localhost:3001/practice');

  console.log("Waiting 3s for board to load...");
  await page.waitForTimeout(3000);
  
  await page.screenshot({ path: 'board_debug.png' });
  console.log("Screenshot saved to board_debug.png");

  const html = await page.content();
  fs.writeFileSync('page_dump.html', html);
  console.log("HTML dumped to page_dump.html");

  await browser.close();
})();
