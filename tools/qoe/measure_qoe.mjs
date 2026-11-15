// Автоматизований прогін кроку 8 ЛР2: ті самі дії, що вручну в DevTools.
// Для кожного прогону: нова сторінка, вимкнений кеш (Disable cache), обмеження мережі
// профілем П1–П3 (Network.emulateNetworkConditions — механізм вкладки Network → Throttling),
// натискання «Старт», очікування кінця відтворення, збирання рядка QoE з player.html.
//
// Запуск (сервер уже працює: cd stream && python -m http.server 8000):
//   cd tools/qoe && npm install && node measure_qoe.mjs [CHROME_PATH]
import { appendFileSync, existsSync, writeFileSync } from "node:fs";
import puppeteer from "puppeteer-core";

const CHROME = process.argv[2] || process.env.CHROME_PATH ||
  "C:/Program Files/Google/Chrome/Application/chrome.exe";
const BASE = "http://localhost:8000/player.html";
const kbps = value => (value * 1000) / 8;           // кбіт/с → байт/с

// Профілі табл. 2 методички: Download, Upload (кбіт/с), Latency (мс)
const PROFILES = {
  "П1": { down: 10000, up: 2000, latency: 20 },
  "П2": { down: 1600, up: 750, latency: 150 },
  "П3": { down: 500, up: 500, latency: 400 },
};

// Обов'язкові прогони (results/qoe.csv) і додаткові порівняння (results/qoe_extra.csv).
// tag дозволяє повторити лише одну групу: RUN_ONLY=low node measure_qoe.mjs (рядки дописуються).
const RUNS = [
  ...["П1", "П2", "П3"].flatMap(p => [1, 2].map(() => ({ file: "qoe", tag: "base", profile: p, query: "" }))),
  ...["П2", "П3"].flatMap(p => [1, 2].map(() => ({ file: "extra", tag: "auto", profile: p, label: `${p} hls start=auto`, query: "&start=auto" }))),
  ...["П1", "П2", "П3"].map(p => ({ file: "extra", tag: "dash", profile: p, label: `${p} dash`, query: "&src=dash/manifest.mpd" })),
  ...["П1", "П2", "П3", "П3"].map(p => ({ file: "extra", tag: "low", profile: p, label: `${p} hls start=low`, query: "&start=low" })),
];
const ONLY = process.env.RUN_ONLY;

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: true,
  args: ["--autoplay-policy=no-user-gesture-required", "--no-first-run"],
});
const results = { qoe: [], extra: [] };
for (const run of ONLY ? RUNS.filter(r => r.tag === ONLY) : RUNS) {
  const page = await browser.newPage();
  const cdp = await page.createCDPSession();
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  await page.goto(`${BASE}?profile=${encodeURIComponent(run.profile)}${run.query}`, { waitUntil: "load" });
  const p = PROFILES[run.profile];
  await cdp.send("Network.emulateNetworkConditions", {
    offline: false, latency: p.latency,
    downloadThroughput: kbps(p.down), uploadThroughput: kbps(p.up),
  });
  await page.click("#start");
  await page.waitForFunction(() => window.qoe, { timeout: 300000, polling: 500 });
  const qoe = await page.evaluate(() => window.qoe);
  const row = run.label ? qoe.row.replace(/^[^,]*/, run.label) : qoe.row;
  results[run.file].push(row);
  console.log(row, JSON.stringify(qoe.timeline));
  await page.close();
}
await browser.close();

const header = "profile,startup_s,switches,stalls,stall_s,avg_kbps\n";
for (const [name, rows] of Object.entries(results)) {
  if (!rows.length) continue;
  const path = `../../results/${name === "qoe" ? "qoe" : "qoe_extra"}.csv`;
  if (ONLY && existsSync(path)) appendFileSync(path, rows.join("\n") + "\n", "utf8");
  else writeFileSync(path, header + rows.join("\n") + "\n", "utf8");
  console.log(`Записано ${path.slice(6)}`);
}
