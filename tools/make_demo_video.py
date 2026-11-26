#!/usr/bin/env python3
"""
Renders a sleek 1280x720 30fps H.264 showcase walkthrough video (frostyrips-demo.mp4)
and optimized animated preview GIF (frostyrips-demo.gif) from real headless Chromium
captures of FrostyRips App Landing, Pack Store, 3D Megastadium, and $FROSTY Presale.
"""
import math
import os
import subprocess
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HOME = "/data/data/com.termux/files/home"
MOBILE = f"{HOME}/frostyrips-mobile"
MEDIA_DIR = f"{MOBILE}/docs/media"
FRAMES_DIR = f"{MOBILE}/build/video_frames"
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


def draw_lower_third(frame: Image.Image, tag: str, title: str, url: str):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # Bottom gradient scrim
    for y in range(H - 170, H):
        a = int(220 * ((y - (H - 170)) / 170.0))
        d.line([(0, y), (W, y)], fill=(4, 9, 20, a))
    # Floating glass badge
    d.rounded_rectangle([38, H - 122, W - 38, H - 26], radius=18, fill=(7, 18, 40, 224), outline=(0, 229, 255, 190), width=2)
    # Neon tag pill
    d.rounded_rectangle([58, H - 106, 286, H - 78], radius=12, fill=(8, 48, 70, 255), outline=(0, 255, 247, 255), width=2)
    d.text((74, H - 101), tag, fill=(0, 255, 247, 255), font=font(15, True))
    d.text((58, H - 70), title, fill=(255, 255, 255, 255), font=font(26, True))
    # Right URL chip
    f_url = font(18, True)
    ub = d.textbbox((0, 0), url, font=f_url)
    uw = ub[2] - ub[0]
    d.rounded_rectangle([W - 76 - uw - 28, H - 94, W - 56, H - 52], radius=14, fill=(255, 229, 0, 255))
    d.text((W - 76 - uw - 14, H - 83), url, fill=(6, 14, 26, 255), font=f_url)
    frame.alpha_composite(ov)


def make_bg() -> Image.Image:
    bg = Image.new("RGBA", (W, H), (5, 10, 22, 255))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=(int(7 + 4 * (1 - t)), int(16 + 14 * (1 - t)), int(38 + 18 * (1 - t)), 255))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([240, -140, 1040, 380], fill=(0, 229, 255, 78))
    gd.ellipse([880, 320, 1380, 820], fill=(255, 229, 0, 52))
    gd.ellipse([-120, 280, 380, 780], fill=(4, 255, 0, 42))
    glow = glow.filter(ImageFilter.GaussianBlur(95))
    bg.alpha_composite(glow)
    return bg


