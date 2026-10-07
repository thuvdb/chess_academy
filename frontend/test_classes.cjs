const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  console.log("Starting browser...");
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  const logs = [];
  page.on('console', msg => {
    console.log('CONSOLE LOG:', msg.text());
    logs.push(`CONSOLE: ${msg.text()}`);
  });
  page.on('pageerror', err => {
    console.log('PAGE ERROR:', err.message);
    logs.push(`ERROR: ${err.message}`);
  });
  
  console.log("Navigating to /classes...");
  await page.goto('http://localhost:3000/classes', { waitUntil: 'networkidle' });
  
  console.log("Taking screenshot...");
  await page.screenshot({ path: 'classes_screenshot.png' });
  
  fs.writeFileSync('browser_logs.txt', logs.join('\n'));
  
  console.log("Closing browser.");
  await browser.close();
})();
