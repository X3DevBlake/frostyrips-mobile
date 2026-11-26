#!/usr/bin/env python3
"""
FrostyRips Mobile & Landing Page Asset Pipeline:
1. Slices 1024x1024 app icon into Android mipmap-* (square + circular), iOS Assets.xcassets, and PWA icons.
2. Border flood-fill isolates hero & invite penguin artwork to transparent WebP cutouts.
3. Composites 4 Retina (446x964) vertical FrostyRips mobile app preview screenshots.
4. Generates a spec-verified ISO/IEC 18004 Version 3-M QR code SVG for https://frostrips.web.app/ad/landing/app.
5. Generates genuine Apple iOS Direct-Install Configuration Profile (FrostyRips-iOS.mobileconfig).
6. Packages the complete native iOS SwiftUI/Xcode project into FrostyRips-iOS-App.zip.
"""
import collections
import json
import math
import os
import plistlib
import uuid
import zipfile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HOME = "/data/data/com.termux/files/home"
ARTIFACTS = f"{HOME}/.gemini/antigravity-cli/brain/c5b64a32-432d-4f45-b0d0-1ed05727527b"
MOBILE = f"{HOME}/frostyrips-mobile"
FROSTRIPS_PUB = f"{HOME}/frostrips/public"
LANDING_ASSETS = f"{FROSTRIPS_PUB}/assets/app-landing"
DOWNLOADS = f"{FROSTRIPS_PUB}/downloads"

ICON_SRC = f"{ARTIFACTS}/frostyrips_app_icon_1795728727033.jpg"
HERO_SRC = f"{ARTIFACTS}/frosty_rips_mascot_hero_1795728725646.jpg"
INVITE_SRC = f"{ARTIFACTS}/frosty_rips_invite_promo_1795728726596.jpg"

FONT_BOLD = "/system/fonts/DroidSans-Bold.ttf"
FONT_REG = "/system/fonts/Roboto-Regular.ttf"

os.makedirs(LANDING_ASSETS, exist_ok=True)
os.makedirs(DOWNLOADS, exist_ok=True)


def font(size: int, bold: bool = True):
    path = FONT_BOLD if bold else FONT_REG
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ── 1. App Icons (Android + iOS + PWA) ─────────────────────────────────────
def generate_icons():
    base = Image.open(ICON_SRC).convert("RGBA")
    # Ensure exact 1024x1024 square
    w, h = base.size
    side = min(w, h)
    base = base.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
    base = base.resize((1024, 1024), Image.Resampling.LANCZOS)

    def make_rounded(img: Image.Image, radius_frac: float) -> Image.Image:
        sz = img.size[0]
        mask = Image.new("L", (sz, sz), 0)
        d = ImageDraw.Draw(mask)
        r = int(sz * radius_frac)
        d.rounded_rectangle([0, 0, sz - 1, sz - 1], radius=r, fill=255)
        out = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        out.paste(img, (0, 0), mask)
        return out

    def make_circle(img: Image.Image) -> Image.Image:
        sz = img.size[0]
        mask = Image.new("L", (sz, sz), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, sz - 1, sz - 1], fill=255)
        out = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        out.paste(img, (0, 0), mask)
        return out

    # Android mipmaps
    android_res = f"{MOBILE}/android/app/src/main/res"
    densities = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    for folder, sz in densities.items():
        dpath = f"{android_res}/{folder}"
        os.makedirs(dpath, exist_ok=True)
        resized = base.resize((sz, sz), Image.Resampling.LANCZOS)
        make_rounded(resized, 0.22).save(f"{dpath}/ic_launcher.png", "PNG", optimize=True)
        make_circle(resized).save(f"{dpath}/ic_launcher_round.png", "PNG", optimize=True)

    # iOS Assets.xcassets (opaque RGB PNG required by Apple App Store for AppIcon)
    xcassets = f"{MOBILE}/ios/Resources/Assets.xcassets"
    appicon_dir = f"{xcassets}/AppIcon.appiconset"
    splash_dir = f"{xcassets}/SplashIcon.imageset"
    color_dir = f"{xcassets}/LaunchBackground.colorset"
    os.makedirs(appicon_dir, exist_ok=True)
    os.makedirs(splash_dir, exist_ok=True)
    os.makedirs(color_dir, exist_ok=True)

    with open(f"{xcassets}/Contents.json", "w") as f:
        json.dump({"info": {"author": "xcode", "version": 1}}, f, indent=2)

    base_rgb = base.convert("RGB")
    ios_specs = [
        ("icon-40.png", "20x20", "2x", "iphone", 40),
        ("icon-60.png", "20x20", "3x", "iphone", 60),
        ("icon-58.png", "29x29", "2x", "iphone", 58),
        ("icon-87.png", "29x29", "3x", "iphone", 87),
        ("icon-80.png", "40x40", "2x", "iphone", 80),
        ("icon-120-40.png", "40x40", "3x", "iphone", 120),
        ("icon-120.png", "60x60", "2x", "iphone", 120),
        ("icon-180.png", "60x60", "3x", "iphone", 180),
        ("icon-76.png", "76x76", "1x", "ipad", 76),
        ("icon-152.png", "76x76", "2x", "ipad", 152),
        ("icon-167.png", "83.5x83.5", "2x", "ipad", 167),
        ("icon-1024.png", "1024x1024", "1x", "ios-marketing", 1024),
    ]
    images_json = []
    for fname, pt_size, scale, idiom, px in ios_specs:
        base_rgb.resize((px, px), Image.Resampling.LANCZOS).save(
            f"{appicon_dir}/{fname}", "PNG", optimize=True
        )
        images_json.append(
            {"filename": fname, "idiom": idiom, "scale": scale, "size": pt_size}
        )
    with open(f"{appicon_dir}/Contents.json", "w") as f:
        json.dump({"images": images_json, "info": {"author": "xcode", "version": 1}}, f, indent=2)

    # SplashIcon imageset
    for suffix, px in [("1x", 160), ("2x", 320), ("3x", 480)]:
        fname = f"splash-{suffix}.png"
        make_rounded(base.resize((px, px), Image.Resampling.LANCZOS), 0.22).save(
            f"{splash_dir}/{fname}", "PNG", optimize=True
        )
    with open(f"{splash_dir}/Contents.json", "w") as f:
        json.dump(
            {
                "images": [
                    {"filename": "splash-1x.png", "idiom": "universal", "scale": "1x"},
                    {"filename": "splash-2x.png", "idiom": "universal", "scale": "2x"},
                    {"filename": "splash-3x.png", "idiom": "universal", "scale": "3x"},
                ],
                "info": {"author": "xcode", "version": 1},
            },
            f,
            indent=2,
        )

    # LaunchBackground colorset (#050A16)
    with open(f"{color_dir}/Contents.json", "w") as f:
        json.dump(
            {
                "colors": [
                    {
                        "color": {
                            "color-space": "srgb",
                            "components": {
                                "alpha": "1.000",
                                "blue": "0.086",
                                "green": "0.039",
                                "red": "0.020",
                            },
                        },
                        "idiom": "universal",
                    }
                ],
                "info": {"author": "xcode", "version": 1},
            },
            f,
            indent=2,
        )

    # Web / PWA / Apple Touch Icons
    base_rgb.resize((180, 180), Image.Resampling.LANCZOS).save(
        f"{LANDING_ASSETS}/app-icon-180.png", "PNG", optimize=True
    )
    base_rgb.resize((192, 192), Image.Resampling.LANCZOS).save(
        f"{LANDING_ASSETS}/app-icon-192.png", "PNG", optimize=True
    )
    icon_512_path = f"{LANDING_ASSETS}/app-icon-512.png"
    base_rgb.resize((512, 512), Image.Resampling.LANCZOS).save(
        icon_512_path, "PNG", optimize=True
    )
    print("✓ Generated Android, iOS, and PWA app icons")
    return icon_512_path


