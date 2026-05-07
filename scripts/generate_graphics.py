"""
Generuje 9 grafik per produkt:
  0. Miniaturka (Photoroom białe tło) + ikony certyfikatów (PIL)
  1. Hero shot (Photoroom białe tło)
  2-4. Lifestyle x3 (Photoroom background.prompt)
  5. AI scene (Fal.ai Flux 1.1 Pro)
  6. Etykieta upscale (Photoroom)
  7. Klimatyczna (Photoroom background.prompt)
  8. Premium separator (złota linia, wygenerowany PIL)

Użycie:
  python generate_graphics.py --session <uuid> \
    --producer "Plakias" \
    --certs "bio,pdо" \
    --fal-prompt "Ancient olive grove..." \
    --lifestyle1 "Mediterranean olive grove, golden hour..." \
    --lifestyle2 "rustic kitchen, marble surface, warm light..." \
    --lifestyle3 "Mediterranean dinner table, friends, lifestyle..." \
    --climate "Ancient olive tree bark texture, Crete, macro..."
"""
import argparse, os, sys, io, json, time, requests
from pathlib import Path
from PIL import Image, ImageDraw

PHOTOROOM_KEY = os.environ.get("PHOTOROOM_API_KEY", "")
FAL_KEY       = os.environ.get("FAL_API_KEY", "")
PHOTOROOM_URL = "https://image-api.photoroom.com/v2/edit"

CERT_ICONS_DIR = Path(__file__).parent.parent / "assets" / "cert_icons"


def photoroom_white(image_bytes: bytes, size: int = 2000, shadow: bool = True) -> bytes:
    params = {
        "background.color": "white",
        "outputSize": f"{size}x{size}",
        "export.format": "jpg",
        "export.quality": "95",
    }
    if shadow:
        params["shadow.mode"] = "ai.soft"
        params["lighting.mode"] = "ai.auto"
    r = requests.post(
        PHOTOROOM_URL,
        headers={"x-api-key": PHOTOROOM_KEY},
        files={"imageFile": ("photo.jpg", image_bytes, "image/jpeg")},
        data=params,
        timeout=60,
    )
    r.raise_for_status()
    return r.content


def photoroom_lifestyle(image_bytes: bytes, bg_prompt: str, size: int = 2000) -> bytes:
    params = {
        "background.prompt": bg_prompt,
        "outputSize": f"{size}x{size}",
        "export.format": "jpg",
        "export.quality": "92",
    }
    r = requests.post(
        PHOTOROOM_URL,
        headers={"x-api-key": PHOTOROOM_KEY},
        files={"imageFile": ("photo.jpg", image_bytes, "image/jpeg")},
        data=params,
        timeout=60,
    )
    r.raise_for_status()
    return r.content


def photoroom_upscale(image_bytes: bytes) -> bytes:
    params = {
        "background.color": "white",
        "upscale.mode": "x4",
        "export.format": "jpg",
        "export.quality": "95",
    }
    r = requests.post(
        PHOTOROOM_URL,
        headers={"x-api-key": PHOTOROOM_KEY},
        files={"imageFile": ("photo.jpg", image_bytes, "image/jpeg")},
        data=params,
        timeout=90,
    )
    r.raise_for_status()
    return r.content


def fal_generate(prompt: str) -> bytes:
    import fal_client
    result = fal_client.run(
        "fal-ai/flux-pro/v1.1",
        arguments={"prompt": prompt, "image_size": "square_hd", "num_images": 1},
    )
    url = result["images"][0]["url"]
    return requests.get(url, timeout=60).content


def add_cert_icons(image_bytes: bytes, certs: list[str], icon_size: int = 180) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    w, h = img.size
    margin = 20
    x = w - margin
    y = h - margin

    for cert in reversed(certs):
        icon_path = CERT_ICONS_DIR / f"{cert.lower().replace(' ', '_')}.png"
        if not icon_path.exists():
            print(f"  [WARN] Brak ikony: {icon_path}")
            continue
        icon = Image.open(icon_path).convert("RGBA")
        icon = icon.resize((icon_size, icon_size), Image.LANCZOS)
        x -= icon_size
        img.paste(icon, (x, y - icon_size), mask=icon)
        x -= margin // 2

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def generate_separator(width: int = 1500, height: int = 4) -> bytes:
    img = Image.new("RGB", (width, height), (201, 168, 76))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--producer", default="")
    ap.add_argument("--certs", default="", help="Comma-separated: bio,pdo,pgi")
    ap.add_argument("--fal-prompt", default="")
    ap.add_argument("--lifestyle1", default="Mediterranean landscape, golden hour, nature")
    ap.add_argument("--lifestyle2", default="rustic kitchen, marble surface, warm light")
    ap.add_argument("--lifestyle3", default="Mediterranean dinner table, lifestyle, friends")
    ap.add_argument("--climate", default="Mediterranean nature, product atmosphere")
    ap.add_argument("--raw-photo", help="Ścieżka do surowego zdjęcia (jeśli brak MCP)")
    ap.add_argument("--out-dir", default="./output")
    args = ap.parse_args()

    out = Path(args.out_dir) / args.session / "processed"
    out.mkdir(parents=True, exist_ok=True)

    certs = [c.strip() for c in args.certs.split(",") if c.strip()]

    # Wczytaj surowe zdjęcie
    if args.raw_photo:
        raw = Path(args.raw_photo).read_bytes()
    else:
        print("Podaj --raw-photo lub pobierz z MCP")
        sys.exit(1)

    print("Generuję grafiki...")

    # 0. Miniaturka (białe tło) + ikony certyfikatów
    print("  [0] Miniaturka...")
    thumb = photoroom_white(raw, size=2000, shadow=True)
    if certs:
        thumb = add_cert_icons(thumb, certs)
    (out / "0_miniaturka.jpg").write_bytes(thumb)

    # 1. Hero shot
    print("  [1] Hero shot...")
    time.sleep(1)
    hero = photoroom_white(raw, size=2000, shadow=True)
    (out / "1_hero.jpg").write_bytes(hero)

    # 2-4. Lifestyle
    for i, prompt in enumerate([args.lifestyle1, args.lifestyle2, args.lifestyle3], 2):
        print(f"  [{i}] Lifestyle {i-1}...")
        time.sleep(1)
        ls = photoroom_lifestyle(raw, prompt)
        (out / f"{i}_lifestyle{i-1}.jpg").write_bytes(ls)

    # 5. Fal.ai AI scene
    if args.fal_prompt:
        print("  [5] AI scene (Fal.ai)...")
        ai_img = fal_generate(args.fal_prompt)
        (out / "5_ai_scene.jpg").write_bytes(ai_img)
    else:
        print("  [5] Pomiń AI scene (brak --fal-prompt)")

    # 6. Etykieta upscale
    print("  [6] Etykieta upscale...")
    time.sleep(1)
    label_up = photoroom_upscale(raw)
    (out / "6_etykieta.jpg").write_bytes(label_up)

    # 7. Klimatyczna
    print("  [7] Klimatyczna...")
    time.sleep(1)
    climate = photoroom_lifestyle(raw, args.climate)
    (out / "7_klimatyczna.jpg").write_bytes(climate)

    # 8. Premium separator
    print("  [8] Separator...")
    sep = generate_separator()
    (out / "8_separator.jpg").write_bytes(sep)

    print(f"\nGotowe! Grafiki w: {out}")
    files = sorted(out.glob("*.jpg"))
    for f in files:
        print(f"  {f.name} ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
