import os
import sys
import json
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from gtts import gTTS
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

OUTPUT_DIR = BASE_DIR / "reels_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def get_gemini_client():
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("tu_"):
        print("❌ Error: Debes configurar GEMINI_API_KEY en tu archivo .env")
        sys.exit(1)
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_reel_script_with_ai(image_path: Path, product_title: str, category: str):
    """
    Uses Gemini 2.5 Flash with Vision to analyze the product and create a high-impact sales script.
    """
    client = get_gemini_client()
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    mime_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

    prompt = f"""Analiza esta imagen de producto para venta en Instagram Reels de la marca 'Ahora Cuotas'.
El producto pertenece a la categoría '{category}' con nombre tentativo '{product_title}'.

Propuesta de venta:
- Financiación solo con DNI + 1 Servicio
- Pagos por día, semana o mes
- Entregas en 24hs a domicilio en Santa Fe y alrededores
- CTA: Escribir al WhatsApp del enlace de la biografía

Devuelve un JSON estrictamente con esta estructura:
{{
    "hook_title": "Título corto y llamativo en mayúsculas (máx 4 palabras)",
    "product_name": "Nombre claro del producto",
    "badge_1": "Beneficio 1 (ej: Solo con tu DNI)",
    "badge_2": "Beneficio 2 (ej: Cuotas por día o semana)",
    "badge_3": "Beneficio 3 (ej: Entrega en 24hs)",
    "voice_script": "Guión corto y enérgico para locución en off en español argentino de 6 a 8 segundos. Debe sonar como vendedor entusiasta que invita a consultar al WhatsApp del perfil."
}}
"""

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            {"inline_data": {"mime_type": mime_type, "data": image_bytes}},
            prompt
        ]
    )

    text_resp = response.text.strip()
    if text_resp.startswith("```json"):
        text_resp = text_resp[7:]
    if text_resp.endswith("```"):
        text_resp = text_resp[:-3]
    text_resp = text_resp.strip()

    try:
        data = json.loads(text_resp)
        return data
    except Exception as e:
        print(f"⚠️ Error parseando respuesta JSON de Gemini: {e}. Usando fallback.")
        return {
            "hook_title": f"¡LLEVATELO HOY MISMO!",
            "product_name": product_title,
            "badge_1": "Solo con tu DNI",
            "badge_2": "Cuotas por día o semana",
            "badge_3": "Entrega en 24 horas",
            "voice_script": f"¡Mirá lo que es este {product_title}! Llevátelo hoy financiado solo con tu DNI y pagá en cuotas como más te convenga. Envíos en 24 horas. ¡Escribinos ya al WhatsApp de la bio!"
        }


def create_voiceover(text: str, output_audio_path: Path):
    """
    Generates voiceover audio using Google TTS with clean pronunciation.
    """
    # Clean common abbreviations so TTS speaks naturally in Spanish
    clean_text = text.replace("24hs", "24 horas").replace("24 hs", "24 horas")
    clean_text = clean_text.replace("DNI", "de ene i")
    clean_text = clean_text.replace("CTA", "").replace("link", "enlace")
    
    tts = gTTS(text=clean_text, lang='es', tld='com.ar')
    tts.save(str(output_audio_path))
    return output_audio_path


