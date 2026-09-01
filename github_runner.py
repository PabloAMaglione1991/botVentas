import os
import sys
import base64
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SESSION_FILE = BASE_DIR / "session.json"
SESSION_B64 = os.getenv("IG_SESSION_B64", "")


def restore_session_if_provided():
    """Restores session.json from base64 secret in GitHub Actions if available."""
    if SESSION_B64 and not SESSION_FILE.exists():
        try:
            decoded = base64.b64decode(SESSION_B64).decode("utf-8")
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                f.write(decoded)
            print("🔑 Sesión de Instagram restaurada desde GitHub Secret.")
        except Exception as e:
            print(f"⚠️ No se pudo decodificar IG_SESSION_B64: {e}")


def run_github_cycle():
    print("\n" + "="*60)
    print(" 🚀 INICIANDO EJECUCIÓN AUTOMÁTICA EN GITHUB ACTIONS")
    print("="*60)

    restore_session_if_provided()

    # 1. Sync from Google Drive
    print("\n☁️ [1/4] Sincronizando stock real desde Google Drive...")
    try:
        from drive_sync import sync_from_google_drive
        sync_from_google_drive()
    except Exception as e:
        print(f"⚠️ Error en sincronización de Drive: {e}")

    # 2. Initialize Instagram Client
    print("\n📱 [2/4] Conectando a Instagram...")
    from instagram_publisher import get_client, publish_item, load_catalog, save_catalog
    cl = get_client()

    # 3. Publish Next Pending Feed Post / Reel
    print("\n📤 [3/4] Publicando siguiente producto pendiente...")
    catalog = load_catalog()
    posts = catalog.get("posts", [])
    pending = [p for p in posts if p["status"] == "pending"]

    if pending:
        target = pending[0]
        try:
            res = publish_item(target, cl=cl, dry_run=False)
            target["status"] = "published"
            target["published_at"] = res["timestamp"]
            target["media_id"] = res["media_id"]
            target["error_message"] = None
            save_catalog(catalog)
            print(f"🎉 Publicado exitosamente: [{target['id']}] {target['title']} | ID: {res['media_id']}")
        except Exception as e:
            print(f"❌ Error al publicar {target['id']}: {e}")
            target["status"] = "error"
            target["error_message"] = str(e)
            save_catalog(catalog)
    else:
        print("✨ No hay posts pendientes en este ciclo.")

    # 4. Check Leads and Comments
    print("\n🤖 [4/4] Revisando comentarios y DMs para captar leads...")
    try:
        from auto_responder import check_and_reply_interactions
        check_and_reply_interactions(cl=cl)
    except Exception as e:
        print(f"⚠️ Error en auto-responder: {e}")

    print("\n" + "="*60)
    print(" ✅ CICLO DE GITHUB ACTIONS FINALIZADO CON ÉXITO")
    print("="*60)


if __name__ == "__main__":
    run_github_cycle()
