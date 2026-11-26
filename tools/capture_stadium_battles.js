const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const PORT = 9338;
const MEDIA_DIR = "/data/data/com.termux/files/home/frostyrips-mobile/docs/media";
const ST_DIR = "/data/data/com.termux/files/home/frostyrips-mobile/build/captures/stadium";
fs.mkdirSync(MEDIA_DIR, { recursive: true });
fs.mkdirSync(ST_DIR, { recursive: true });

const sleep = ms => new Promise(r => setTimeout(r, ms));

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
  for (let i = 0; i < 45; i++) {
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

async function snap(cdp, outPath, format = "png", quality = 90) {
  const params = { format };
  if (format === "jpeg") params.quality = quality;
  const r = await cdp.send("Page.captureScreenshot", params);
  fs.writeFileSync(outPath, Buffer.from(r.data, "base64"));
}

async function evalJS(cdp, expr) {
  const r = await cdp.send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  return r.result ? r.result.value : null;
}

async function clickSel(cdp, sel) {
  return await evalJS(cdp, `(() => {
    const el = document.querySelector(${JSON.stringify(sel)});
    if (!el) return false;
    el.click();
    return true;
  })()`);
}

async function waitForScreen(cdp, targetId, maxMs = 20000) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const cur = await evalJS(cdp, `document.querySelector('.st-screen.is-active')?.id`);
    if (cur === targetId) return true;
    await sleep(400);
  }
  return false;
}

async function pressKey(cdp, key, code, holdMs = 350) {
  await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key, code });
  await sleep(holdMs);
  await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key, code });
}

