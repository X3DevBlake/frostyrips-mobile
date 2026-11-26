#!/usr/bin/env python3
"""
Renders 3 dedicated 1280x720 30fps H.264 + AAC videos and 3 compact (<4.2MB)
auto-playing GitHub README preview GIFs from live Chromium captures:
  1. frostyrips-app-demo.mp4       + docs/media/frostyrips-app-demo.gif
  2. frostyrips-presale-video.mp4  + docs/media/frostyrips-presale-video.gif
  3. frostyrips-stadium-battle.mp4 + docs/media/frostyrips-stadium-battle.gif
"""
import glob
import math
import os
import subprocess
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HOME = "/data/data/com.termux/files/home"
MOBILE = f"{HOME}/frostyrips-mobile"
MEDIA_DIR = f"{MOBILE}/docs/media"
CAP_DIR = f"{MOBILE}/build/captures"
VID_DIR = f"{MOBILE}/build/videos"
APP_ASSETS = f"{HOME}/frostrips/public/assets/app-landing"
AUDIO_SRC = f"{HOME}/frostrips/public/assets/sfx/blizzard_loop.mp3"

FONT_BOLD = "/system/fonts/DroidSans-Bold.ttf"
FONT_REG = "/system/fonts/Roboto-Regular.ttf"

W, H = 1280, 720
FPS = 30


def font(sz: int, bold: bool = True):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, sz)
    except Exception:
        return ImageFont.load_default()


def ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def fit_cover(im: Image.Image, tw: int, th: int, zoom: float = 1.0, pan_y: float = 0.5) -> Image.Image:
    sw, sh = im.size
    scale = max(tw / sw, th / sh) * zoom
    nw, nh = max(tw, int(sw * scale)), max(th, int(sh * scale))
    r = im.resize((nw, nh), Image.Resampling.LANCZOS)
    x0 = (nw - tw) // 2
    y0 = int((nh - th) * max(0.0, min(1.0, pan_y)))
    return r.crop((x0, y0, x0 + tw, y0 + th))


def draw_lower_third(
    frame: Image.Image,
    tag: str,
    title: str,
    url: str,
    accent=(0, 255, 247),
    chip_bg=(255, 229, 0),
    chip_fg=(6, 14, 26),
):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(H - 160, H):
        a = int(215 * ((y - (H - 160)) / 160.0))
        d.line([(0, y), (W, y)], fill=(4, 9, 20, a))
    d.rounded_rectangle(
        [36, H - 116, W - 36, H - 24],
        radius=18,
        fill=(7, 16, 36, 226),
        outline=(accent[0], accent[1], accent[2], 210),
        width=2,
    )
    f_tag = font(14, True)
    tb = d.textbbox((0, 0), tag, font=f_tag)
    tw = tb[2] - tb[0]
    d.rounded_rectangle(
        [54, H - 102, 54 + tw + 26, H - 76],
        radius=11,
        fill=(accent[0] // 5, accent[1] // 5, accent[2] // 5, 255),
        outline=(accent[0], accent[1], accent[2], 255),
        width=2,
    )
    d.text((67, H - 97), tag, fill=(accent[0], accent[1], accent[2], 255), font=f_tag)
    d.text((54, H - 68), title, fill=(255, 255, 255, 255), font=font(25, True))

    f_url = font(17, True)
    ub = d.textbbox((0, 0), url, font=f_url)
    uw = ub[2] - ub[0]
    d.rounded_rectangle([W - 56 - uw - 28, H - 90, W - 54, H - 48], radius=13, fill=(*chip_bg, 255))
    d.text((W - 56 - uw - 14, H - 79), url, fill=(*chip_fg, 255), font=f_url)
    frame.alpha_composite(ov)


def make_bg(c1=(0, 229, 255, 78), c2=(255, 229, 0, 52), c3=(4, 255, 0, 42)) -> Image.Image:
    bg = Image.new("RGBA", (W, H), (5, 10, 22, 255))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=(int(6 + 5 * (1 - t)), int(14 + 14 * (1 - t)), int(34 + 18 * (1 - t)), 255))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([220, -140, 1060, 380], fill=c1)
    gd.ellipse([860, 320, 1380, 820], fill=c2)
    gd.ellipse([-120, 280, 380, 780], fill=c3)
    glow = glow.filter(ImageFilter.GaussianBlur(95))
    bg.alpha_composite(glow)
    return bg


