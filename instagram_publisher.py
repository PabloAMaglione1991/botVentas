import os
import sys
import json
import time
import random
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

CATALOG_FILE = BASE_DIR / "posts.json"
SESSION_FILE = BASE_DIR / os.getenv("IG_SESSION_FILE", "session.json")
IG_USERNAME = os.getenv("IG_USERNAME", "")
IG_PASSWORD = os.getenv("IG_PASSWORD", "")
DEFAULT_INTERVAL = int(os.getenv("POSTING_INTERVAL_MINUTES", "20"))


def load_catalog():
    if not CATALOG_FILE.exists():
        print(f"❌ Error: No se encontró {CATALOG_FILE}. Ejecutá primero 'python catalog_builder.py'.")
        sys.exit(1)
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_catalog(catalog_data):
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, ensure_ascii=False, indent=2)


def get_client():
    from instagrapi import Client

    cl = Client()
    cl.delay_range = [2, 5]

    if SESSION_FILE.exists():
        try:
            print(f"🔄 Cargando sesión guardada desde {SESSION_FILE}...")
            cl.load_settings(SESSION_FILE)
            user_info = cl.account_info()
            print(f"✅ Sesión activa para @{user_info.username}. Reutilizando conexión.")
            return cl
        except Exception as e:
            print(f"⚠️ No se pudo reutilizar la sesión guardada: {e}. Iniciando login nuevo...")

    if not IG_USERNAME or not IG_PASSWORD or IG_USERNAME == "tu_usuario_de_instagram":
        print("❌ Error: Debes configurar IG_USERNAME e IG_PASSWORD en tu archivo .env")
        sys.exit(1)

    print(f"🔑 Iniciando sesión para el usuario @{IG_USERNAME}...")
    try:
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(SESSION_FILE)
        print(f"✅ Login exitoso. Sesión guardada en {SESSION_FILE}.")
        return cl
    except Exception as e:
        print(f"❌ Error de autenticación en Instagram: {e}")
        sys.exit(1)


def show_status():
    catalog = load_catalog()
    posts = catalog.get("posts", [])
    
    pending = [p for p in posts if p["status"] == "pending"]
    published = [p for p in posts if p["status"] == "published"]
    errors = [p for p in posts if p["status"] == "error"]

    print("\n" + "="*50)
    print(" 📊 ESTADO DEL CATÁLOGO DE PUBLICACIONES")
    print("="*50)
    print(f" Total de posts : {len(posts)}")
    print(f" ⏳ Pendientes  : {len(pending)}")
    print(f" ✅ Publicados  : {len(published)}")
    print(f" ❌ Con error   : {len(errors)}")
    print("="*50)

    print("\nDETALLE DE PUBLICACIONES:")
    for p in posts:
        status_icon = "⏳" if p["status"] == "pending" else ("✅" if p["status"] == "published" else "❌")
        print(f" [{p['id']}] {status_icon} [{p['category']}] {p['title']} ({p['filename']})")
        if p["status"] == "published":
            print(f"       Publicado el: {p['published_at']} | ID Media: {p['media_id']}")
        elif p["status"] == "error":
            print(f"       Error: {p['error_message']}")
    print("")


def validate_dry_run():
    catalog = load_catalog()
    posts = catalog.get("posts", [])
    print("\n🔍 Validando catálogo en MODO DRY RUN (Sin subir nada a Instagram)...")
    
    all_ok = True
    for p in posts:
        file_path = Path(p["absolute_path"])
        exists = file_path.exists()
        size_kb = file_path.stat().st_size / 1024 if exists else 0
        
        status_str = "OK" if exists else "NO ENCONTRADO"
        if not exists:
            all_ok = False
            
        print(f"\n🏷️  [{p['id']}] {p['title']}")
        print(f"    Archivo : {p['relative_path']} ({size_kb:.1f} KB) -> [{status_str}]")
        print(f"    Rubro   : {p['category']}")
        print(f"    Copy    : {p['caption'][:80].replace(chr(10), ' ')}...")

    print("\n" + "-"*50)
    if all_ok:
        print("✅ Validación completada: Todos los archivos y copys están listos.")
    else:
        print("⚠️ Algunos archivos no se encontraron. Revisá las rutas.")


