import os
import sys
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

STORIES_TMP_DIR = BASE_DIR / "temp_stories"
STORIES_TMP_DIR.mkdir(parents=True, exist_ok=True)


def format_image_for_story(image_path: Path, title: str = "", category: str = "") -> Path:
    """
    Formats any square or standard photo into a high-res 1080x1920 vertical Story format
    with blurred background, card framing, and clear sales CTA.
    """
    orig_img = Image.open(image_path).convert("RGBA")
    W, H = 1080, 1920

    # 1. Background: Blurred version of the product
    bg = orig_img.resize((W, H), Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=25))
    dark = Image.new("RGBA", (W, H), (10, 15, 30, 170))
    bg_final = Image.alpha_composite(bg, dark)

    # 2. Card: Centered product
    card_w = 920
    aspect = orig_img.height / orig_img.width
    card_h = int(card_w * aspect)
    if card_h > 1050:
        card_h = 1050
        card_w = int(card_h / aspect)

    fg_resized = orig_img.resize((card_w, card_h), Image.Resampling.LANCZOS)
    
    pos_x = (W - card_w) // 2
    pos_y = 420

    # White border / shadow for product
    border_img = Image.new("RGBA", (card_w + 24, card_h + 24), (255, 255, 255, 255))
    bg_final.paste(border_img, (pos_x - 12, pos_y - 12), border_img)
    bg_final.paste(fg_resized, (pos_x, pos_y), fg_resized)

    # 3. Graphics & Badges
    draw = ImageDraw.Draw(bg_final)
    try:
        font_brand = ImageFont.truetype("arialbd.ttf", 44)
        font_title = ImageFont.truetype("arialbd.ttf", 46)
        font_badge = ImageFont.truetype("arialbd.ttf", 36)
        font_cta = ImageFont.truetype("arialbd.ttf", 38)
    except:
        font_brand = font_title = font_badge = font_cta = ImageFont.load_default()

    # Top Brand Pill
    draw.rounded_rectangle([(140, 120), (940, 220)], radius=30, fill=(255, 102, 0, 240))
    draw.text((W // 2, 170), "🔥 AHORA CUOTAS 🔥", fill="white", font=font_brand, anchor="mm")

    # Title Banner
    draw.rounded_rectangle([(80, 260), (1000, 360)], radius=25, fill=(15, 23, 42, 230))
    clean_t = title if title else "¡OFERTA DISPONIBLE HOY!"
    draw.text((W // 2, 310), clean_t.upper(), fill="#FFD700", font=font_title, anchor="mm")

    # Lower Badges
    b_y = pos_y + card_h + 40
    draw.rounded_rectangle([(100, b_y), (980, b_y + 80)], radius=20, fill=(255, 255, 255, 240))
    draw.text((W // 2, b_y + 40), "✔️ SOLO CON DNI + 1 SERVICIO", fill="#0F172A", font=font_badge, anchor="mm")

    b_y2 = b_y + 100
    draw.rounded_rectangle([(100, b_y2), (980, b_y2 + 80)], radius=20, fill=(255, 255, 255, 240))
    draw.text((W // 2, b_y2 + 40), "💳 CUOTAS POR DÍA, SEMANA O MES", fill="#0F172A", font=font_badge, anchor="mm")

    # Bottom CTA Box (Direct link or reply indicator)
    draw.rounded_rectangle([(80, 1700), (1000, 1830)], radius=35, fill=(0, 180, 80, 240))
    draw.text((W // 2, 1765), "💬 ¡RESPONDÉ ESTA HISTORIA O ESCRIBINOS!", fill="white", font=font_cta, anchor="mm")

    out_path = STORIES_TMP_DIR / f"story_{image_path.stem}.jpg"
    bg_final.convert("RGB").save(out_path, quality=95)
    return out_path


def publish_random_story(cl=None):
    """
    Picks an in-stock product, formats it into a Story, and uploads to Instagram.
    """
    from instagram_publisher import get_client, load_catalog
    
    catalog = load_catalog()
    posts = catalog.get("posts", [])
    
    if not posts:
        print("❌ No hay posts en el catálogo.")
        return None

    # Pick a random pending or in-stock post
    chosen = random.choice(posts)
    img_path = Path(chosen["absolute_path"])
    
    if not img_path.exists():
        print(f"⚠️ Imagen no encontrada: {img_path}")
        return None

    if cl is None:
        cl = get_client()

    print(f"\n📸 Generando y subiendo Story de: {chosen['title']} ({img_path.name})...")
    story_img = format_image_for_story(img_path, title=chosen["title"], category=chosen.get("category", ""))
    
    try:
        res = cl.photo_upload_to_story(path=str(story_img))
        print(f"🎉 ¡Historia publicada con éxito en Instagram!")
        return res
    except Exception as e:
        print(f"❌ Error al subir Story: {e}")
        return None


if __name__ == "__main__":
    publish_random_story()