def make_cta_plate(
    kicker: str,
    kicker_color,
    sub_head: str,
    big1: str,
    big1_color,
    big2: str,
    big2_color,
    bullets: str,
    pill1: str,
    pill1_bg,
    pill1_fg,
    pill2: str,
    pill2_bg,
    pill2_fg,
    bg_glows,
    hero_penguin: Image.Image,
    app_icon: Image.Image,
) -> Image.Image:
    outro = make_bg(*bg_glows)
    hp = hero_penguin.copy()
    hp.thumbnail((420, 580), Image.Resampling.LANCZOS)
    outro.alpha_composite(hp, (805, 68))
    ic = app_icon.resize((92, 92), Image.Resampling.LANCZOS)
    imask = Image.new("L", (92, 92), 0)
    ImageDraw.Draw(imask).rounded_rectangle([0, 0, 91, 91], radius=22, fill=255)
    outro.paste(ic, (72, 74), imask)
    od = ImageDraw.Draw(outro)
    od.text((184, 82), kicker, fill=(*kicker_color, 255), font=font(21, True))
    od.text((184, 114), sub_head, fill=(255, 255, 255, 255), font=font(29, True))
    od.text((72, 202), big1, fill=(*big1_color, 255), font=font(70, True))
    od.text((72, 286), big2, fill=(*big2_color, 255), font=font(56, True))
    od.text((72, 372), bullets, fill=(216, 236, 255, 245), font=font(23, False))
    od.rounded_rectangle([72, 440, 720, 506], radius=16, fill=(*pill1_bg, 255))
    od.text((98, 459), pill1, fill=(*pill1_fg, 255), font=font(23, True))
    od.rounded_rectangle([72, 526, 720, 592], radius=16, fill=(*pill2_bg, 255))
    od.text((98, 545), pill2, fill=(*pill2_fg, 255), font=font(23, True))
    return outro


def encode_video_and_gif(name: str, scenes, render_fn, mp4_out: str, gif_out: str):
    total_dur = sum(dur for _, dur in scenes)
    fade_out_start = max(1.0, total_dur - 1.5)
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-",
    ]
    has_audio = os.path.exists(AUDIO_SRC)
    if has_audio:
        cmd += ["-stream_loop", "-1", "-i", AUDIO_SRC]
    cmd += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]
    if has_audio:
        cmd += [
            "-c:a", "aac", "-b:a", "128k",
            "-af", f"volume=0.35,afade=t=in:st=0:d=0.7,afade=t=out:st={fade_out_start:.2f}:d=1.5",
            "-shortest",
        ]
    cmd += [mp4_out]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    fade_frames = int(0.32 * FPS)
    prev_tail = None
    total_frames = 0

    for kind, dur in scenes:
        n_frames = int(round(dur * FPS))
        for fi in range(n_frames):
            t = fi / max(1, n_frames - 1)
            fr = render_fn(kind, t)
            if prev_tail is not None and fi < fade_frames:
                fr = Image.blend(prev_tail, fr, fi / float(fade_frames))
            proc.stdin.write(fr.convert("RGB").tobytes())
            total_frames += 1
            if fi == n_frames - 1:
                prev_tail = fr

    proc.stdin.close()
    rc = proc.wait()
    assert rc == 0, f"ffmpeg failed for {name} (rc={rc})"
    mp4_sz = os.path.getsize(mp4_out)
    print(f"✓ [{name}] MP4 -> {mp4_out} ({total_frames} frames, {mp4_sz / 1024 / 1024:.2f} MB)")

    # Encode compact GitHub-friendly GIF (< 4.3 MB guaranteed)
    pal_png = f"{VID_DIR}/{name}_palette.png"
    for fps_g, width_g, colors_g in [(8, 560, 96), (7, 500, 80), (6, 460, 64)]:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", mp4_out,
                "-vf", f"fps={fps_g},scale={width_g}:-1:flags=lanczos,palettegen=max_colors={colors_g}:stats_mode=diff",
                pal_png,
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", mp4_out, "-i", pal_png,
                "-lavfi", f"fps={fps_g},scale={width_g}:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
                gif_out,
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        gif_sz = os.path.getsize(gif_out)
        if gif_sz <= 4_300_000:
            break
    print(f"✓ [{name}] GIF -> {gif_out} ({os.path.getsize(gif_out) / 1024 / 1024:.2f} MB)")


