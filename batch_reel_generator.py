import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def generate_reels_in_batch(max_reels: int = 5, category: str = None):
    from instagram_publisher import load_catalog, save_catalog
    from ai_reel_generator import generate_reel_for_product

    catalog = load_catalog()
    posts = catalog.get("posts", [])

    candidates = [
        p for p in posts
        if p["status"] == "pending" and p.get("media_type") == "photo"
    ]

    if category:
        candidates = [p for p in candidates if category.lower() in p.get("category", "").lower()]

    if not candidates:
        print("✨ No se encontraron fotos pendientes para transformar en Reels.")
        return

    to_process = candidates[:max_reels]
    print("\n" + "="*60)
    print(f" 🎬 GENERANDO {len(to_process)} REELS CON IA DE GOOGLE EN LOTE")
    print("="*60)

    generated_count = 0
    for i, post in enumerate(to_process):
        img_path = Path(post["absolute_path"])
        if not img_path.exists():
            print(f"⚠️ Imagen no encontrada: {img_path}")
            continue

        print(f"\n[{i+1}/{len(to_process)}] Procesando: {post['title']} ({post['category']})...")
        try:
            video_path, script_data = generate_reel_for_product(
                image_path=img_path,
                product_title=post["title"],
                category=post.get("category", "")
            )

            # Update post in catalog to point to the new video Reel
            post["media_type"] = "video"
            post["absolute_path"] = str(video_path.resolve())
            post["relative_path"] = str(video_path.relative_to(BASE_DIR))
            post["filename"] = video_path.name
            
            # Use the AI script as the caption if desired
            generated_count += 1
            print(f"✅ Reel listo: {video_path.name}")
            
            # Small delay between API calls
            time.sleep(2)

        except Exception as e:
            print(f"❌ Error al generar Reel para {post['id']}: {e}")

    save_catalog(catalog)
    print(f"\n🎉 Proceso finalizado: {generated_count} Reels creados y agregados a la cola de publicación.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch generate Reels using Google AI")
    parser.add_argument("--count", type=int, default=3, help="Cantidad de Reels a generar")
    parser.add_argument("--category", type=str, help="Filtrar por categoría")
    args = parser.parse_args()

    generate_reels_in_batch(max_reels=args.count, category=args.category)
