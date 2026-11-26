const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const PORT = 9328;
const MEDIA_DIR = "/data/data/com.termux/files/home/frostyrips-mobile/docs/media";
const ST_DIR = "/data/data/com.termux/files/home/frostyrips-mobile/build/captures/stadium";
const APP_DIR = "/data/data/com.termux/files/home/frostyrips-mobile/build/captures/app";
fs.mkdirSync(MEDIA_DIR, { recursive: true });
fs.mkdirSync(ST_DIR, { recursive: true });
fs.mkdirSync(APP_DIR, { recursive: true });

const sleep = ms => new Promise(r => setTimeout(r, ms));

class CDP {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.method === "Runtime.exceptionThrown") {
        console.log("EX:", msg.params.exceptionDetails.text);
      }
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

async function waitForScreen(cdp, targetId, maxMs = 18000) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const cur = await evalJS(cdp, `document.querySelector('.st-screen.is-active')?.id`);
    if (cur === targetId) return true;
    await sleep(350);
  }
  return false;
}

async function pressKey(cdp, key, code, holdMs = 260) {
  await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key, code });
  await sleep(holdMs);
  await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key, code });
}

(async () => {
  for (const f of fs.readdirSync(ST_DIR)) {
    if (f.startsWith("battle_")) fs.unlinkSync(path.join(ST_DIR, f));
  }

  // Full ANGLE + Mesa Vulkan 1.4 Lavapipe (llvmpipe 128-bit SIMD) — real PBR WebGL2 3D!
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

    // Preserve WebGL drawing buffer for clean frame captures + balanced preset for fast smooth 3D rendering
    await cdp.send("Page.addScriptToEvaluateOnNewDocument", {
      source: `
        const origGetCtx = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, attrs) {
          if (type && type.includes("webgl")) {
            attrs = Object.assign({}, attrs, { preserveDrawingBuffer: true });
          }
          return origGetCtx.call(this, type, attrs);
        };
      `
    });

    // 1. Capture All 42 Mystery Packs Grid cleanly on frostrips.web.app
    console.log("Capturing All 42 Mystery Packs grid...");
    await cdp.send("Page.navigate", { url: "https://frostrips.web.app/" });
    await sleep(4200);
    await evalJS(cdp, `(() => {
      const p = document.getElementById('packGridPills');
      if (p) {
        p.scrollIntoView({ behavior: 'instant', block: 'start' });
        window.scrollBy(0, -110);
      }
    })()`);
    await sleep(900);
    await snap(cdp, path.join(MEDIA_DIR, "03b-packs-catalog-42.png"));
    await snap(cdp, path.join(APP_DIR, "store_catalog.jpg"), "jpeg", 92);

    // =========================================================================
    // 2. LIVE WEBGL2 3D MEGASTADIUM — TITLE, 3D LOBBY, 3D POKEMON GLBs & BATTLES
    // =========================================================================
    console.log("Loading https://frostyrips-stadium.web.app/ on Mesa Vulkan 1.4 Lavapipe...");
    await cdp.send("Page.navigate", { url: "https://frostyrips-stadium.web.app/" });
    await sleep(6500);

    await snap(cdp, path.join(MEDIA_DIR, "05-megastadium-title.png"));
    await snap(cdp, path.join(ST_DIR, "st_00_title.jpg"), "jpeg", 92);

    // Tap to Start -> Server Browser -> Connect -> 3D Squad Lobby!
    await clickSel(cdp, "#btnTapToStart");
    await waitForScreen(cdp, "screenServers", 15000);
    await sleep(1200);
    await clickSel(cdp, "#btnConnectServer");
    await waitForScreen(cdp, "screenLobby", 15000);
    await sleep(6000); // Full 3D Megadome + 3D Squad GLBs + floodlights!

    const lobbyGL = await evalJS(cdp, `(() => {
      const c = document.getElementById('stadiumWebglCanvas');
      const gl = c && (c.getContext('webgl2') || c.getContext('webgl'));
      if (!gl || gl.isContextLost()) return { lost: true };
      const px = new Uint8Array(4);
      gl.readPixels(640, 360, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
      const px2 = new Uint8Array(4);
      gl.readPixels(640, 220, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px2);
      return { lost: false, center: Array.from(px), lower: Array.from(px2) };
    })()`);
    console.log("LOBBY_GL:", JSON.stringify(lobbyGL));

    // Open 27,014 Fighter Locker -> 3D GLBs tab -> pick Charizard for Slot 1!
    await clickSel(cdp, "#btnLobbyOpenLocker");
    await waitForScreen(cdp, "screenDraft", 10000);
    await sleep(2200);
    await clickSel(cdp, '.st-tab[data-roster-src="models3d"]');
    await sleep(2500);
    const picked = await evalJS(cdp, `(() => {
      const cards = Array.from(document.querySelectorAll('#screenDraft button, #screenDraft .st-fighter-card, #screenDraft [data-card-id]'));
      const fav = cards.find(c => /charizard/i.test(c.textContent || ''));
      if (fav) { fav.click(); return fav.textContent.trim().slice(0, 36); }
      return 'none';
    })()`);
    console.log("PICKED_3D_POKEMON:", picked);
    await sleep(4500); // Wait for live 3D Charizard GLB preview render!
    await snap(cdp, path.join(MEDIA_DIR, "05c-megastadium-roster.png"));
    await snap(cdp, path.join(ST_DIR, "st_02_roster.jpg"), "jpeg", 92);

    // Save & Return to 3D Lobby (now showing Charizard on the center 3D pedestal!)
    await clickSel(cdp, "#btnDraftSave");
    const backLobby = await waitForScreen(cdp, "screenLobby", 5000);
    if (!backLobby) {
      await clickSel(cdp, "#btnDraftBack");
      await waitForScreen(cdp, "screenLobby", 8000);
    }
    await sleep(4000);
    await snap(cdp, path.join(MEDIA_DIR, "05b-megastadium-lobby.png"));
    await snap(cdp, path.join(ST_DIR, "st_01_lobby.jpg"), "jpeg", 92);

    // Launch Straight Into Live 3D Battle!
    await clickSel(cdp, "#btnLobbyReadyPlay");
    await waitForScreen(cdp, "screenBattle", 18000);
    await sleep(5500);

    const roamHidden = await evalJS(cdp, `document.getElementById('roamHudOverlay')?.classList.contains('is-hidden')`);
    if (roamHidden) {
      await clickSel(cdp, "#btnToggleRoam");
      await sleep(2000);
    }

    const battleGL = await evalJS(cdp, `(() => {
      const c = document.getElementById('stadiumWebglCanvas');
      const gl = c && (c.getContext('webgl2') || c.getContext('webgl'));
      if (!gl || gl.isContextLost()) return { lost: true };
      const px = new Uint8Array(4);
      gl.readPixels(640, 360, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
      return { lost: false, center: Array.from(px) };
    })()`);
    console.log("BATTLE_GL:", JSON.stringify(battleGL));

    let frameIdx = 0;
    async function capBattleFrame() {
      const fname = `battle_${String(frameIdx).padStart(3, "0")}.jpg`;
      await snap(cdp, path.join(ST_DIR, fname), "jpeg", 90);
      frameIdx++;
    }

    // === PHASE A: Grand Champions Megadome — Close In & 5-Hit Combo ===
    await pressKey(cdp, "w", "KeyW", 800);
    await clickSel(cdp, "#btnActStrike");
    await sleep(420);
    await capBattleFrame();
    await snap(cdp, path.join(MEDIA_DIR, "05d-megastadium-battle-1.png"));

    for (let i = 0; i < 8; i++) {
      if (i % 2 === 0) await clickSel(cdp, "#btnActStrike");
      else await clickSel(cdp, "#btnActKick");
      await sleep(340);
      await capBattleFrame();
    }

    // === PHASE B: Elemental Blast & Dodge ===
    await clickSel(cdp, "#btnActDefend");
    await sleep(320);
    await capBattleFrame();
    for (let i = 0; i < 7; i++) {
      await clickSel(cdp, "#btnActBlast");
      await sleep(360);
      await capBattleFrame();
    }
    await snap(cdp, path.join(MEDIA_DIR, "05e-megastadium-battle-2.png"));

    // === PHASE C: Switch PBR Arena -> Glacier Titan Coliseum + Frostmax + Ultimate ===
    await clickSel(cdp, "#btnCycleTheme");
    await sleep(600);
    const st2 = await evalJS(cdp, `(() => {
      const t = document.querySelectorAll('#stagePickerGrid [data-stage-pick]');
      if (t[1]) { t[1].click(); return t[1].getAttribute('data-stage-pick'); }
      return null;
    })()`);
    console.log("STAGE_2:", st2);
    await sleep(3000);
    await clickSel(cdp, "#btnToggleStanceDrawer");
    await sleep(300);
    await clickSel(cdp, "#btnRoamFrostmax");
    await sleep(500);
    for (let i = 0; i < 9; i++) {
      if (i === 2 || i === 6) await clickSel(cdp, "#btnActUlt");
      else if (i % 2 === 0) await clickSel(cdp, "#btnActStrike");
      else await clickSel(cdp, "#btnActBlast");
      await sleep(360);
      await capBattleFrame();
    }
    await snap(cdp, path.join(MEDIA_DIR, "05f-megastadium-battle-3.png"));

    // === PHASE D: Switch PBR Arena -> Cyber Overwatch + Jump Slam ===
    await clickSel(cdp, "#btnCycleTheme");
    await sleep(600);
    const st3 = await evalJS(cdp, `(() => {
      const t = document.querySelectorAll('#stagePickerGrid [data-stage-pick]');
      if (t[3]) { t[3].click(); return t[3].getAttribute('data-stage-pick'); }
      return null;
    })()`);
    console.log("STAGE_3:", st3);
    await sleep(2800);
    await clickSel(cdp, "#btnActJump");
    await sleep(300);
    for (let i = 0; i < 8; i++) {
      if (i % 3 === 0) await clickSel(cdp, "#btnActKick");
      else if (i % 3 === 1) await clickSel(cdp, "#btnActBlast");
      else await clickSel(cdp, "#btnActStrike");
      await sleep(340);
      await capBattleFrame();
    }

    console.log("STADIUM_3D_CAPTURE_COMPLETE! Frames:", frameIdx);
  } finally {
    chrome.kill("SIGKILL");
  }
})();