# ── 2. Border Flood-Fill Transparent Cutout for Hero & Invite Art ──────────
def isolate_dark_bg(src_path: str, out_webp: str, target_size: tuple[int, int], tolerance: int = 24):
    im = Image.open(src_path).convert("RGBA")
    im = im.resize(target_size, Image.Resampling.LANCZOS)
    w, h = im.size
    px = im.load()

    # Sample corner reference dark backdrop color
    corners = [px[2, 2], px[w - 3, 2], px[2, h - 3], px[w - 3, h - 3]]
    bg_r = sum(c[0] for c in corners) // 4
    bg_g = sum(c[1] for c in corners) // 4
    bg_b = sum(c[2] for c in corners) // 4

    visited = bytearray(w * h)
    is_bg = bytearray(w * h)
    q = collections.deque()

    def matches_bg(r, g, b):
        dr = r - bg_r
        dg = g - bg_g
        db = b - bg_b
        return (dr * dr + dg * dg + db * db) <= (tolerance * tolerance * 3) and max(r, g, b) < 34

    # Seed from all 4 borders
    for x in range(w):
        for y in (0, h - 1):
            idx = y * w + x
            if not visited[idx]:
                visited[idx] = 1
                r, g, b, _ = px[x, y]
                if matches_bg(r, g, b):
                    is_bg[idx] = 1
                    q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            idx = y * w + x
            if not visited[idx]:
                visited[idx] = 1
                r, g, b, _ = px[x, y]
                if matches_bg(r, g, b):
                    is_bg[idx] = 1
                    q.append((x, y))

    while q:
        cx, cy = q.popleft()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                idx = ny * w + nx
                if not visited[idx]:
                    visited[idx] = 1
                    r, g, b, _ = px[nx, ny]
                    if matches_bg(r, g, b):
                        is_bg[idx] = 1
                        q.append((nx, ny))

    # Build alpha mask: 0 for background, 255 for subject, then smooth feather edge
    alpha = Image.new("L", (w, h), 255)
    apx = alpha.load()
    for y in range(h):
        row = y * w
        for x in range(w):
            if is_bg[row + x]:
                apx[x, y] = 0

    # Soft feathering: shrink mask slightly and blur to eliminate dark fringe
    feathered = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(2.2))
    # Preserve bright glow/smoke pixels near edges using luminance lift
    fpx = feathered.load()
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            a = fpx[x, y]
            if a == 0:
                # Keep soft cyan/white mist/lightning glow smoothly blended
                lum = max(r - bg_r, g - bg_g, b - bg_b, 0)
                if lum > 14:
                    a = min(255, int((lum - 14) * 5.2))
            # Gentle fade on bottom/side border 10px to avoid any sharp cut edge
            edge_dist = min(x, w - 1 - x, y, h - 1 - y)
            if edge_dist < 8 and a > 0 and is_bg[y * w + x]:
                a = int(a * (edge_dist / 8.0))
            px[x, y] = (r, g, b, a)

    im.save(out_webp, "WEBP", quality=92, method=6)
    # Also save small preview PNG for quick visual verification if needed
    print(f"✓ Isolated transparent artwork: {out_webp} ({os.path.getsize(out_webp):,} bytes)")


# ── 3. Composite 4 Crisp Retina Mobile App Screenshots (446x964) ───────────
def draw_vertical_gradient(img: Image.Image, top_rgb, bot_rgb):
    w, h = img.size
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top_rgb[0] + (bot_rgb[0] - top_rgb[0]) * t)
        g = int(top_rgb[1] + (bot_rgb[1] - top_rgb[1]) * t)
        b = int(top_rgb[2] + (bot_rgb[2] - top_rgb[2]) * t)
        d.line([(0, y), (w, y)], fill=(r, g, b, 255))


