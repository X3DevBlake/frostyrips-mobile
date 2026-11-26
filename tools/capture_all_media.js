const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const PORT = 9325;
const MEDIA_DIR = "/data/data/com.termux/files/home/frostyrips-mobile/docs/media";
const FRAMES_DIR = "/data/data/com.termux/files/home/frostyrips-mobile/build/captures";
fs.mkdirSync(MEDIA_DIR, { recursive: true });
fs.mkdirSync(path.join(FRAMES_DIR, "stadium"), { recursive: true });
fs.mkdirSync(path.join(FRAMES_DIR, "presale"), { recursive: true });
fs.mkdirSync(path.join(FRAMES_DIR, "app"), { recursive: true });

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

async function pressKey(cdp, key, code, holdMs = 120) {
  await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key, code });
  await sleep(holdMs);
  await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key, code });
}

(async () => {
  const chrome = spawn("chromium-browser", [
    "--headless=new", "--no-sandbox", "--disable-gpu-sandbox",
    "--enable-unsafe-swiftshader", "--enable-webgl",
    "--ignore-gpu-blocklist", "--mute-audio",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    `--remote-debugging-port=${PORT}`,
    "--window-size=1280,720", "about:blank"
  ], { stdio: "ignore" });

  try {
    const cdp = await connect();
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");

    // =========================================================================
    // PART 1: UPDATED AD LANDING PAGE (Desktop Hero, Ecosystem, Mobile)
    // =========================================================================
    console.log("[1/4] Capturing Ad Landing Page...");
    await cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await cdp.send("Page.navigate", { url: "https://frostrips.web.app/ad/landing/app" });
    await sleep(3200);
    await snap(cdp, path.join(MEDIA_DIR, "01-app-landing-desktop.png"));
    await snap(cdp, path.join(FRAMES_DIR, "app", "ad_hero.jpg"), "jpeg", 92);

    const adHeight = await evalJS(cdp, `document.documentElement.scrollHeight`);
    // Scroll through ad landing page smoothly for app video + capture ecosystem shot
    await evalJS(cdp, `document.getElementById('ecosystem')?.scrollIntoView({ behavior: 'instant', block: 'center' })`);
    await sleep(600);
    await snap(cdp, path.join(MEDIA_DIR, "01b-app-landing-ecosystem.png"));
    await snap(cdp, path.join(FRAMES_DIR, "app", "ad_ecosystem.jpg"), "jpeg", 92);

    // Full tall scroll capture of ad page for smooth video panning
    const adTall = await cdp.send("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: true,
      clip: { x: 0, y: 0, width: 1280, height: Math.min(4200, Math.max(1400, adHeight || 3200)), scale: 1 }
    });
    fs.writeFileSync(path.join(FRAMES_DIR, "app", "ad_full.png"), Buffer.from(adTall.data, "base64"));

    // Mobile view of Ad Landing Page (Hero + Ecosystem)
    await cdp.send("Emulation.setDeviceMetricsOverride", { width: 412, height: 892, deviceScaleFactor: 2, mobile: true });
    await cdp.send("Page.navigate", { url: "https://frostrips.web.app/ad/landing/app" });
    await sleep(2600);
    await snap(cdp, path.join(MEDIA_DIR, "02-app-landing-mobile.png"));

    // =========================================================================
    // PART 2: REGULAR WEBSITE / FOIL PACK STORE + PACK RIP + FIXED MOBILE APP
    // =========================================================================
    console.log("[2/4] Capturing Pack Store, Pack Rip & Fixed Mobile App...");
    await cdp.send("Emulation.setDeviceMetricsOverride", { width: 412, height: 892, deviceScaleFactor: 2, mobile: true });
    await cdp.send("Page.navigate", { url: "https://frostrips.web.app/?app=android&v=1.1.0" });
    await sleep(4500);
    await snap(cdp, path.join(MEDIA_DIR, "02b-mobile-app-live.png"));

    // Desktop Pack Store (1280x720)
    await cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await cdp.send("Page.navigate", { url: "https://frostrips.web.app/" });
    await sleep(4500);
    await snap(cdp, path.join(MEDIA_DIR, "03-packs-store.png"));
    await snap(cdp, path.join(FRAMES_DIR, "app", "store_hero.jpg"), "jpeg", 92);

    // Cycle to a couple iconic packs & capture All 42 catalog
    await clickSel(cdp, "#cfNext");
    await sleep(800);
    await clickSel(cdp, "#cfNext");
    await sleep(800);
    await snap(cdp, path.join(FRAMES_DIR, "app", "store_pack2.jpg"), "jpeg", 92);

    // Click "All 42" category & scroll to All Packs grid
    await clickSel(cdp, '.cat-tab-btn[data-cat="all"]');
    await sleep(1000);
    await evalJS(cdp, `window.scrollTo(0, 520)`);
    await sleep(800);
    await snap(cdp, path.join(MEDIA_DIR, "03b-packs-catalog-42.png"));
    await snap(cdp, path.join(FRAMES_DIR, "app", "store_catalog.jpg"), "jpeg", 92);

    // Trigger an actual Instant Pack Rip to show real 5-card graded pull reveal!
    await evalJS(cdp, `window.scrollTo(0, 0)`);
    await sleep(500);
    await clickSel(cdp, "#btnRipModeToggle");
    await sleep(300);
    await clickSel(cdp, '.rm-option[data-rip-mode="instant"]');
    await sleep(300);
    const ripped = await clickSel(cdp, "#btnPayRip");
    console.log("PACK_RIP_CLICKED:", ripped);
    await sleep(2200);
    await snap(cdp, path.join(MEDIA_DIR, "03c-pack-pull-reveal.png"));
    await snap(cdp, path.join(FRAMES_DIR, "app", "store_pull.jpg"), "jpeg", 92);

    // =========================================================================
    // PART 3: $FROSTY TOKEN PRESALE (Hero, Buy Widget, Tokenomics, Roadmap + Full Tall Scroll)
    // =========================================================================
    console.log("[3/4] Capturing $FROSTY Presale Portal...");
    await cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await cdp.send("Page.navigate", { url: "https://frostyrips-presale.web.app/" });
    await sleep(4500);
    await snap(cdp, path.join(MEDIA_DIR, "04-presale-portal.png"));
    await snap(cdp, path.join(FRAMES_DIR, "presale", "presale_01_hero.jpg"), "jpeg", 92);

    const preH = await evalJS(cdp, `document.documentElement.scrollHeight`);
    console.log("PRESALE_HEIGHT:", preH);
    const preTall = await cdp.send("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: true,
      clip: { x: 0, y: 0, width: 1280, height: Math.min(5400, Math.max(1800, preH || 3600)), scale: 1 }
    });
    fs.writeFileSync(path.join(FRAMES_DIR, "presale", "presale_full.png"), Buffer.from(preTall.data, "base64"));

    // Scroll to 35% (Utility / 50% Pack Burn / Multi-chain)
    await evalJS(cdp, `window.scrollTo(0, Math.round(document.documentElement.scrollHeight * 0.30))`);
    await sleep(800);
    await snap(cdp, path.join(MEDIA_DIR, "04b-presale-tokenomics.png"));
    await snap(cdp, path.join(FRAMES_DIR, "presale", "presale_02_tokenomics.jpg"), "jpeg", 92);

    // Scroll to 65% (Roadmap / Utility / FAQ)
    await evalJS(cdp, `window.scrollTo(0, Math.round(document.documentElement.scrollHeight * 0.64))`);
    await sleep(800);
    await snap(cdp, path.join(MEDIA_DIR, "04c-presale-roadmap.png"));
    await snap(cdp, path.join(FRAMES_DIR, "presale", "presale_03_roadmap.jpg"), "jpeg", 92);

    // =========================================================================
    // PART 4: LIVE 3D MEGASTADIUM — TITLE, 3D LOBBY, LOCKER & REAL 3D BATTLE!
    // =========================================================================
    console.log("[4/4] Capturing Live 3D Megastadium & Real 3D Combat Frames...");
    await cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await cdp.send("Page.navigate", { url: "https://frostyrips-stadium.web.app/" });
    await sleep(5500);
    await snap(cdp, path.join(MEDIA_DIR, "05-megastadium-title.png"));
    await snap(cdp, path.join(FRAMES_DIR, "stadium", "st_00_title.jpg"), "jpeg", 92);

    // Click TAP TO START -> wait for loading -> Server Browser -> Join Server -> 3D Lobby!
    await clickSel(cdp, "#btnTapToStart");
    await sleep(4500);
    const activeAfterTap = await evalJS(cdp, `document.querySelector('.st-screen.is-active')?.id`);
    console.log("STADIUM_AFTER_TAP:", activeAfterTap);
    if (activeAfterTap === "screenServers" || (await evalJS(cdp, `!!document.querySelector('#btnConnectServer')`))) {
      await clickSel(cdp, "#btnConnectServer");
      await sleep(4000);
    }
    const activeLobby = await evalJS(cdp, `document.querySelector('.st-screen.is-active')?.id`);
    console.log("STADIUM_LOBBY_STATE:", activeLobby);
    await snap(cdp, path.join(MEDIA_DIR, "05b-megastadium-lobby.png"));
    await snap(cdp, path.join(FRAMES_DIR, "stadium", "st_01_lobby.jpg"), "jpeg", 92);

    // Open 27,014 Fighter Locker briefly to show Pokémon 3D GLB + FrostyRips roster
    await clickSel(cdp, "#btnLobbyOpenLocker");
    await sleep(2200);
    await clickSel(cdp, '.st-tab[data-roster-src="models3d"]');
    await sleep(1600);
    await snap(cdp, path.join(MEDIA_DIR, "05c-megastadium-roster.png"));
    await snap(cdp, path.join(FRAMES_DIR, "stadium", "st_02_roster.jpg"), "jpeg", 92);

    // Return to Lobby & click READY / PLAY to enter Live 3D Battle!
    await clickSel(cdp, "#btnDraftBack");
    await sleep(1200);
    await clickSel(cdp, "#btnLobbyReadyPlay");
    await sleep(4500);

    const activeBattle = await evalJS(cdp, `document.querySelector('.st-screen.is-active')?.id`);
    console.log("STADIUM_BATTLE_STATE:", activeBattle);

    // Ensure Real-Time 3D Roam Combat mode is active
    const roamHidden = await evalJS(cdp, `document.getElementById('roamHudOverlay')?.classList.contains('is-hidden')`);
    if (roamHidden) {
      await clickSel(cdp, "#btnToggleRoam");
      await sleep(1500);
    }

    // Capture a live sequence of 36 real 3D combat frames while triggering movement, combos, blasts, kicks, ultimate & stage swaps!
    let frameIdx = 0;
    async function capBattleFrame() {
      const fname = `battle_${String(frameIdx).padStart(3, "0")}.jpg`;
      await snap(cdp, path.join(FRAMES_DIR, "stadium", fname), "jpeg", 88);
      frameIdx++;
    }

    // Hero live battle screenshot #1 (opening clash)
    await pressKey(cdp, "w", "KeyW", 300);
    await clickSel(cdp, "#btnActStrike");
    await sleep(250);
    await capBattleFrame();
    await snap(cdp, path.join(MEDIA_DIR, "05d-megastadium-battle-1.png"));

    // 5-hit combo burst
    for (let i = 0; i < 8; i++) {
      if (i % 2 === 0) await clickSel(cdp, "#btnActStrike");
      else await clickSel(cdp, "#btnActKick");
      await sleep(220);
      await capBattleFrame();
    }

    // Elemental blast & dash sequence
    await clickSel(cdp, "#btnActDefend");
    await sleep(180);
    await capBattleFrame();
    for (let i = 0; i < 7; i++) {
      await clickSel(cdp, "#btnActBlast");
      await sleep(240);
      await capBattleFrame();
    }
    await snap(cdp, path.join(MEDIA_DIR, "05e-megastadium-battle-2.png"));

    // Switch stage map to show another PBR 3D arena + Frostmax / Ultimate FX!
    await clickSel(cdp, "#btnCycleTheme");
    await sleep(900);
    await clickSel(cdp, "#btnToggleStanceDrawer");
    await sleep(200);
    await clickSel(cdp, "#btnRoamFrostmax");
    await sleep(300);
    for (let i = 0; i < 8; i++) {
      if (i === 2 || i === 5) await clickSel(cdp, "#btnActUlt");
      else if (i % 2 === 0) await clickSel(cdp, "#btnActStrike");
      else await clickSel(cdp, "#btnActBlast");
      await sleep(250);
      await capBattleFrame();
    }
    await snap(cdp, path.join(MEDIA_DIR, "05f-megastadium-battle-3.png"));

    // One more PBR stage + aerial jump/kick slam sequence
    await clickSel(cdp, "#btnCycleTheme");
    await sleep(800);
    await clickSel(cdp, "#btnActJump");
    await sleep(180);
    for (let i = 0; i < 8; i++) {
      if (i % 3 === 0) await clickSel(cdp, "#btnActKick");
      else if (i % 3 === 1) await clickSel(cdp, "#btnActStrike");
      else await clickSel(cdp, "#btnActBlast");
      await sleep(220);
      await capBattleFrame();
    }

    console.log("ALL_CAPTURES_DONE! Battle frames:", frameIdx);
  } finally {
    chrome.kill("SIGKILL");
  }
})();