def render_reel_video(image_path: Path, script_data: dict, audio_path: Path, output_video_path: Path):
    """
    Creates a 1080x1920 9:16 vertical video with smooth animation, overlay badges and voiceover.
    """
    from moviepy import AudioFileClip, VideoClip

    audio_clip = AudioFileClip(str(audio_path))
    duration = max(audio_clip.duration + 0.8, 6.0)

    # Base image loaded via PIL
    orig_img = Image.open(image_path).convert("RGBA")
    
    # 1080x1920 Canvas
    W, H = 1080, 1920

    # Background: blurred version of the product image
    bg = orig_img.resize((W, H), Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
    # Darken background
    dark_overlay = Image.new("RGBA", (W, H), (15, 20, 35, 180))
    bg_final = Image.alpha_composite(bg, dark_overlay)

    # Foreground product image
    target_card_w = 880
    aspect = orig_img.height / orig_img.width
    target_card_h = int(target_card_w * aspect)
    if target_card_h > 880:
        target_card_h = 880
        target_card_w = int(target_card_h / aspect)
    
    fg_resized = orig_img.resize((target_card_w, target_card_h), Image.Resampling.LANCZOS)

    # Create static overlay graphics (Header, badges, footer)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Try to load font or default
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 52)
        font_subtitle = ImageFont.truetype("arialbd.ttf", 40)
        font_badge = ImageFont.truetype("arialbd.ttf", 36)
        font_brand = ImageFont.truetype("arialbd.ttf", 44)
    except:
        font_title = font_subtitle = font_badge = font_brand = ImageFont.load_default()

    # Top Brand Header
    draw.rounded_rectangle([(100, 80), (980, 180)], radius=30, fill=(255, 102, 0, 240))
    draw.text((W // 2, 130), "⭐ AHORA CUOTAS ⭐", fill="white", font=font_brand, anchor="mm")

    # Hook Title
    draw.rounded_rectangle([(80, 220), (1000, 340)], radius=25, fill=(10, 30, 70, 230))
    draw.text((W // 2, 280), script_data.get("hook_title", "¡OFERTA IMPERDIBLE!"), fill="#FFD700", font=font_title, anchor="mm")

    # Product Name
    draw.text((W // 2, 390), script_data.get("product_name", ""), fill="white", font=font_subtitle, anchor="mm")

    # Badges below product
    badges = [
        script_data.get("badge_1", "✔️ Solo con tu DNI"),
        script_data.get("badge_2", "💳 Cuotas por día o semana"),
        script_data.get("badge_3", "🚀 Entrega en 24 horas")
    ]
    
    badge_start_y = 1380
    for i, b_text in enumerate(badges):
        by = badge_start_y + (i * 105)
        draw.rounded_rectangle([(100, by), (980, by + 80)], radius=20, fill=(255, 255, 255, 230))
        draw.text((W // 2, by + 40), b_text, fill="#0F172A", font=font_badge, anchor="mm")

    # Bottom CTA Banner
    draw.rounded_rectangle([(80, 1720), (1000, 1840)], radius=30, fill=(0, 180, 80, 240))
    draw.text((W // 2, 1780), "📲 ¡CONSULTÁ AL WHATSAPP EN LA BIO!", fill="white", font=font_subtitle, anchor="mm")

    # Product center position
    fg_center_x = W // 2
    fg_center_y = 860

    # Frame generator function with Ken Burns slow zoom
    def make_frame(t):
        # Zoom factor from 1.0 to 1.08 over duration
        zoom = 1.0 + (0.08 * (t / duration))
        curr_w = int(target_card_w * zoom)
        curr_h = int(target_card_h * zoom)

        zoomed_fg = fg_resized.resize((curr_w, curr_h), Image.Resampling.BILINEAR)

        # Composite frame
        frame = bg_final.copy()
        pos_x = fg_center_x - (curr_w // 2)
        pos_y = fg_center_y - (curr_h // 2)

        # Draw card background shadow/white backing
        card_backing = Image.new("RGBA", (curr_w + 30, curr_h + 30), (255, 255, 255, 255))
        frame.paste(card_backing, (pos_x - 15, pos_y - 15), card_backing)
        frame.paste(zoomed_fg, (pos_x, pos_y), zoomed_fg)

        # Paste overlays
        frame.paste(overlay, (0, 0), overlay)

        return np.array(frame.convert("RGB"))

    video_clip = VideoClip(make_frame, duration=duration)
    video_clip = video_clip.with_audio(audio_clip)

    print(f"🎬 Renderizando Reel vertical MP4 (1080x1920, {duration:.1f}s)...")
    video_clip.write_videofile(
        str(output_video_path),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        logger=None
    )
    print(f"✅ Reel generado exitosamente en: {output_video_path}")
    return output_video_path


def generate_reel_for_product(image_path: Path, product_title: str = "", category: str = ""):
    """
    Full pipeline: AI analysis -> Voiceover -> Video Render
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"No se encontró la imagen: {image_path}")

    if not product_title:
        product_title = image_path.stem.replace("_", " ").title()

    print("\n" + "="*60)
    print(f" 🤖 GENERANDO REEL CON IA PARA: {product_title}")
    print("="*60)

    # 1. AI Scripting
    print("🧠 1/3 Analizando imagen con Google Gemini...")
    script_data = generate_reel_script_with_ai(image_path, product_title, category)
    print(f"   Título : {script_data.get('hook_title')}")
    print(f"   Guión  : \"{script_data.get('voice_script')}\"")

    # 2. Voiceover
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
        tmp_audio_path = Path(tmp_audio.name)
    print("🎙️ 2/3 Generando locución con Google TTS...")
    create_voiceover(script_data.get("voice_script"), tmp_audio_path)

    # 3. Video Composition
    output_video_path = OUTPUT_DIR / f"reel_{image_path.stem}.mp4"
    print("🎥 3/3 Componiendo y renderizando video en 9:16...")
    render_reel_video(image_path, script_data, tmp_audio_path, output_video_path)

    # Cleanup temp audio
    try:
        tmp_audio_path.unlink(missing_ok=True)
    except:
        pass

    return output_video_path, script_data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate Instagram Reels with Google AI")
    parser.add_argument("--image", type=str, help="Ruta de la imagen del producto")
    parser.add_argument("--test", action="store_true", help="Genera un Reel de prueba con un celular")
    args = parser.parse_args()

    if args.test:
        test_img = BASE_DIR / "Assets" / "- INFORMATIVAS FEED-20260901T122245Z-1-001" / "- INFORMATIVAS FEED" / "placas para ig" / "placa celulares.jpg"
        generate_reel_for_product(test_img, product_title="Celulares Multimarca", category="Celulares y Tablet")
    elif args.image:
        generate_reel_for_product(Path(args.image))
    else:
        print("💡 Uso: python ai_reel_generator.py --test")
        print("💡 O:    python ai_reel_generator.py --image 'ruta/a/la/foto.jpg'")
