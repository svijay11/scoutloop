import puppeteer from "puppeteer-core";

const browser = await puppeteer.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-gpu"],
});
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900 });
page.on("pageerror", (err) => console.log("PAGEERROR", err.message));

await page.goto("http://127.0.0.1:8787/", { waitUntil: "networkidle0" });
await page.click(".df-hero-cta .df-btn-green");
await page.waitForSelector(".dash");
await page.click("a.wordmark");
await page.waitForSelector(".df");
const back = await page.evaluate(() => ({
  path: location.pathname,
  landing: !!document.querySelector(".df"),
  title: document.querySelector(".df-hero-title")?.textContent,
}));
console.log("BACK_TO_LANDING", JSON.stringify(back));
await page.click(".df-nav-cta");
await page.waitForSelector(".dash");
console.log("SECOND_DASH", await page.evaluate(() => location.pathname));
await browser.close();
console.log("OK");