def main():
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(VID_DIR, exist_ok=True)

    hero_penguin = Image.open(f"{APP_ASSETS}/hero-penguin.webp").convert("RGBA")
    app_icon = Image.open(f"{APP_ASSETS}/app-icon-512.png").convert("RGBA")

    # =========================================================================
    # VIDEO 1: APP DOWNLOAD + FIXED MOBILE APP + FOIL PACK STORE + REAL PULL
    # =========================================================================
    ad_full = Image.open(f"{CAP_DIR}/app/ad_full.png").convert("RGBA")
    ad_w, ad_h = ad_full.size
    ad_scaled_h = int(ad_h * (W / ad_w))
    ad_scaled = ad_full.resize((W, ad_scaled_h), Image.Resampling.LANCZOS)

    store_hero = Image.open(f"{CAP_DIR}/app/store_hero.jpg").convert("RGBA")
    store_catalog = Image.open(f"{CAP_DIR}/app/store_catalog.jpg").convert("RGBA")
    store_pull = Image.open(f"{CAP_DIR}/app/store_pull.jpg").convert("RGBA")
    mobile_live = Image.open(f"{MEDIA_DIR}/02b-mobile-app-live.png").convert("RGBA")

    mobile_cards = []
    for src_img in [
        mobile_live,
        Image.open(f"{MEDIA_DIR}/screen-packs.png").convert("RGBA"),
        Image.open(f"{MEDIA_DIR}/screen-pull.png").convert("RGBA"),
        Image.open(f"{MEDIA_DIR}/screen-stadium.png").convert("RGBA"),
    ]:
        sc = fit_cover(src_img, 248, 536)
        card = Image.new("RGBA", (264, 552), (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle([4, 4, 259, 547], radius=22, fill=(0, 229, 255, 88))
        card = card.filter(ImageFilter.GaussianBlur(4))
        mask = Image.new("L", (248, 536), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, 247, 535], radius=18, fill=255)
        card.paste(sc, (8, 8), mask)
        ImageDraw.Draw(card).rounded_rectangle([8, 8, 255, 543], radius=18, outline=(210, 248, 255, 255), width=2)
        mobile_cards.append(card)

    bg_app = make_bg()
    outro_app = make_cta_plate(
        "NEW RELEASE • ANDROID APK & iOS APP", (4, 255, 0),
        "FROSTYRIPS MOBILE v1.1.0",
        "GET A FREE PACK", (0, 255, 247),
        "IN THE APP TODAY", (255, 229, 0),
        "90% Instant Buyback • $0 Vaulting • 3D Megastadium",
        "APP:  frostrips.web.app/ad/landing/app", (0, 255, 247), (4, 22, 24),
        "PRESALE:  frostyrips-presale.web.app", (255, 229, 0), (14, 14, 4),
        ((0, 229, 255, 78), (255, 229, 0, 52), (4, 255, 0, 42)),
        hero_penguin, app_icon,
    )

    def render_app(kind: str, t: float) -> Image.Image:
        et = ease_in_out(t)
        if kind == "ad_scroll":
            max_y = max(0, ad_scaled_h - H)
            y = int(max_y * et)
            fr = ad_scaled.crop((0, y, W, y + H)).copy()
            draw_lower_third(fr, "APP LANDING PAGE", "Download v1.1.0 + Explore Presale, Store & 3D Stadium", "frostrips.web.app/ad/landing/app")
            return fr
        elif kind == "mobile_strip":
            fr = bg_app.copy()
            d = ImageDraw.Draw(fr)
            d.text((54, 24), "FROSTYRIPS MOBILE APP v1.1.0 — ZERO GLITCHES", fill=(0, 255, 247, 255), font=font(32, True))
            d.text((54, 64), "Live Mobile UI  •  42 Foil Packs  •  90% Instant Buyback  •  3D Megastadium", fill=(214, 236, 255, 228), font=font(18, False))
            for idx, card in enumerate(mobile_cards):
                bx = 66 + idx * 296
                bob = int(math.sin(t * math.pi * 2.0 + idx * 0.9) * 9)
                fr.alpha_composite(card, (bx, 118 + bob))
            return fr
        elif kind == "store":
            fr = fit_cover(store_hero, W, H, zoom=1.0 + 0.08 * et, pan_y=0.2 + 0.3 * et)
            draw_lower_third(fr, "OFFICIAL WEBSITE & STORE", "42 Liquid-Chrome Foil Packs • 25,000+ Graded Cards", "frostrips.web.app")
            return fr
        elif kind == "catalog":
            fr = fit_cover(store_catalog, W, H, zoom=1.02 + 0.07 * et, pan_y=0.25 + 0.4 * et)
            draw_lower_third(fr, "ALL 42 COLLECTIBLE PACKS", "Pokémon, Anime, Sports, Pop Icons & Sealed Slabs", "frostrips.web.app")
            return fr
        elif kind == "pull":
            fr = fit_cover(store_pull, W, H, zoom=1.0 + 0.09 * et, pan_y=0.3 + 0.25 * et)
            draw_lower_third(fr, "LIVE FOIL PACK RIP", "Instant 90% Fair Market Buyback • $0 Vaulting Forever", "frostrips.web.app", accent=(4, 255, 0))
            return fr
        return outro_app.copy()

    encode_video_and_gif(
        "app_demo",
        [("ad_scroll", 4.6), ("mobile_strip", 3.4), ("store", 2.8), ("catalog", 2.6), ("pull", 2.8), ("outro", 2.4)],
        render_app,
        f"{VID_DIR}/frostyrips-app-demo.mp4",
        f"{MEDIA_DIR}/frostyrips-app-demo.gif",
    )

    # =========================================================================
    # VIDEO 2: DEDICATED $FROSTY TOKEN PRESALE VIDEO
    # =========================================================================
    pre_full = Image.open(f"{CAP_DIR}/presale/presale_full.png").convert("RGBA")
    pw, ph = pre_full.size
    pre_scaled_h = int(ph * (W / pw))
    pre_scaled = pre_full.resize((W, pre_scaled_h), Image.Resampling.LANCZOS)
    pre_hero = Image.open(f"{MEDIA_DIR}/04-presale-portal.png").convert("RGBA")

    outro_presale = make_cta_plate(
        "LIVE NOW • ETHEREUM MAINNET", (255, 229, 0),
        "$FROSTY TOKEN PRESALE",
        "+5% EARLY-BIRD", (255, 229, 0),
        "BONUS LIVE NOW", (0, 255, 247),
        "10% OFF Packs • 50% Pack Burn • ETH, SOL & BNB",
        "PRESALE:  frostyrips-presale.web.app", (255, 229, 0), (14, 14, 4),
        "GET APP:  frostrips.web.app/ad/landing/app", (0, 255, 247), (4, 22, 24),
        ((255, 210, 0, 86), (0, 229, 255, 62), (255, 140, 0, 48)),
        hero_penguin, app_icon,
    )

    def render_presale(kind: str, t: float) -> Image.Image:
        et = ease_in_out(t)
        max_y = max(0, pre_scaled_h - H)
        if kind == "hero":
            fr = fit_cover(pre_hero, W, H, zoom=1.0 + 0.09 * et, pan_y=0.2 + 0.25 * et)
            draw_lower_third(
                fr, "$FROSTY PRESALE LIVE", "Early-Bird +5% Bonus • 10,000,000,000 Fixed Supply",
                "frostyrips-presale.web.app", accent=(255, 229, 0), chip_bg=(255, 229, 0), chip_fg=(14, 14, 4)
            )
            return fr
        elif kind == "scroll_top":
            y = int(max_y * 0.48 * et)
            fr = pre_scaled.crop((0, y, W, y + H)).copy()
            draw_lower_third(
                fr, "MULTI-CHAIN BUY WIDGET", "Contribute with ETH, SOL, BNB, USDT, USDC & WBTC",
                "frostyrips-presale.web.app", accent=(255, 229, 0), chip_bg=(0, 255, 247), chip_fg=(4, 20, 24)
            )
            return fr
        elif kind == "scroll_bot":
            y = int(max_y * (0.48 + 0.52 * et))
            fr = pre_scaled.crop((0, y, W, y + H)).copy()
            draw_lower_third(
                fr, "REAL PACK UTILITY & BURN", "10% OFF Every Pack • 50% Permanent Burn • +10% Referrals",
                "frostyrips-presale.web.app", accent=(0, 255, 247), chip_bg=(255, 229, 0), chip_fg=(14, 14, 4)
            )
            return fr
        return outro_presale.copy()

    encode_video_and_gif(
        "presale_video",
        [("hero", 3.0), ("scroll_top", 5.0), ("scroll_bot", 5.0), ("outro", 2.6)],
        render_presale,
        f"{VID_DIR}/frostyrips-presale-video.mp4",
        f"{MEDIA_DIR}/frostyrips-presale-video.gif",
    )

    # =========================================================================
    # VIDEO 3: DEDICATED 3D MEGASTADIUM LIVE BATTLE VIDEO
    # =========================================================================
    st_title = Image.open(f"{CAP_DIR}/stadium/st_00_title.jpg").convert("RGBA")
    st_lobby = Image.open(f"{CAP_DIR}/stadium/st_01_lobby.jpg").convert("RGBA")
    st_roster = Image.open(f"{CAP_DIR}/stadium/st_02_roster.jpg").convert("RGBA")
    battle_paths = sorted(glob.glob(f"{CAP_DIR}/stadium/battle_*.jpg"))
    battle_imgs = [Image.open(p).convert("RGBA") for p in battle_paths]
    print(f"Loaded {len(battle_imgs)} live 3D Megastadium battle frames!")

    outro_stadium = make_cta_plate(
        "REAL-TIME 3D WEBGL2 COLISEUM", (249, 65, 177),
        "FROSTYRIPS 3D MEGASTADIUM",
        "27,014 FIGHTERS", (255, 92, 214),
        "6 PBR 3D ARENAS", (0, 255, 247),
        "3D Pokémon GLB Models • Frostmax Ultimates • Free To Play",
        "PLAY 3D:  frostyrips-stadium.web.app", (249, 65, 177), (255, 255, 255),
        "GET APP:  frostrips.web.app/ad/landing/app", (0, 255, 247), (4, 22, 24),
        ((249, 65, 177, 88), (0, 229, 255, 72), (139, 92, 246, 62)),
        hero_penguin, app_icon,
    )

    def render_stadium(kind: str, t: float) -> Image.Image:
        et = ease_in_out(t)
        if kind == "title":
            fr = fit_cover(st_title, W, H, zoom=1.0 + 0.08 * et, pan_y=0.45)
            draw_lower_third(
                fr, "3D MEGASTADIUM ARENA", "Next-Gen 3D Battle Coliseum • 27,014 Fighters & 6 PBR Maps",
                "frostyrips-stadium.web.app", accent=(249, 65, 177), chip_bg=(249, 65, 177), chip_fg=(255, 255, 255)
            )
            return fr
        elif kind == "lobby":
            fr = fit_cover(st_lobby, W, H, zoom=1.0 + 0.07 * et, pan_y=0.5)
            draw_lower_third(
                fr, "LIVE 3D WAITING LOBBY", "Customize Fighters, Switch Arenas & Jump Straight Into Combat",
                "frostyrips-stadium.web.app", accent=(0, 255, 247), chip_bg=(255, 229, 0), chip_fg=(14, 14, 4)
            )
            return fr
        elif kind == "roster":
            fr = fit_cover(st_roster, W, H, zoom=1.0 + 0.07 * et, pan_y=0.4 + 0.2 * et)
            draw_lower_third(
                fr, "3D POKÉMON + FROSTYRIPS ROSTER", "Hundreds of 3D GLB Pokémon Models & FrostyRips Legends",
                "frostyrips-stadium.web.app", accent=(255, 229, 0), chip_bg=(0, 255, 247), chip_fg=(4, 20, 24)
            )
            return fr
        elif kind == "battle_1" or kind == "battle_2":
            if battle_imgs:
                half = max(1, len(battle_imgs) // 2)
                subset = battle_imgs[:half] if kind == "battle_1" else battle_imgs[half:]
                pos = t * max(0, len(subset) - 1)
                idx0 = int(pos)
                idx1 = min(len(subset) - 1, idx0 + 1)
                frac = pos - idx0
                im0 = subset[idx0]
                im1 = subset[idx1]
                # Crisp quick blend for ultra-fluid WebGL action feel
                fr = Image.blend(im0, im1, frac * 0.45).copy() if idx0 != idx1 else im0.copy()
            else:
                fr = st_title.copy()
            if kind == "battle_1":
                draw_lower_third(
                    fr, "LIVE 3D COMBAT ACTION", "Real-Time Combos, High Kicks, Dodges & Elemental Blasts",
                    "frostyrips-stadium.web.app", accent=(249, 65, 177), chip_bg=(255, 229, 0), chip_fg=(14, 14, 4)
                )
            else:
                draw_lower_third(
                    fr, "FROSTMAX ULTIMATES & 6 MAPS", "Dynamic Stage Switching, Hit-Stop FX & Stadium Spotlights",
                    "frostyrips-stadium.web.app", accent=(0, 255, 247), chip_bg=(249, 65, 177), chip_fg=(255, 255, 255)
                )
            return fr
        return outro_stadium.copy()

    encode_video_and_gif(
        "stadium_battle",
        [("title", 2.4), ("lobby", 2.2), ("roster", 2.4), ("battle_1", 4.2), ("battle_2", 4.2), ("outro", 2.4)],
        render_stadium,
        f"{VID_DIR}/frostyrips-stadium-battle.mp4",
        f"{MEDIA_DIR}/frostyrips-stadium-battle.gif",
    )

    print("ALL 3 VIDEOS AND 3 COMPACT GIFS GENERATED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
