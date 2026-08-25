import puppeteer from "puppeteer-core";

const browser = await puppeteer.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-gpu"],
});
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900 });
page.on("pageerror", (err) => {
  console.log("PAGEERROR", err.message);
  console.log(err.stack);
});
page.on("console", (msg) => {
  if (msg.type() === "error") console.log("CONSOLE", msg.text());
});

async function dump(label) {
  const info = await page.evaluate(() => ({
    path: location.pathname,
    scrollY: window.scrollY,
    hasDash: !!document.querySelector(".dash"),
    hasLanding: !!document.querySelector(".df"),
    landingClass: document.body.classList.contains("is-landing"),
    rootText: (document.getElementById("root")?.innerText || "").slice(0, 200),
    rootHTML: (document.getElementById("root")?.innerHTML || "").slice(0, 180),
  }));
  console.log(label, JSON.stringify(info));
}

await page.goto("http://127.0.0.1:8787/", { waitUntil: "networkidle0", timeout: 20000 });
await page.waitForSelector(".df-hero-cta .df-btn-green");
await dump("AT_TOP");

console.log("--- click hero CTA at top ---");
await page.click(".df-hero-cta .df-btn-green");
await new Promise((r) => setTimeout(r, 1500));
await dump("AFTER_HERO_CLICK");
await page.screenshot({
  path: "/Users/sidd/Documents/scoutloop/.tmp-verify/after-hero.png",
});

await page.goto("http://127.0.0.1:8787/", { waitUntil: "networkidle0", timeout: 20000 });
await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
await new Promise((r) => setTimeout(r, 400));
await dump("SCROLLED");
console.log("--- click nav CTA after scroll ---");
await page.click(".df-nav-cta");
await new Promise((r) => setTimeout(r, 1500));
await dump("AFTER_NAV_CLICK");
await page.screenshot({
  path: "/Users/sidd/Documents/scoutloop/.tmp-verify/after-nav.png",
});

await page.goto("http://127.0.0.1:8787/dashboard", { waitUntil: "networkidle0" });
await dump("DIRECT_DASH");
await page.screenshot({
  path: "/Users/sidd/Documents/scoutloop/.tmp-verify/direct-dash.png",
});

await browser.close();