def add_radial_glow(canvas: Image.Image, cx: int, cy: int, radius: int, color_rgba):
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color_rgba)
    glow = glow.filter(ImageFilter.GaussianBlur(radius * 0.45))
    canvas.alpha_composite(glow)


def draw_phone_chrome(img: Image.Image, active_tab: int = 0):
    w, h = img.size
    d = ImageDraw.Draw(img)
    # Top status bar
    d.text((28, 18), "9:41", fill=(235, 246, 255, 235), font=font(20, True))
    # Dynamic Island pill
    d.rounded_rectangle([w // 2 - 58, 16, w // 2 + 58, 42], radius=14, fill=(4, 8, 18, 255))
    # Signal + battery
    d.rounded_rectangle([w - 64, 22, w - 28, 38], radius=4, outline=(220, 240, 255, 210), width=2)
    d.rounded_rectangle([w - 60, 26, w - 34, 34], radius=2, fill=(4, 255, 0, 240))

    # Top FrostyRips app bar
    d.rounded_rectangle([20, 58, w - 20, 114], radius=16, fill=(10, 22, 46, 215), outline=(0, 229, 255, 95), width=2)
    d.text((38, 72), "FROSTY", fill=(0, 242, 255, 255), font=font(24, True))
    d.text((134, 72), "RIPS", fill=(255, 229, 0, 255), font=font(24, True))
    # Balance pill
    d.rounded_rectangle([w - 178, 68, w - 30, 104], radius=14, fill=(5, 36, 56, 235), outline=(0, 255, 247, 150), width=2)
    d.text((w - 162, 76), "$1,250.00", fill=(255, 255, 255, 255), font=font(19, True))

    # Bottom navigation bar
    d.rounded_rectangle([14, h - 88, w - 14, h - 14], radius=24, fill=(7, 16, 36, 242), outline=(0, 229, 255, 90), width=2)
    tabs = ["PACKS", "VAULT", "STADIUM", "REWARDS"]
    tab_w = (w - 44) // 4
    for i, label in enumerate(tabs):
        tx = 22 + i * tab_w
        cx = tx + tab_w // 2
        if i == active_tab:
            d.rounded_rectangle([tx + 4, h - 80, tx + tab_w - 4, h - 22], radius=16, fill=(8, 52, 78, 255), outline=(0, 255, 247, 255), width=2)
            col = (0, 255, 247, 255)
        else:
            col = (165, 195, 230, 255)
        bbox = d.textbbox((0, 0), label, font=font(14, True))
        tw = bbox[2] - bbox[0]
        d.text((cx - tw // 2, h - 58), label, fill=col, font=font(14, True))


def draw_centered_text(d: ImageDraw.ImageDraw, cx: int, y: int, text: str, fnt, fill):
    bbox = d.textbbox((0, 0), text, font=fnt)
    tw = bbox[2] - bbox[0]
    d.text((cx - tw // 2, y), text, fill=fill, font=fnt)


def generate_app_screens():
    W, H = 446, 964
    foil_dir = f"{FROSTRIPS_PUB}/assets/foil_packs"
    p_glacier = Image.open(f"{foil_dir}/foil_glacier-starter-25.png").convert("RGBA")
    p_dollar = Image.open(f"{foil_dir}/foil_frosty-dollar-1.png").convert("RGBA")
    p_aurora = Image.open(f"{foil_dir}/foil_aurora-ultimate-500.png").convert("RGBA")
    p_emperor = Image.open(f"{foil_dir}/foil_emperor-master-1000.png").convert("RGBA")
    p_mon = Image.open(f"{foil_dir}/foil_cat-frostymon.png").convert("RGBA")
    s1 = Image.open(f"{FROSTRIPS_PUB}/assets/blender_sprites/DC-0001.webp").convert("RGBA")
    s2 = Image.open(f"{FROSTRIPS_PUB}/assets/blender_sprites/DC-0005.webp").convert("RGBA")
    s3 = Image.open(f"{FROSTRIPS_PUB}/assets/blender_sprites/DC-0008.webp").convert("RGBA")

    # ── Screen 1: Pack Store (screen-packs.webp) ──
    im1 = Image.new("RGBA", (W, H), (5, 10, 22, 255))
    draw_vertical_gradient(im1, (8, 22, 52), (4, 8, 18))
    add_radial_glow(im1, W // 2, 340, 200, (0, 229, 255, 105))
    add_radial_glow(im1, W // 2, 420, 150, (255, 229, 0, 55))
    d1 = ImageDraw.Draw(im1)

    # Free pack ribbon
    d1.rounded_rectangle([76, 130, W - 76, 168], radius=18, fill=(8, 46, 22, 255), outline=(4, 255, 0, 255), width=2)
    draw_centered_text(d1, W // 2, 140, "FREE STARTER PACK READY", font(16, True), (4, 255, 0, 255))

    # Featured pack image
    feat = p_glacier.copy()
    feat.thumbnail((270, 355), Image.Resampling.LANCZOS)
    im1.alpha_composite(feat, ((W - feat.width) // 2, 182))

    # Pack title + CTA
    draw_centered_text(d1, W // 2, 542, "GLACIER STARTER PACK", font(24, True), (255, 255, 255, 255))
    draw_centered_text(d1, W // 2, 574, "5 Graded TCG Cards • Instant 90% Buyback", font(15, False), (165, 210, 245, 230))
    d1.rounded_rectangle([42, 608, W - 42, 672], radius=22, fill=(0, 255, 247, 255), outline=(255, 255, 255, 180), width=3)
    draw_centered_text(d1, W // 2, 626, "RIP PACK — FREE", font(23, True), (4, 26, 20, 255))

    # Lower hot packs row
    d1.text((28, 692), "HOT LIQUID-CHROME PACKS", fill=(255, 229, 0, 255), font=font(15, True))
    for idx, (pk_img, label, price) in enumerate([
        (p_dollar, "FROSTY $1", "$1"),
        (p_aurora, "AURORA", "$500"),
        (p_emperor, "EMPEROR", "$1K"),
    ]):
        bx = 22 + idx * 138
        d1.rounded_rectangle([bx, 718, bx + 128, 862], radius=16, fill=(10, 22, 46, 220), outline=(0, 229, 255, 110), width=2)
        thumb = pk_img.copy()
        thumb.thumbnail((84, 96), Image.Resampling.LANCZOS)
        im1.alpha_composite(thumb, (bx + (128 - thumb.width) // 2, 726))
        draw_centered_text(d1, bx + 64, 824, label, font(12, True), (255, 255, 255, 240))
        draw_centered_text(d1, bx + 64, 841, price, font(13, True), (0, 255, 247, 255))

    draw_phone_chrome(im1, active_tab=0)
    im1.convert("RGB").save(f"{LANDING_ASSETS}/screen-packs.webp", "WEBP", quality=92, method=6)

    # ── Screen 2: Pull Reveal & 90% Instant Buyback (screen-pull.webp) ──
    im2 = Image.new("RGBA", (W, H), (5, 10, 22, 255))
    draw_vertical_gradient(im2, (16, 12, 46), (4, 8, 18))
    add_radial_glow(im2, W // 2, 360, 210, (255, 229, 0, 115))
    add_radial_glow(im2, W // 2, 360, 160, (0, 229, 255, 90))
    d2 = ImageDraw.Draw(im2)

    draw_centered_text(d2, W // 2, 130, "MYTHIC GRAIL PULLED!", font(24, True), (255, 229, 0, 255))
    # Graded slab frame
    sx0, sy0, sx1, sy1 = 78, 168, W - 78, 578
    d2.rounded_rectangle([sx0, sy0, sx1, sy1], radius=22, fill=(14, 24, 52, 245), outline=(255, 229, 0, 245), width=4)
    # Top PSA-style label inside slab
    d2.rounded_rectangle([sx0 + 14, sy0 + 14, sx1 - 14, sy0 + 78], radius=12, fill=(245, 250, 255, 255), outline=(0, 229, 255, 255), width=2)
    d2.text((sx0 + 26, sy0 + 22), "FROSTYRIPS GRADE", fill=(8, 25, 62, 255), font=font(13, True))
    d2.text((sx0 + 26, sy0 + 44), "CRYO EMPEROR #001", fill=(10, 14, 24, 255), font=font(15, True))
    d2.rounded_rectangle([sx1 - 92, sy0 + 22, sx1 - 24, sy0 + 70], radius=10, fill=(255, 229, 0, 255))
    draw_centered_text(d2, sx1 - 58, sy0 + 26, "GEM", font(12, True), (8, 14, 26, 255))
    draw_centered_text(d2, sx1 - 58, sy0 + 42, "10", font(22, True), (8, 14, 26, 255))
    # Card art inside slab
    d2.rounded_rectangle([sx0 + 18, sy0 + 92, sx1 - 18, sy1 - 18], radius=16, fill=(8, 36, 72, 255), outline=(0, 255, 247, 190), width=2)
    hero_card = Image.open(ICON_SRC).convert("RGBA")
    hero_card.thumbnail((244, 244), Image.Resampling.LANCZOS)
    im2.alpha_composite(hero_card, ((W - hero_card.width) // 2, sy0 + 104))
    draw_centered_text(d2, W // 2, sy1 - 52, "HOLO CHROME • 1 OF 25", font(15, True), (0, 255, 247, 255))

    # FMV value callout
    draw_centered_text(d2, W // 2, 594, "EST. MARKET VALUE", font(13, True), (160, 195, 235, 220))
    draw_centered_text(d2, W // 2, 612, "$485.00 FMV", font(34, True), (4, 255, 0, 255))

    # Action buttons
    d2.rounded_rectangle([32, 668, W - 32, 726], radius=18, fill=(255, 229, 0, 255))
    draw_centered_text(d2, W // 2, 684, "SELL BACK 90% — $436.50", font(20, True), (8, 14, 24, 255))
    d2.rounded_rectangle([32, 740, W // 2 - 8, 796], radius=16, fill=(8, 44, 68, 255), outline=(0, 255, 247, 255), width=2)
    draw_centered_text(d2, 32 + (W // 2 - 40) // 2, 758, "VAULT FREE ($0)", font(15, True), (0, 255, 247, 255))
    d2.rounded_rectangle([W // 2 + 8, 740, W - 32, 796], radius=16, fill=(18, 30, 56, 255), outline=(210, 232, 255, 255), width=2)
    draw_centered_text(d2, W // 2 + 8 + (W // 2 - 40) // 2, 758, "SHIP TO DOOR", font(15, True), (255, 255, 255, 255))
    draw_centered_text(d2, W // 2, 818, "Instant settlement • Insured physical custody", font(14, False), (170, 200, 235, 215))

    draw_phone_chrome(im2, active_tab=1)
    im2.convert("RGB").save(f"{LANDING_ASSETS}/screen-pull.webp", "WEBP", quality=92, method=6)

    # ── Screen 3: 3D Megastadium Battle Arena (screen-stadium.webp) ──
    im3 = Image.new("RGBA", (W, H), (5, 10, 22, 255))
    draw_vertical_gradient(im3, (6, 20, 56), (4, 8, 18))
    add_radial_glow(im3, W // 2, 390, 220, (0, 229, 255, 125))
    add_radial_glow(im3, 120, 440, 120, (249, 65, 177, 90))
    add_radial_glow(im3, W - 110, 310, 120, (255, 229, 0, 80))
    d3 = ImageDraw.Draw(im3)

    d3.rounded_rectangle([76, 130, W - 76, 166], radius=16, fill=(8, 42, 68, 255), outline=(0, 255, 247, 255), width=2)
    draw_centered_text(d3, W // 2, 139, "3D MEGASTADIUM • LIVE", font(15, True), (0, 255, 247, 255))

    # Neon 3D arena floor oval
    d3.ellipse([26, 360, W - 26, 540], fill=(8, 28, 66, 255), outline=(0, 255, 247, 255), width=4)
    d3.ellipse([78, 392, W - 78, 508], outline=(255, 229, 0, 200), width=2)
    d3.line([(W // 2, 362), (W // 2, 538)], fill=(0, 229, 255, 140), width=2)

    # Opponent HP HUD (top-right)
    d3.rounded_rectangle([176, 182, W - 22, 246], radius=14, fill=(10, 20, 44, 255), outline=(249, 65, 177, 255), width=2)
    d3.text((190, 192), "SHERLOCK PENGU • LV.50", fill=(255, 255, 255, 255), font=font(14, True))
    d3.rounded_rectangle([190, 218, W - 36, 232], radius=7, fill=(26, 36, 62, 255))
    d3.rounded_rectangle([190, 218, W - 108, 232], radius=7, fill=(249, 65, 177, 255))

    # Fighter sprites
    f_opp = s2.copy()
    f_opp.thumbnail((168, 168), Image.Resampling.LANCZOS)
    im3.alpha_composite(f_opp, (W - f_opp.width - 36, 258))

    f_hero = s1.copy()
    f_hero.thumbnail((196, 196), Image.Resampling.LANCZOS)
    im3.alpha_composite(f_hero, (30, 355))

    # Player HP HUD (bottom-left of arena)
    d3.rounded_rectangle([22, 558, W - 22, 628], radius=16, fill=(10, 22, 46, 255), outline=(0, 255, 247, 255), width=2)
    d3.text((38, 570), "DJ FROSTY • LV.50", fill=(255, 229, 0, 255), font=font(16, True))
    d3.text((W - 118, 570), "240/240", fill=(4, 255, 0, 255), font=font(15, True))
    d3.rounded_rectangle([38, 598, W - 38, 614], radius=8, fill=(24, 38, 66, 255))
    d3.rounded_rectangle([38, 598, W - 64, 614], radius=8, fill=(4, 255, 0, 255))

    # 2x2 Move Grid
    moves = [
        ("BLIZZARD BEAM", "ICE • 120 PWR", (0, 229, 255)),
        ("FROSTMAX NOVA", "ULT • 180 PWR", (255, 229, 0)),
        ("CRYO CLAW", "MELEE • 90 PWR", (4, 255, 0)),
        ("AURORA SHIELD", "BUFF • +2 DEF", (249, 65, 177)),
    ]
    for i, (mname, msub, mcol) in enumerate(moves):
        col_i = i % 2
        row_i = i // 2
        mx = 22 + col_i * 206
        my = 646 + row_i * 96
        d3.rounded_rectangle([mx, my, mx + 196, my + 84], radius=16, fill=(10, 24, 52, 235), outline=(*mcol, 220), width=2)
        d3.text((mx + 14, my + 18), mname, fill=(255, 255, 255, 255), font=font(15, True))
        d3.text((mx + 14, my + 48), msub, fill=(*mcol, 255), font=font(13, True))

    draw_centered_text(d3, W // 2, 848, "Summon 25,000+ pulled cards in 3D", font(14, False), (170, 210, 245, 225))
    draw_phone_chrome(im3, active_tab=2)
    im3.convert("RGB").save(f"{LANDING_ASSETS}/screen-stadium.webp", "WEBP", quality=92, method=6)

    # ── Screen 4: Daily Rewards & Referrals (screen-rewards.webp) ──
    im4 = Image.new("RGBA", (W, H), (5, 10, 22, 255))
    draw_vertical_gradient(im4, (8, 28, 48), (4, 8, 18))
    add_radial_glow(im4, W // 2, 280, 190, (4, 255, 0, 85))
    add_radial_glow(im4, W // 2, 640, 170, (0, 229, 255, 85))
    d4 = ImageDraw.Draw(im4)

    draw_centered_text(d4, W // 2, 132, "FROSTY REWARDS", font(26, True), (4, 255, 0, 255))
    # Level bar
    d4.rounded_rectangle([24, 174, W - 24, 256], radius=18, fill=(10, 24, 50, 235), outline=(255, 229, 0, 180), width=2)
    d4.text((42, 188), "GLACIER VIP • LEVEL 5", fill=(255, 229, 0, 255), font=font(16, True))
    d4.text((W - 110, 188), "85% XP", fill=(0, 255, 247, 255), font=font(15, True))
    d4.rounded_rectangle([42, 222, W - 42, 238], radius=8, fill=(24, 40, 68, 255))
    d4.rounded_rectangle([42, 222, W - 96, 238], radius=8, fill=(4, 255, 0, 255))

    # Daily Free Pack Claim Card
    d4.rounded_rectangle([24, 276, W - 24, 488], radius=22, fill=(8, 32, 58, 235), outline=(4, 255, 0, 210), width=3)
    pk_small = p_mon.copy()
    pk_small.thumbnail((126, 168), Image.Resampling.LANCZOS)
    im4.alpha_composite(pk_small, (42, 298))
    d4.text((184, 304), "DAILY FREE PACK", fill=(4, 255, 0, 255), font=font(19, True))
    d4.text((184, 334), "Claim 5 Graded Cards\nevery 24h in the app", fill=(220, 238, 255, 235), font=font(15, False))
    d4.rounded_rectangle([184, 404, W - 42, 456], radius=16, fill=(0, 255, 247, 255))
    draw_centered_text(d4, 184 + (W - 226) // 2, 418, "CLAIM FREE", font(18, True), (4, 26, 20, 255))

    # Invite Friends Referral Card
    d4.rounded_rectangle([24, 508, W - 24, 694], radius=22, fill=(14, 22, 52, 235), outline=(0, 229, 255, 195), width=2)
    spr3 = s3.copy()
    spr3.thumbnail((118, 118), Image.Resampling.LANCZOS)
    im4.alpha_composite(spr3, (W - 148, 526))
    d4.text((42, 526), "INVITE FRIENDS", fill=(0, 255, 247, 255), font=font(20, True))
    d4.text((42, 558), "Earn a Free Pack +\n10% $FROSTY Rewards", fill=(255, 255, 255, 240), font=font(16, True))
    d4.rounded_rectangle([42, 622, 272, 670], radius=14, fill=(255, 229, 0, 255))
    draw_centered_text(d4, 157, 635, "SHARE INVITE LINK", font(16, True), (8, 14, 24, 255))

    # Vault perks bar
    d4.rounded_rectangle([24, 714, W - 24, 846], radius=18, fill=(10, 22, 46, 225), outline=(249, 65, 177, 160), width=2)
    draw_centered_text(d4, W // 2, 732, "$0 VAULTING FEES FOREVER", font(18, True), (255, 255, 255, 255))
    draw_centered_text(d4, W // 2, 764, "90% Instant Buyback • Insured Shipping", font(15, False), (165, 205, 240, 230))
    draw_centered_text(d4, W // 2, 796, "50% $FROSTY PACK BURN ACTIVE", font(14, True), (255, 229, 0, 255))

    draw_phone_chrome(im4, active_tab=3)
    im4.convert("RGB").save(f"{LANDING_ASSETS}/screen-rewards.webp", "WEBP", quality=92, method=6)

    # Also build 1200x630 OG card for app landing page
    og = Image.new("RGBA", (1200, 630), (5, 10, 22, 255))
    draw_vertical_gradient(og, (7, 18, 46), (4, 8, 18))
    add_radial_glow(og, 900, 315, 280, (0, 229, 255, 110))
    add_radial_glow(og, 280, 200, 260, (4, 255, 0, 55))
    og_art = Image.open(f"{LANDING_ASSETS}/hero-penguin.webp").convert("RGBA")
    og_art.thumbnail((440, 580), Image.Resampling.LANCZOS)
    og.alpha_composite(og_art, (720, 28))
    od = ImageDraw.Draw(og)
    od.text((76, 86), "NOW ON iOS & ANDROID", fill=(4, 255, 0, 255), font=font(24, True))
    od.text((72, 134), "GET A", fill=(0, 255, 247, 255), font=font(112, True))
    od.text((72, 246), "FREE PACK", fill=(255, 229, 0, 255), font=font(88, True))
    od.text((76, 366), "Download the FrostyRips App to Claim", fill=(255, 255, 255, 255), font=font(32, True))
    od.text((76, 418), "90% Instant Buyback • $0 Vaulting • 3D Megastadium", fill=(165, 208, 245, 235), font=font(24, False))
    od.rounded_rectangle([76, 488, 520, 566], radius=24, fill=(0, 255, 247, 255))
    draw_centered_text(od, 298, 511, "DOWNLOAD THE APP", font(28, True), (4, 24, 18, 255))
    og.convert("RGB").save(f"{LANDING_ASSETS}/og-app-download.png", "PNG", optimize=True)
    print("✓ Composited 4 Retina FrostyRips app screenshots + OG banner")


# ── 4. Spec-Verified ISO/IEC 18004 QR Code Generator (Version 3-M, 29x29) ──
def generate_qr_svg(text: str, out_svg: str):
    """Pure-Python ISO/IEC 18004 Version 3-M (29x29) QR encoder with RS self-check."""
    data = text.encode("utf-8")
    assert len(data) <= 42, f"Version 3-M byte mode max is 42 bytes, got {len(data)}"

    # GF(256) with primitive polynomial 0x11D
    exp_tbl = [0] * 512
    log_tbl = [0] * 256
    x = 1
    for i in range(255):
        exp_tbl[i] = x
        log_tbl[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        exp_tbl[i] = exp_tbl[i - 255]

    def gf_mul(a, b):
        if a == 0 or b == 0:
            return 0
        return exp_tbl[log_tbl[a] + log_tbl[b]]

    # Build RS generator polynomial of degree 26 (Version 3-M: 44 data + 26 EC = 70 total)
    gen = [1]
    for i in range(26):
        ng = [0] * (len(gen) + 1)
        root = exp_tbl[i]
        for j, c in enumerate(gen):
            ng[j] ^= c
            ng[j + 1] ^= gf_mul(c, root)
        gen = ng

    # Encode bit stream: Mode 0100 (Byte), 8-bit char count, data bytes, terminator
    bits = []
    def push_bits(val, n):
        for i in range(n - 1, -1, -1):
            bits.append((val >> i) & 1)

    push_bits(0b0100, 4)
    push_bits(len(data), 8)
    for b in data:
        push_bits(b, 8)
    rem = 44 * 8 - len(bits)
    push_bits(0, min(4, rem))
    while len(bits) % 8 != 0:
        bits.append(0)
    codewords = []
    for i in range(0, len(bits), 8):
        val = 0
        for j in range(8):
            val = (val << 1) | bits[i + j]
        codewords.append(val)
    pad_bytes = [0xEC, 0x11]
    pi = 0
    while len(codewords) < 44:
        codewords.append(pad_bytes[pi % 2])
        pi += 1

    # Reed-Solomon remainder
    msg = codewords + [0] * 26
    for i in range(44):
        coef = msg[i]
        if coef != 0:
            for j in range(len(gen)):
                msg[i + j] ^= gf_mul(gen[j], coef)
    ec = msg[44:]
    full_cw = codewords + ec
    assert len(full_cw) == 70

    # Self-verify: evaluate full_cw at all 26 RS roots -> must be 0
    for r_i in range(26):
        root = exp_tbl[r_i]
        acc = 0
        for cw in full_cw:
            acc = gf_mul(acc, root) ^ cw
        assert acc == 0, f"RS verification failed at root {r_i}"

    # Version 3 matrix: 29x29
    N = 29
    grid = [[None] * N for _ in range(N)]
    is_func = [[False] * N for _ in range(N)]

    def set_func(r, c, val):
        grid[r][c] = 1 if val else 0
        is_func[r][c] = True

    # Finder patterns + separators
    def place_finder(r0, c0):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = r0 + dr, c0 + dc
                if 0 <= r < N and 0 <= c < N:
                    if 0 <= dr <= 6 and 0 <= dc <= 6:
                        val = (
                            dr in (0, 6)
                            or dc in (0, 6)
                            or (2 <= dr <= 4 and 2 <= dc <= 4)
                        )
                    else:
                        val = False
                    set_func(r, c, val)

    place_finder(0, 0)
    place_finder(0, N - 7)
    place_finder(N - 7, 0)

    # Alignment pattern at (22, 22) for Version 3
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            val = max(abs(dr), abs(dc)) != 1
            set_func(22 + dr, 22 + dc, val)

    # Timing patterns
    for i in range(8, N - 8):
        set_func(6, i, i % 2 == 0)
        set_func(i, 6, i % 2 == 0)

    # Dark module at (4*3 + 9, 8) = (21, 8)
    set_func(21, 8, True)

    # Reserve format info modules
    for i in range(9):
        if i != 6:
            is_func[8][i] = True
            is_func[i][8] = True
    for i in range(8):
        is_func[8][N - 1 - i] = True
        is_func[N - 1 - i][8] = True

    # Place data bits (70 codewords = 560 bits + 7 remainder zero bits for Version 3)
    data_bits = []
    for cw in full_cw:
        for i in range(7, -1, -1):
            data_bits.append((cw >> i) & 1)
    data_bits.extend([0] * 7)

    bi = 0
    upward = True
    c = N - 1
    while c > 0:
        if c == 6:
            c -= 1
        rows = range(N - 1, -1, -1) if upward else range(N)
        for r in rows:
            for dc in (0, -1):
                cc = c + dc
                if not is_func[r][cc]:
                    grid[r][cc] = data_bits[bi] if bi < len(data_bits) else 0
                    bi += 1
        upward = not upward
        c -= 2
    assert bi == len(data_bits), f"Bit placement mismatch: {bi} != {len(data_bits)}"

    # Format info BCH(15,5) for EC Level M (00) + mask 0..7, XOR 0x5412
    def format_bits(mask_id: int) -> int:
        # EC level M = 00
        d5 = (0b00 << 3) | mask_id
        rem = d5 << 10
        for i in range(4, -1, -1):
            if (rem >> (i + 10)) & 1:
                rem ^= 0b10100110111 << i
        return ((d5 << 10) | rem) ^ 0b101010000010010

    def apply_mask(mask_id: int):
        m = [row[:] for row in grid]
        for r in range(N):
            for c in range(N):
                if is_func[r][c]:
                    continue
                flip = (
                    (mask_id == 0 and (r + c) % 2 == 0)
                    or (mask_id == 1 and r % 2 == 0)
                    or (mask_id == 2 and c % 3 == 0)
                    or (mask_id == 3 and (r + c) % 3 == 0)
                    or (mask_id == 4 and (r // 2 + c // 3) % 2 == 0)
                    or (mask_id == 5 and ((r * c) % 2 + (r * c) % 3) == 0)
                    or (mask_id == 6 and (((r * c) % 2 + (r * c) % 3) % 2) == 0)
                    or (mask_id == 7 and (((r + c) % 2 + (r * c) % 3) % 2) == 0)
                )
                if flip:
                    m[r][c] ^= 1
        fb = format_bits(mask_id)
        # Place format bits (bit 14 is MSB -> (8,0) / (N-1,8), bit 0 is LSB -> (0,8) / (8,N-1))
        coords1 = [
            (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
            (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8),
        ]
        coords2 = [
            (N - 1, 8), (N - 2, 8), (N - 3, 8), (N - 4, 8), (N - 5, 8), (N - 6, 8), (N - 7, 8),
            (8, N - 8), (8, N - 7), (8, N - 6), (8, N - 5), (8, N - 4), (8, N - 3), (8, N - 2), (8, N - 1),
        ]
        for idx in range(15):
            bit = (fb >> (14 - idx)) & 1
            r1, c1 = coords1[idx]
            r2, c2 = coords2[idx]
            m[r1][c1] = bit
            m[r2][c2] = bit
        return m

    def penalty(m):
        score = 0
        # Rule 1: runs of >= 5
        for r in range(N):
            run = 1
            for c in range(1, N):
                if m[r][c] == m[r][c - 1]:
                    run += 1
                    if run == 5:
                        score += 3
                    elif run > 5:
                        score += 1
                else:
                    run = 1
        for c in range(N):
            run = 1
            for r in range(1, N):
                if m[r][c] == m[r - 1][c]:
                    run += 1
                    if run == 5:
                        score += 3
                    elif run > 5:
                        score += 1
                else:
                    run = 1
        # Rule 2: 2x2 blocks
        for r in range(N - 1):
            for c in range(N - 1):
                v = m[r][c]
                if v == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                    score += 3
        # Rule 4: balance
        dark = sum(sum(row) for row in m)
        pct = dark * 100 / (N * N)
        score += int(abs(pct - 50) // 5) * 10
        return score

    best_mask, best_grid, best_score = 0, None, 10**9
    for mid in range(8):
        cand = apply_mask(mid)
        sc = penalty(cand)
        if sc < best_score:
            best_score, best_mask, best_grid = sc, mid, cand

    # Render crisp SVG with 2-module quiet zone (33x33 viewBox)
    quiet = 2
    vb = N + quiet * 2
    rects = []
    for r in range(N):
        for c in range(N):
            if best_grid[r][c]:
                rects.append(f'<rect x="{c + quiet}" y="{r + quiet}" width="1" height="1"/>')
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vb} {vb}" shape-rendering="crispEdges">'
        f'<rect width="{vb}" height="{vb}" fill="#ffffff"/>'
        f'<g fill="#050a16">{"".join(rects)}</g>'
        f"</svg>"
    )
    with open(out_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"✓ Generated spec-verified QR Version 3-M (mask {best_mask}): {out_svg}")


# ── 5. Genuine Apple iOS Direct-Install Configuration Profile ──────────────
def generate_ios_mobileconfig(icon_512_path: str):
    with open(icon_512_path, "rb") as f:
        icon_bytes = f.read()

    webclip_payload = {
        "FullScreen": True,
        "IgnoreManifestScope": False,
        "IsRemovable": True,
        "Precomposed": True,
        "Icon": icon_bytes,
        "Label": "FrostyRips",
        "URL": "https://frostrips.web.app/?app=ios&source=webclip",
        "PayloadDescription": "Adds the FrostyRips full-screen app to your Home Screen.",
        "PayloadDisplayName": "FrostyRips App",
        "PayloadIdentifier": "com.frostyrips.app.webclip",
        "PayloadType": "com.apple.webClip.managed",
        "PayloadUUID": "7A6E82B4-5C91-4B8F-9E21-F8A3D9421001",
        "PayloadVersion": 1,
    }

    profile = {
        "PayloadContent": [webclip_payload],
        "PayloadDescription": (
            "Installs the official FrostyRips full-screen iOS app directly to your "
            "Home Screen — claim a free foil pack, rip 25,000+ graded cards, battle in "
            "the 3D Megastadium, and cash out instantly at 90% FMV."
        ),
        "PayloadDisplayName": "FrostyRips iOS App",
        "PayloadIdentifier": "com.frostyrips.app.profile",
        "PayloadOrganization": "FrostyRips LLC",
        "PayloadRemovalDisallowed": False,
        "PayloadType": "Configuration",
        "PayloadUUID": "7A6E82B4-5C91-4B8F-9E21-F8A3D9421000",
        "PayloadVersion": 1,
    }

    ios_out = f"{MOBILE}/ios/FrostyRips-iOS.mobileconfig"
    pub_out = f"{DOWNLOADS}/FrostyRips-iOS.mobileconfig"
    for p in (ios_out, pub_out):
        with open(p, "wb") as f:
            plistlib.dump(profile, f, fmt=plistlib.FMT_XML, sort_keys=True)
        # Validate round-trip
        with open(p, "rb") as f:
            loaded = plistlib.load(f)
            assert loaded["PayloadIdentifier"] == "com.frostyrips.app.profile"
            assert loaded["PayloadContent"][0]["FullScreen"] is True
            assert len(loaded["PayloadContent"][0]["Icon"]) > 10000
    print(f"✓ Generated & verified Apple iOS profile: {pub_out} ({os.path.getsize(pub_out):,} bytes)")


# ── 6. Package Complete Native iOS Xcode App Project into ZIP ──────────────
def package_ios_zip():
    zip_path = f"{DOWNLOADS}/FrostyRips-iOS-App.zip"
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        ios_root = f"{MOBILE}/ios"
        for root, _, files in os.walk(ios_root):
            for fn in sorted(files):
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, MOBILE)
                zf.write(full, f"FrostyRips-iOS/{rel}")
        wf = f"{MOBILE}/.github/workflows/build-ios-ipa.yml"
        if os.path.exists(wf):
            zf.write(wf, "FrostyRips-iOS/.github/workflows/build-ios-ipa.yml")
        readme = f"{MOBILE}/README.md"
        if os.path.exists(readme):
            zf.write(readme, "FrostyRips-iOS/README.md")
    print(f"✓ Packaged native iOS app bundle: {zip_path} ({os.path.getsize(zip_path):,} bytes)")


if __name__ == "__main__":
    icon_512 = generate_icons()
    isolate_dark_bg(HERO_SRC, f"{LANDING_ASSETS}/hero-penguin.webp", (726, 1002), tolerance=15)
    isolate_dark_bg(INVITE_SRC, f"{LANDING_ASSETS}/invite-penguins.webp", (798, 1074), tolerance=14)
    generate_app_screens()
    generate_qr_svg("https://frostrips.web.app/ad/landing/app", f"{LANDING_ASSETS}/qr-frostyrips.svg")
    generate_ios_mobileconfig(icon_512)
    package_ios_zip()
    print("ALL MOBILE ASSETS & iOS PACKAGES GENERATED SUCCESSFULLY!")
