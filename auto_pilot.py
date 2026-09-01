import os
import sys
import time
import random
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

LOG_FILE = BASE_DIR / "autopilot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Settings from environment
POSTING_INTERVAL_MINUTES = int(os.getenv("POSTING_INTERVAL_MINUTES", "20"))
SYNC_INTERVAL_HOURS = int(os.getenv("SYNC_INTERVAL_HOURS", "6"))
STORY_INTERVAL_HOURS = int(os.getenv("STORY_INTERVAL_HOURS", "2"))
LEAD_CHECK_MINUTES = int(os.getenv("LEAD_CHECK_MINUTES", "10"))


def run_autopilot():
    from drive_sync import sync_from_google_drive
    from instagram_publisher import get_client, publish_item, load_catalog, save_catalog
    from story_publisher import publish_random_story
    from auto_responder import check_and_reply_interactions

    logging.info("🚀 ========================================================")
    logging.info("   AHORA CUOTAS - AUTOPILOT TOTAL INICIADO")
    logging.info("   • Publicación Feed/Reels : Cada %d min", POSTING_INTERVAL_MINUTES)
    logging.info("   • Historias (Stories)    : Cada %d horas", STORY_INTERVAL_HOURS)
    logging.info("   • Auto-responder DMs/Com : Cada %d min", LEAD_CHECK_MINUTES)
    logging.info("   • Sincronización Drive   : Cada %d horas", SYNC_INTERVAL_HOURS)
    logging.info("==========================================================")

    last_sync_time = datetime.min
    last_story_time = datetime.min
    last_lead_check_time = datetime.min
    cl = None

    while True:
        try:
            now = datetime.now()

            # Ensure Instagram client is ready
            if cl is None:
                cl = get_client()

            # 1. Check Google Drive Sync
            if now - last_sync_time >= timedelta(hours=SYNC_INTERVAL_HOURS):
                logging.info("☁️ [DRIVE] Sincronizando stock real desde Google Drive...")
                try:
                    sync_from_google_drive()
                    last_sync_time = datetime.now()
                    logging.info("✅ [DRIVE] Sincronización finalizada.")
                except Exception as e:
                    logging.error("⚠️ [DRIVE] Error: %s", e)

            # 2. Check Lead Auto-Responder (Comments & DMs)
            if now - last_lead_check_time >= timedelta(minutes=LEAD_CHECK_MINUTES):
                logging.info("🤖 [LEADS] Revisando comentarios y DMs nuevos...")
                try:
                    check_and_reply_interactions(cl=cl)
                    last_lead_check_time = datetime.now()
                except Exception as e:
                    logging.error("⚠️ [LEADS] Error en auto-responder: %s", e)

            # 3. Check Stories Publishing
            if now - last_story_time >= timedelta(hours=STORY_INTERVAL_HOURS):
                logging.info("📸 [STORY] Publicando Historia automática...")
                try:
                    publish_random_story(cl=cl)
                    last_story_time = datetime.now()
                except Exception as e:
                    logging.error("⚠️ [STORY] Error publicando historia: %s", e)

            # 4. Feed & Reel Post Publishing
            catalog = load_catalog()
            posts = catalog.get("posts", [])
            pending_posts = [p for p in posts if p["status"] == "pending"]

            if not pending_posts:
                logging.info("✨ No hay posts pendientes en el feed. Esperando 30 min...")
                time.sleep(1800)
                continue

            target_post = pending_posts[0]
            logging.info("📌 [FEED/REEL] Próximo a publicar: [%s] %s (%s)", target_post['id'], target_post['title'], target_post['filename'])

            try:
                res = publish_item(target_post, cl=cl, dry_run=False)
                target_post["status"] = "published"
                target_post["published_at"] = res["timestamp"]
                target_post["media_id"] = res["media_id"]
                target_post["error_message"] = None
                save_catalog(catalog)
                logging.info("🎉 [FEED/REEL] Publicado exitosamente: [%s] ID: %s", target_post['id'], res['media_id'])
            except Exception as e:
                logging.error("❌ [FEED/REEL] Error al publicar [%s]: %s", target_post['id'], e)
                target_post["status"] = "error"
                target_post["error_message"] = str(e)
                save_catalog(catalog)

            # 5. Delay before next feed cycle
            wait_seconds = (POSTING_INTERVAL_MINUTES * 60) + random.randint(15, 45)
            logging.info("⏳ Esperando %d minutos para la siguiente publicación en feed...", wait_seconds // 60)
            time.sleep(wait_seconds)

        except KeyboardInterrupt:
            logging.info("🛑 Autopilot detenido por el usuario.")
            break
        except Exception as e:
            logging.error("💥 Error en ciclo de Autopilot: %s", e)
            time.sleep(60)


if __name__ == "__main__":
    run_autopilot()
