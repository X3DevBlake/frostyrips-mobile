const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const PORT = 9321;
const OUT = "/data/data/com.termux/files/home/frostyrips-mobile/build/verify";
fs.mkdirSync(OUT, { recursive: true });

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

class CDP {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message));
        else resolve(msg.result);
      }
    };
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
}

async function connect() {
  for (let i = 0; i < 40; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const list = await res.json();
      const page = list.find(t => t.type === "page");
      if (page && page.webSocketDebuggerUrl) {
        const ws = new WebSocket(page.webSocketDebuggerUrl);
        await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
        return new CDP(ws);
      }
    } catch (_) {}
    await sleep(250);
  }
  throw new Error("CDP connect timeout");
}

async function snap(cdp, file, full = false) {
  const r = await cdp.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: full });
  fs.writeFileSync(path.join(OUT, file), Buffer.from(r.data, "base64"));
}

async function evalJS(cdp, expr) {
  const r = await cdp.send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  return r.result ? r.result.value : null;
}

(async () => {
  const chrome = spawn("chromium-browser", [
    "--headless=new", "--no-sandbox", "--disable-gpu-sandbox",
    "--use-gl=angle", "--use-angle=swiftshader", "--enable-webgl",
    "--ignore-gpu-blocklist", "--mute-audio",
    `--remote-debugging-port=${PORT}`,
    "--window-size=412,915", "about:blank"
  ], { stdio: "ignore" });

  try {
    const cdp = await connect();
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");

    // 1. Verify fixed mobile app (412x915)
    await cdp.send("Emulation.setDeviceMetricsOverride", { width: 412, height: 915, deviceScaleFactor: 2, mobile: true });
    await cdp.send("Page.navigate", { url: "https://frostrips.web.app/?app=android&v=1.1.0" });
    await sleep(5000);
    const mobileMetrics = await evalJS(cdp, `(() => {
      const tb = document.querySelector('.topbar');
      const rip = document.querySelector('#paySplitGroup');
      const dock = document.querySelector('#nxMobileDock');
      const wheel = document.querySelector('#floatingWheelBtn');
      const meta = document.querySelector('.pack-meta-grid');
      const rect = el => el ? { x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y), r: Math.round(el.getBoundingClientRect().right), b: Math.round(el.getBoundingClientRect().bottom), w: Math.round(el.getBoundingClientRect().width), h: Math.round(el.getBoundingClientRect().height) } : null;
      return {
        innerW: window.innerWidth,
        docScrollW: document.documentElement.scrollWidth,
        bodyScrollW: document.body.scrollWidth,
        topbar: rect(tb),
        topbarScrollW: tb ? tb.scrollWidth : 0,
        meta: rect(meta),
        ripBtn: rect(rip),
        dock: rect(dock),
        wheel: rect(wheel)
      };
    })()`);
    console.log("MOBILE_FIXED:", JSON.stringify(mobileMetrics));
    await snap(cdp, "mobile_app_fixed.png");

    // 2. Verify updated Ad Landing Page Desktop (1440x900)
    await cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await cdp.send("Page.navigate", { url: "https://frostrips.web.app/ad/landing/app" });
    await sleep(3500);
    await snap(cdp, "ad_desktop_hero.png");
    await evalJS(cdp, `document.getElementById('ecosystem')?.scrollIntoView({ behavior: 'instant', block: 'center' })`);
    await sleep(600);
    await snap(cdp, "ad_desktop_ecosystem.png");

    // 3. Verify updated Ad Landing Page Mobile (430x932)
    await cdp.send("Emulation.setDeviceMetricsOverride", { width: 430, height: 932, deviceScaleFactor: 2, mobile: true });
    await cdp.send("Page.navigate", { url: "https://frostrips.web.app/ad/landing/app" });
    await sleep(3000);
    await snap(cdp, "ad_mobile_hero.png");
    await evalJS(cdp, `document.getElementById('ecosystem')?.scrollIntoView({ behavior: 'instant', block: 'start' })`);
    await sleep(600);
    await snap(cdp, "ad_mobile_ecosystem.png");
    console.log("VERIFY_DONE");
  } finally {
    chrome.kill("SIGKILL");
  }
})();
