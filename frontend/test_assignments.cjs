const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  const results = [];
  page.on('response', async response => {
    if (response.url().includes('/api/assignments') && response.request().method() === 'GET') {
      try {
        const text = await response.text();
        results.push(text);
      } catch (e) {}
    }
  });

  await page.goto('http://localhost:3000/login');
  await page.fill('input[type="email"]', 'teacher@cams.vn'); 
  await page.fill('input[type="password"]', '123456');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);

  await page.goto('http://localhost:3000/assignments');
  await page.waitForTimeout(3000); // Wait for the response

  fs.writeFileSync('assignments_network.json', JSON.stringify(results, null, 2));
  await browser.close();
})();