def publish_item(post, cl=None, dry_run=False):
    file_path = Path(post["absolute_path"])
    if not file_path.exists():
        raise FileNotFoundError(f"No existe el archivo {file_path}")

    if dry_run:
        print(f"🚀 [DRY RUN] Se publicaría: [{post['id']}] {post['title']} ({post['filename']})")
        return {"media_id": "dry_run_id", "timestamp": datetime.now().isoformat()}

    # Real-time Gemini Vision analysis to ensure 100% accurate caption for the actual image
    from catalog_builder import generate_caption_with_gemini
    try:
        final_caption = generate_caption_with_gemini(file_path, post["title"], post.get("category", ""))
        post["caption"] = final_caption
    except Exception as e:
        print(f"⚠️ Nota de caption: {e}. Usando caption predeterminada.")
        final_caption = post["caption"]

    print(f"📤 Subiendo [{post['id']}]: {post['title']} ({file_path.name})...")
    
    for attempt in range(2):
        try:
            if post.get("media_type") == "photo" or file_path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                media = cl.photo_upload(
                    path=str(file_path),
                    caption=final_caption
                )
            elif post.get("media_type") == "video" or file_path.suffix.lower() in [".mp4", ".mov"]:
                media = cl.clip_upload(
                    path=str(file_path),
                    caption=final_caption
                )
            else:
                raise ValueError(f"Tipo de archivo no soportado: {file_path.suffix}")

            media_dict = media.dict() if hasattr(media, "dict") else (media.model_dump() if hasattr(media, "model_dump") else media.__dict__)
            media_pk = media_dict.get("pk") or media_dict.get("id")

            return {
                "media_id": str(media_pk),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            err_str = str(e).lower()
            if ("login_required" in err_str or "403" in err_str or "unauthorized" in err_str) and attempt == 0:
                print("🔄 Sesión vencida o requerida. Renovando login en Instagram...")
                if SESSION_FILE.exists():
                    SESSION_FILE.unlink(missing_ok=True)
                cl.login(IG_USERNAME, IG_PASSWORD)
                cl.dump_settings(SESSION_FILE)
                print("✅ Sesión renovada. Reintentando subida...")
                time.sleep(3)
                continue
            raise e


def run_next(dry_run=False):
    catalog = load_catalog()
    posts = catalog.get("posts", [])
    
    target = None
    for p in posts:
        if p["status"] == "pending":
            target = p
            break

    if not target:
        print("✨ No hay más posts pendientes en el catálogo.")
        return

    cl = None if dry_run else get_client()
    try:
        res = publish_item(target, cl=cl, dry_run=dry_run)
        if not dry_run:
            target["status"] = "published"
            target["published_at"] = res["timestamp"]
            target["media_id"] = res["media_id"]
            target["error_message"] = None
            save_catalog(catalog)
            print(f"🎉 Post {target['id']} publicado con éxito! ID: {res['media_id']}")
    except Exception as e:
        if not dry_run:
            target["status"] = "error"
            target["error_message"] = str(e)
            save_catalog(catalog)
        print(f"❌ Error al publicar {target['id']}: {e}")


def run_all(interval_minutes=DEFAULT_INTERVAL, dry_run=False):
    catalog = load_catalog()
    pending = [p for p in catalog.get("posts", []) if p["status"] == "pending"]

    if not pending:
        print("✨ No hay posts pendientes para publicar.")
        return

    print(f"📋 Se van a procesar {len(pending)} publicaciones.")
    print(f"⏱️ Intervalo entre posts: {interval_minutes} minutos.")
    
    cl = None if dry_run else get_client()

    for i, post in enumerate(pending):
        try:
            res = publish_item(post, cl=cl, dry_run=dry_run)
            if not dry_run:
                post["status"] = "published"
                post["published_at"] = res["timestamp"]
                post["media_id"] = res["media_id"]
                post["error_message"] = None
                save_catalog(catalog)
                print(f"✅ [{i+1}/{len(pending)}] Publicado {post['id']} exitosamente.")
        except Exception as e:
            if not dry_run:
                post["status"] = "error"
                post["error_message"] = str(e)
                save_catalog(catalog)
            print(f"❌ Error en {post['id']}: {e}")

        # Wait before next post if there are remaining items
        if i < len(pending) - 1:
            wait_seconds = (interval_minutes * 60) + random.randint(10, 60)
            print(f"⏳ Esperando {wait_seconds // 60} min para la siguiente publicación...")
            if not dry_run:
                time.sleep(wait_seconds)


def main():
    parser = argparse.ArgumentParser(description="Instagram Direct Sales Uploader")
    parser.add_argument("--status", action="store_true", help="Muestra el estado del catálogo")
    parser.add_argument("--dry-run", action="store_true", help="Valida archivos y copys sin subir")
    parser.add_argument("--next", action="store_true", help="Publica el siguiente post pendiente")
    parser.add_argument("--all", action="store_true", help="Publica todos los posts pendientes con intervalo")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Minutos de espera entre posts")
    parser.add_argument("--post-id", type=str, help="Publica un post específico por su ID (ej: post_001)")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.dry_run:
        validate_dry_run()
    elif args.next:
        run_next(dry_run=False)
    elif args.all:
        run_all(interval_minutes=args.interval, dry_run=False)
    elif args.post_id:
        catalog = load_catalog()
        target = next((p for p in catalog.get("posts", []) if p["id"] == args.post_id), None)
        if not target:
            print(f"❌ Post con ID '{args.post_id}' no encontrado.")
            sys.exit(1)
        res = publish_item(target, dry_run=False)
        target["status"] = "published"
        target["published_at"] = res["timestamp"]
        target["media_id"] = res["media_id"]
        save_catalog(catalog)
        print(f"🎉 Post {target['id']} publicado con éxito!")
    else:
        # Default behavior: Show status and dry run summary
        show_status()
        print("💡 Para probar sin publicar: python instagram_publisher.py --dry-run")
        print("💡 Para publicar el siguiente: python instagram_publisher.py --next")
        print("💡 Para publicar la cola completa: python instagram_publisher.py --all --interval 20")


if __name__ == "__main__":
    main()
