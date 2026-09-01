import os
import sys
import json
import re
import time
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "Assets"
CATALOG_FILE = BASE_DIR / "posts.json"

load_dotenv(BASE_DIR / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def clean_category_name(folder_name: str) -> str:
    # Remove leading hyphens/symbols
    name = re.sub(r"^[\s\-_]+", "", folder_name)
    # Remove timestamp hashes like -20260901T122245Z-1-001
    name = re.sub(r"-\d{8}T\d{6}Z.*", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def clean_title_from_filename(filename: str) -> str:
    name = Path(filename).stem
    name = re.sub(r"-\d{8}T\d{6}Z.*", "", name)
    name = re.sub(r"\(\d+\)", "", name)
    name = name.replace("_", " ").replace("-", " ")
    name = " ".join(name.split()).title()
    return name


def generate_caption_with_gemini(image_path: Path, product_title: str, category: str) -> str:
    """
    Uses Gemini Vision to read and see the actual image, generating accurate sales copy.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("tu_"):
        return generate_fallback_caption(product_title, category)

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        mime_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

        prompt = f"""Observa atentamente esta imagen de producto para venta en Instagram de 'Ahora Cuotas'.
Categoría sugerida: '{category}', Archivo: '{product_title}'.

INSTRUCCIONES ESTRICTAS:
1. Mira QUÉ producto aparece exactamente en la imagen (ej: Horno freidor Yelmo, Celular Samsung, Moto 110, etc.) y lee cualquier texto que contenga.
2. NO hables de celulares si la foto muestra un producto de cocina, belleza, moto o muebles.
3. El post debe tener tono vendedor directo argentino para Santa Fe y zona.
4. Condiciones: Solo con DNI + 1 Servicio | Cuotas por día, semana o mes | Entrega en 24hs | WhatsApp en el enlace de la bio.
5. Devuelve ÚNICAMENTE el texto final listo para publicar en Instagram, con emojis y hashtags. NO incluyas introducciones ni comentarios adicionales."""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                {"inline_data": {"mime_type": mime_type, "data": image_bytes}},
                prompt
            ]
        )
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Error al consultar Gemini para {image_path.name}: {e}. Usando fallback.")
        return generate_fallback_caption(product_title, category)


def generate_fallback_caption(product_title: str, category: str) -> str:
    cat_lower = category.lower()
    
    if any(k in cat_lower for k in ["moto"]):
        emoji, header, tag = "🛵", "¡SUBITE A TU MOTO 0KM EN CUOTAS!", "#MotosEnCuotas #Motos0km #SantaFeMotos #MotoConDNI"
    elif any(k in cat_lower for k in ["celular", "iphone", "tablet"]):
        emoji, header, tag = "📱", "¡ESTRENÁ TU CELULAR HOY MISMO!", "#CelularesEnCuotas #VentaCelulares #SantaFe #FinanciacionDNI"
    elif any(k in cat_lower for k in ["cocina", "heladera", "horno"]):
        emoji, header, tag = "🍳❄️", "¡RENOVÁ TU COCINA Y EQUIPAMIENTO DEL HOGAR!", "#Cocinas #Heladeras #ElectroHogar #SantaFe"
    elif any(k in cat_lower for k in ["audio", "parlante"]):
        emoji, header, tag = "🔊", "¡MÁXIMA POTENCIA Y SONIDO PARA TU CASA!", "#Audio #ParlantesBluetooth #SonidoPotente"
    elif any(k in cat_lower for k in ["silla gamer", "gamer"]):
        emoji, header, tag = "🎮", "¡MEJORÁ TU SETUP CON SILLAS GAMER ERGONÓMICAS!", "#SillaGamer #SetupGamer #GamerArgentina"
    elif any(k in cat_lower for k in ["colchon", "sommier", "acolchado"]):
        emoji, header, tag = "🛏️", "¡EL MEJOR DESCANSO PARA VOS Y TU FAMILIA!", "#Colchones #Sommier #Descanso #AhoraCuotas"
    elif any(k in cat_lower for k in ["mueble", "pino", "melamina"]):
        emoji, header, tag = "🛋️", "¡MUEBLES DE PRIMERA CALIDAD PARA TU CASA!", "#Muebles #Hogar #AhoraCuotas #SantaFe"
    elif any(k in cat_lower for k in ["bazar", "termo", "olla", "tramontina"]):
        emoji, header, tag = "✨", "¡LO MEJOR EN BAZAR, OLLAS Y ARTÍCULOS DE COCINA!", "#Bazar #Ollas #Tramontina #Cocina"
    elif any(k in cat_lower for k in ["calefaccion", "calefactor", "estufa"]):
        emoji, header, tag = "🌡️", "¡CALEFACCIÓN Y CONFORT PARA TU HOGAR!", "#Calefaccion #Estufas #HogarCalido #SantaFe"
    elif any(k in cat_lower for k in ["limpieza", "herramienta", "aspiradora", "hidro"]):
        emoji, header, tag = "🛠️🧹", "¡EQUIPOS DE LIMPIEZA Y HERRAMIENTAS EN CUOTAS!", "#Herramientas #Limpieza #Aspiradoras #AhoraCuotas"
    elif any(k in cat_lower for k in ["belleza", "spa", "secador", "planchita"]):
        emoji, header, tag = "💇‍♀️", "¡CUIDADO PERSONAL Y BELLEZA AL MEJOR PRECIO!", "#Belleza #CuidadoPersonal #AhoraCuotas"
    elif any(k in cat_lower for k in ["comercial", "negocio"]):
        emoji, header, tag = "🏪", "¡EQUIPÁ TU COMERCIO O NEGOCIO HOY MISMO!", "#EquipamientoComercial #Gastronomia #AhoraCuotas"
    else:
        emoji, header, tag = "📦", f"¡LLEVATE TU {product_title.upper()} EN CUOTAS!", "#AhoraCuotas #VentasSantaFe #FinanciacionDNI"

    return f"""{emoji} {header}
📍 {product_title}

Comprá fácil, rápido y sin trámites complicados.

✔️ Solo con tu DNI + 1 Servicio
✔️ Elegí pagar por DÍA, SEMANA o MES
✔️ Entrega inmediata en 24 horas en tu domicilio
✔️ Envíos gratis en Santa Fe Capital, Santo Tomé y alrededores

🚚 Rutas programadas a Esperanza, Rafaela, Franck, San Carlos y más.

💬 ¡Escribinos ahora al WhatsApp del enlace en la bio y consultá disponibilidad!

{tag} #AhoraCuotas #SantaFe #VentaDirecta"""


def sync_stock_catalog(use_ai=False, dry_run=False):
    """
    Scans Assets directory:
    - ONLY files directly in root of each category.
    - Accurately names categories.
    - If use_ai=True, uses Gemini Vision for pending posts.
    """
    existing_posts_by_rel_path = {}
    existing_posts_by_filename = {}
    if CATALOG_FILE.exists():
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for p in data.get("posts", []):
                    if p.get("relative_path"):
                        existing_posts_by_rel_path[p["relative_path"]] = p
                    if p.get("filename"):
                        existing_posts_by_filename[p["filename"]] = p
        except Exception as e:
            print(f"⚠️ No se pudo leer {CATALOG_FILE}: {e}")

    scanned_posts = []
    seen_paths = set()

    for category_dir in sorted(ASSETS_DIR.iterdir()):
        if not category_dir.is_dir():
            continue

        clean_cat = clean_category_name(category_dir.name)

        # Look for the inner category directory
        inner_candidates = [d for d in category_dir.iterdir() if d.is_dir()]
        target_dir = inner_candidates[0] if inner_candidates else category_dir

        for file in sorted(target_dir.iterdir()):
            if not file.is_file():
                continue

            ext = file.suffix.lower()
            if ext not in [".jpg", ".jpeg", ".png", ".mp4"]:
                continue

            rel_path = str(file.relative_to(BASE_DIR))
            if rel_path in seen_paths:
                continue
            seen_paths.add(rel_path)

            media_type = "video" if ext == ".mp4" else "photo"
            clean_title = clean_title_from_filename(file.name)

            # Check if this post was already registered and published
            prev = existing_posts_by_rel_path.get(rel_path) or existing_posts_by_filename.get(file.name)
            
            if prev and prev.get("status") == "published":
                post_data = {
                    "id": prev.get("id", f"post_{len(scanned_posts) + 1:03d}"),
                    "filename": file.name,
                    "relative_path": rel_path,
                    "absolute_path": str(file.resolve()),
                    "media_type": media_type,
                    "category": clean_cat,
                    "title": prev.get("title", clean_title),
                    "caption": prev.get("caption"),
                    "status": "published",
                    "published_at": prev.get("published_at"),
                    "media_id": prev.get("media_id"),
                    "error_message": None
                }
            else:
                # Re-generate caption with accurate category fallback
                caption = generate_fallback_caption(clean_title, clean_cat)
                post_data = {
                    "id": f"post_{len(scanned_posts) + 1:03d}",
                    "filename": file.name,
                    "relative_path": rel_path,
                    "absolute_path": str(file.resolve()),
                    "media_type": media_type,
                    "category": clean_cat,
                    "title": clean_title,
                    "caption": caption,
                    "status": "pending",
                    "published_at": None,
                    "media_id": None,
                    "error_message": None
                }

            scanned_posts.append(post_data)

    # Re-index IDs cleanly
    for i, p in enumerate(scanned_posts):
        p["id"] = f"post_{i + 1:03d}"

    published_count = len([p for p in scanned_posts if p["status"] == "published"])
    pending_count = len([p for p in scanned_posts if p["status"] == "pending"])

    print("\n" + "="*60)
    print(f" 📦 CATÁLOGO CORREGIDO Y SINCRONIZADO")
    print("="*60)
    print(f" Total productos en stock real : {len(scanned_posts)}")
    print(f" ✅ Ya publicados              : {published_count}")
    print(f" ⏳ Pendientes corregidos      : {pending_count}")
    print("="*60 + "\n")

    if not dry_run:
        with open(CATALOG_FILE, "w", encoding="utf-8") as f:
            json.dump({"posts": scanned_posts}, f, ensure_ascii=False, indent=2)
        print(f"✅ Archivo {CATALOG_FILE} actualizado con categorías y descripciones correctas.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync catalog with corrected categories")
    parser.add_argument("--dry-run", action="store_true", help="Scan without saving posts.json")
    args = parser.parse_args()

    sync_stock_catalog(dry_run=args.dry_run)