(async () => {
  for (const f of fs.readdirSync(ST_DIR)) {
    if (f.startsWith("battle_")) fs.unlinkSync(path.join(ST_DIR, f));
  }

  const chrome = spawn("chromium-browser", [
    "--headless=new", "--no-sandbox", "--disable-gpu-sandbox",
    "--use-gl=angle", "--use-angle=vulkan", "--enable-features=Vulkan",
    "--ozone-platform=headless", "--enable-webgl",
    "--ignore-gpu-blocklist", "--mute-audio",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    `--remote-debugging-port=${PORT}`,
    "--window-size=1280,720", "about:blank"
  ], {
    stdio: "ignore",
    env: {
      ...process.env,
      VK_ICD_FILENAMES: "/data/data/com.termux/files/usr/share/vulkan/icd.d/lvp_icd.aarch64.json",
    },
  });

  try {
    const cdp = await connect();
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });

    // Fast preset keeps full PBR stadium, skyboxes, spotlights & 3D GLBs while avoiding 2048px CPU shadow stalls!
    // Also throttle rAF slightly (~12fps) so Lavapipe never saturates compositor vsync during CDP screenshots!
    await cdp.send("Page.addScriptToEvaluateOnNewDocument", {
      source: `
        localStorage.setItem("frosty_stadium_gfx_v27", "fast");
        const origGetCtx = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, attrs) {
          if (type && type.includes("webgl")) {
            attrs = Object.assign({}, attrs, { preserveDrawingBuffer: true, antialias: false });
          }
          return origGetCtx.call(this, type, attrs);
        };
        const origRAF = window.requestAnimationFrame.bind(window);
        window.requestAnimationFrame = function(cb) {
          return setTimeout(() => origRAF(cb), 65);
        };
      `
    });

    console.log("[1] Loading 3D Megastadium...");
    await cdp.send("Page.navigate", { url: "https://frostyrips-stadium.web.app/" });
    await sleep(5000);

    await clickSel(cdp, "#btnTapToStart");
    await waitForScreen(cdp, "screenServers", 15000);
    await sleep(600);
    await clickSel(cdp, "#btnConnectServer");
    await waitForScreen(cdp, "screenLobby", 15000);
    await sleep(4000);
    console.log("[2] Capturing Live 3D Squad Lobby...");
    await snap(cdp, path.join(MEDIA_DIR, "05b-megastadium-lobby.png"));
    await snap(cdp, path.join(ST_DIR, "st_01_lobby.jpg"), "jpeg", 92);

    // Quick-update st_02_roster.jpg from the crisp 05c-megastadium-roster.png we already captured!
    console.log("[3] Launching Live 3D Battle Arena...");
    await clickSel(cdp, "#btnLobbyReadyPlay");
    await waitForScreen(cdp, "screenBattle", 18000);
    await sleep(4500);

    const roamHidden = await evalJS(cdp, `document.getElementById('roamHudOverlay')?.classList.contains('is-hidden')`);
    if (roamHidden) {
      await clickSel(cdp, "#btnToggleRoam");
      await sleep(1200);
    }

    let frameIdx = 0;
    async function capBattleFrame() {
      const fname = `battle_${String(frameIdx).padStart(3, "0")}.jpg`;
      await snap(cdp, path.join(ST_DIR, fname), "jpeg", 90);
      frameIdx++;
    }

    // === PHASE A: Grand Champions Megadome — Close In & Melee Combos ===
    console.log("[4] Phase A: Grand Champions Megadome combat...");
    await pressKey(cdp, "w", "KeyW", 750);
    await clickSel(cdp, "#btnActStrike");
    await sleep(320);
    await capBattleFrame();
    await snap(cdp, path.join(MEDIA_DIR, "05d-megastadium-battle-1.png"));

    for (let i = 0; i < 5; i++) {
      await clickSel(cdp, i % 2 === 0 ? "#btnActStrike" : "#btnActKick");
      await sleep(280);
      await capBattleFrame();
    }

    // === PHASE B: Elemental Blast & Dodge ===
    console.log("[5] Phase B: Elemental Blasts...");
    await clickSel(cdp, "#btnActDefend");
    await sleep(250);
    await capBattleFrame();
    for (let i = 0; i < 4; i++) {
      await clickSel(cdp, "#btnActBlast");
      await sleep(300);
      await capBattleFrame();
    }
    await snap(cdp, path.join(MEDIA_DIR, "05e-megastadium-battle-2.png"));

    // === PHASE C: Switch PBR Arena -> Glacier Titan Coliseum + Frostmax + Ultimate ===
    console.log("[6] Phase C: Glacier Titan Coliseum + Frostmax + Ultimate...");
    await clickSel(cdp, "#btnCycleTheme");
    await sleep(450);
    await evalJS(cdp, `(() => { const t = document.querySelectorAll('#stagePickerGrid [data-stage-pick]'); if (t[1]) t[1].click(); })()`);
    await sleep(2200);
    await clickSel(cdp, "#btnToggleStanceDrawer");
    await sleep(200);
    await clickSel(cdp, "#btnRoamFrostmax");
    await sleep(400);
    for (let i = 0; i < 5; i++) {
      await clickSel(cdp, i === 2 ? "#btnActUlt" : (i % 2 === 0 ? "#btnActStrike" : "#btnActBlast"));
      await sleep(300);
      await capBattleFrame();
    }
    await snap(cdp, path.join(MEDIA_DIR, "05f-megastadium-battle-3.png"));

    // === PHASE D: Switch PBR Arena -> Cyber Overwatch + Jump Slam ===
    console.log("[7] Phase D: Cyber Overwatch + Jump Slam...");
    await clickSel(cdp, "#btnCycleTheme");
    await sleep(450);
    await evalJS(cdp, `(() => { const t = document.querySelectorAll('#stagePickerGrid [data-stage-pick]'); if (t[3]) t[3].click(); })()`);
    await sleep(2000);
    await clickSel(cdp, "#btnActJump");
    await sleep(250);
    for (let i = 0; i < 5; i++) {
      await clickSel(cdp, i % 2 === 0 ? "#btnActKick" : "#btnActBlast");
      await sleep(280);
      await capBattleFrame();
    }

    console.log("BATTLE_CAPTURE_DONE! Frames:", frameIdx);
  } finally {
    chrome.kill("SIGKILL");
  }
})();
