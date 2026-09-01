import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def group_pending_posts_by_category():
    from instagram_publisher import load_catalog
    catalog = load_catalog()
    posts = catalog.get("posts", [])
    
    categories = {}
    for p in posts:
        if p.get("status") == "pending":
            cat = p.get("category", "Varios")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(p)
    return categories


def publish_category_carousel(target_category: str = None, max_items: int = 5, cl=None, dry_run=False):
    from instagram_publisher import get_client, load_catalog, save_catalog
    from catalog_builder import generate_caption_with_gemini

    grouped = group_pending_posts_by_category()
    
    # Filter categories that have at least 2 items
    eligible = {k: v for k, v in grouped.items() if len(v) >= 2}
    
    if not eligible:
        print("✨ No hay suficientes productos pendientes para armar un carrusel (mínimo 2 por rubro).")
        return False

    if target_category and target_category in eligible:
        selected_cat = target_category
    else:
        # Pick category with most items
        selected_cat = max(eligible.keys(), key=lambda k: len(eligible[k]))

    items = eligible[selected_cat][:max_items]
    image_paths = [Path(p["absolute_path"]) for p in items if Path(p["absolute_path"]).exists()]

    if len(image_paths) < 2:
        print(f"⚠️ Menos de 2 imágenes válidas para la categoría {selected_cat}.")
        return False

    print("\n" + "="*60)
    print(f" 📑 PUBLICANDO CARRUSEL DE {len(image_paths)} PRODUCTOS: {selected_cat.upper()}")
    print("="*60)
    for p in items:
        print(f"  📸 [{p['id']}] {p['title']} ({p['filename']})")

    # Generate multi-product sales copy
    first_img = image_paths[0]
    caption = f"""🔥 ¡CATÁLOGO EN CUOTAS: {selected_cat.upper()}! 🚀
Deslizá para ver los modelos disponibles en stock.

✔️ Llevate cualquiera solo con tu DNI + 1 Servicio
✔️ Planes en cuotas por DÍA, SEMANA o MES
✔️ Entregas garantizadas en 24 horas a domicilio
✔️ Envíos gratis en Santa Fe Capital, Santo Tomé y zonas diarias

📦 Rutas programadas en toda la región.

📲 ¿Te gustó algún modelo? Tocá el link de nuestra bio y consultanos por WhatsApp para congelar precio y cuota hoy.

#AhoraCuotas #SantaFe #VentaDirecta #FinanciacionDNI #Cuotas #{selected_cat.replace(' ', '')}"""

    if dry_run:
        print("\n🚀 [DRY RUN] Carrusel listo para publicar:")
        print(f"   Imágenes: {[p.name for p in image_paths]}")
        print(f"   Copy:\n{caption}")
        return True

    if cl is None:
        cl = get_client()

    print("\n📤 Subiendo carrusel a Instagram...")
    try:
        media = cl.album_upload(
            paths=[str(p) for p in image_paths],
            caption=caption
        )
        media_dict = media.dict() if hasattr(media, "dict") else (media.model_dump() if hasattr(media, "model_dump") else media.__dict__)
        media_pk = media_dict.get("pk") or media_dict.get("id")

        # Update posts in catalog
        catalog = load_catalog()
        now_str = datetime.now().isoformat()
        item_ids = {p["id"] for p in items}

        for p in catalog.get("posts", []):
            if p["id"] in item_ids:
                p["status"] = "published"
                p["published_at"] = now_str
                p["media_id"] = str(media_pk)
                p["error_message"] = None

        save_catalog(catalog)
        print(f"🎉 ¡Carrusel publicado exitosamente! Media ID: {media_pk}")
        return True
    except Exception as e:
        print(f"❌ Error al publicar carrusel: {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Publish Instagram multi-product carousel")
    parser.add_argument("--category", type=str, help="Categoría específica para el carrusel")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin publicar")
    parser.add_argument("--max", type=int, default=5, help="Máximo de fotos en el carrusel")
    args = parser.parse_args()

    publish_category_carousel(target_category=args.category, max_items=args.max, dry_run=args.dry_run)