def main():
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(FRAMES_DIR, exist_ok=True)

    # Copy the 4 crisp mobile showcase screens into docs/media as PNG too
    mobile_screens = []
    for name in ["screen-packs", "screen-pull", "screen-stadium", "screen-rewards"]:
        im = Image.open(f"{APP_ASSETS}/{name}.webp").convert("RGBA")
        im.convert("RGB").save(f"{MEDIA_DIR}/{name}.png", "PNG", optimize=True)
        mobile_screens.append(im)

    landing_tall = Image.open(f"{FRAMES_DIR}/landing-tall.png").convert("RGBA")
    packs_img = Image.open(f"{MEDIA_DIR}/03-packs-store.png").convert("RGBA")
    presale_img = Image.open(f"{MEDIA_DIR}/04-presale-portal.png").convert("RGBA")
    stadium_img = Image.open(f"{MEDIA_DIR}/05-megastadium-3d.png").convert("RGBA")
    hero_penguin = Image.open(f"{APP_ASSETS}/hero-penguin.webp").convert("RGBA")
    app_icon = Image.open(f"{APP_ASSETS}/app-icon-512.png").convert("RGBA")
    og_banner = Image.open(f"{APP_ASSETS}/og-app-download.png").convert("RGBA")
    og_banner.convert("RGB").save(f"{MEDIA_DIR}/00-hero-banner.png", "PNG", optimize=True)

    # Pre-scale mobile screens to 250x540 with crisp glowing white frame
    framed_screens = []
    for scr in mobile_screens:
        sc = scr.resize((250, 540), Image.Resampling.LANCZOS)
        card = Image.new("RGBA", (266, 556), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle([4, 4, 261, 551], radius=22, fill=(0, 229, 255, 85))
        card = card.filter(ImageFilter.GaussianBlur(4))
        mask = Image.new("L", (250, 540), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, 249, 539], radius=18, fill=255)
        card.paste(sc, (8, 8), mask)
        ImageDraw.Draw(card).rounded_rectangle([8, 8, 257, 547], radius=18, outline=(210, 248, 255, 255), width=2)
        framed_screens.append(card)

    base_bg = make_bg()

    # Pre-scale landing tall to exact width 1280
    lt_w, lt_h = landing_tall.size
    lt_scaled_h = int(lt_h * (W / lt_w))
    landing_scaled = landing_tall.resize((W, lt_scaled_h), Image.Resampling.LANCZOS)

    # Build outro plate
    outro = base_bg.copy()
    hp = hero_penguin.copy()
    hp.thumbnail((430, 590), Image.Resampling.LANCZOS)
    outro.alpha_composite(hp, (790, 62))
    ic = app_icon.resize((96, 96), Image.Resampling.LANCZOS)
    imask = Image.new("L", (96, 96), 0)
    ImageDraw.Draw(imask).rounded_rectangle([0, 0, 95, 95], radius=22, fill=255)
    outro.paste(ic, (76, 84), imask)
    od = ImageDraw.Draw(outro)
    od.text((192, 92), "NOW LIVE ON ANDROID & iOS", fill=(4, 255, 0, 255), font=font(22, True))
    od.text((192, 126), "FROSTYRIPS MOBILE v1.0.0", fill=(255, 255, 255, 255), font=font(30, True))
    od.text((76, 214), "GET A FREE PACK", fill=(0, 255, 247, 255), font=font(76, True))
    od.text((76, 304), "IN THE APP TODAY", fill=(255, 229, 0, 255), font=font(60, True))
    od.text((76, 392), "90% Instant Buyback • $0 Vaulting • 3D Megastadium", fill=(214, 236, 255, 245), font=font(24, False))
    od.rounded_rectangle([76, 456, 650, 524], radius=18, fill=(0, 255, 247, 255))
    od.text((104, 476), "APP:  frostrips.web.app/ad/landing/app", fill=(4, 22, 24, 255), font=font(24, True))
    od.rounded_rectangle([76, 544, 650, 610], radius=18, fill=(255, 229, 0, 255))
    od.text((104, 563), "PRESALE:  frostyrips-presale.web.app", fill=(14, 14, 4, 255), font=font(24, True))

    # Stream raw RGB24 frames directly into ffmpeg (no giant PNG folder needed!)
    mp4_out = f"{MEDIA_DIR}/frostyrips-demo.mp4"
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
        cmd += ["-c:a", "aac", "-b:a", "128k", "-af", "volume=0.35,afade=t=in:st=0:d=0.8,afade=t=out:st=19.2:d=1.8", "-shortest"]
    cmd += [mp4_out]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    # Timeline: 21 seconds total (630 frames @ 30fps)
    scenes = [
        ("landing", 4.2),   # Smooth live scroll down app landing page
        ("mobile", 3.8),    # 4 Retina mobile app screens floating carousel
        ("packs", 3.5),     # Live Foil Pack Store capture
        ("stadium", 3.2),   # Live 3D Megastadium capture
        ("presale", 3.3),   # Live $FROSTY Presale Portal capture
        ("outro", 3.0),     # FrostyRips App + Presale CTA card
    ]

    def render_scene(kind: str, t: float) -> Image.Image:
        et = ease_in_out(t)
        if kind == "landing":
            max_y = max(0, lt_scaled_h - H)
            y = int(max_y * et)
            fr = landing_scaled.crop((0, y, W, y + H)).copy()
            draw_lower_third(fr, "APP LANDING PAGE", "Download for Android & iOS — Claim a Free Foil Pack", "frostrips.web.app/ad/landing/app")
            return fr
        elif kind == "mobile":
            fr = base_bg.copy()
            d = ImageDraw.Draw(fr)
            d.text((54, 26), "WHAT'S IN THE FROSTYRIPS APP", fill=(0, 255, 247, 255), font=font(32, True))
            d.text((54, 66), "Packs Store  •  90% Instant Buyback  •  3D Megastadium  •  Daily Rewards", fill=(214, 236, 255, 225), font=font(18, False))
            for idx, card in enumerate(framed_screens):
                bx = 64 + idx * 296
                bob = int(math.sin(t * math.pi * 2.0 + idx * 0.9) * 10)
                entry_y = int((1.0 - min(1.0, t * 3.0 - idx * 0.18)) * 90) if (t * 3.0 - idx * 0.18) < 1.0 else 0
                fr.alpha_composite(card, (bx, 118 + bob + entry_y))
            return fr
        elif kind == "packs":
            fr = fit_cover(packs_img, W, H, zoom=1.0 + 0.08 * et, pan_y=0.15 + 0.4 * et)
            draw_lower_third(fr, "42 LIQUID-CHROME PACKS", "25,000+ Graded Cards • Instant 90% Buyback • $0 Vaulting", "frostrips.web.app")
            return fr
        elif kind == "stadium":
            fr = fit_cover(stadium_img, W, H, zoom=1.0 + 0.09 * et, pan_y=0.35 + 0.25 * et)
            draw_lower_third(fr, "3D MEGASTADIUM ARENA", "Real-Time 3D Coliseum Battles • 27,014 Fighters & 6 PBR Maps", "frostyrips-stadium.web.app")
            return fr
        elif kind == "presale":
            fr = fit_cover(presale_img, W, H, zoom=1.0 + 0.08 * et, pan_y=0.1 + 0.45 * et)
            draw_lower_third(fr, "$FROSTY TOKEN PRESALE", "Live Presale Portal • 50% Pack Burn • +10% Referral Rewards", "frostyrips-presale.web.app")
            return fr
        else:
            return outro.copy()

    # Render with 0.35s crossfade transitions between scenes
    fade_frames = int(0.35 * FPS)
    prev_tail = None
    total_frames = 0

    for si, (kind, dur) in enumerate(scenes):
        n_frames = int(round(dur * FPS))
        for fi in range(n_frames):
            t = fi / max(1, n_frames - 1)
            fr = render_scene(kind, t)
            if prev_tail is not None and fi < fade_frames:
                alpha = fi / float(fade_frames)
                fr = Image.blend(prev_tail, fr, alpha)
            proc.stdin.write(fr.convert("RGB").tobytes())
            total_frames += 1
            if fi == n_frames - 1:
                prev_tail = fr

    proc.stdin.close()
    rc = proc.wait()
    assert rc == 0, f"ffmpeg failed with exit code {rc}"
    print(f"✓ Rendered {total_frames} frames -> {mp4_out} ({os.path.getsize(mp4_out):,} bytes)")

    # Generate compact animated GIF preview (<5MB for instant GitHub README rendering)
    gif_out = f"{MEDIA_DIR}/frostyrips-demo.gif"
    pal_png = f"{FRAMES_DIR}/palette.png"
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp4_out, "-vf", "fps=8,scale=540:-1:flags=lanczos,palettegen=max_colors=96:stats_mode=diff", pal_png],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp4_out, "-i", pal_png, "-lavfi", "fps=8,scale=540:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle", gif_out],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"✓ Generated animated preview GIF -> {gif_out} ({os.path.getsize(gif_out):,} bytes)")


if __name__ == "__main__":
    main()
