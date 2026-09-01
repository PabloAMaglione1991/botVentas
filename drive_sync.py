import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

ASSETS_DIR = BASE_DIR / "Assets"
DRIVE_URL = os.getenv("GOOGLE_DRIVE_FOLDER_URL", "https://drive.google.com/drive/folders/1e8l8vqrS6fdYOvhWEzRSLhOyCr5vAGR1")


def sync_from_google_drive():
    try:
        import gdown
    except ImportError:
        print("❌ Error: gdown no está instalado. Ejecutá: pip install gdown")
        sys.exit(1)

    print("\n" + "="*60)
    print(" ☁️  SINCRONIZANDO FOTOS DESDE GOOGLE DRIVE")
    print("="*60)
    print(f" URL Origen : {DRIVE_URL}")
    print(f" Destino    : {ASSETS_DIR}")
    print(" Descargando y actualizando carpetas...\n")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        gdown.download_folder(
            url=DRIVE_URL,
            output=str(ASSETS_DIR),
            quiet=False,
            use_cookies=False
        )
        print("\n✅ Descarga de Google Drive finalizada exitosamente.")
    except Exception as e:
        print(f"\n⚠️ Nota sobre la descarga: {e}")

    # After sync, run the catalog builder to update posts.json with root-only stock
    from catalog_builder import sync_stock_catalog
    print("\n🔄 Actualizando catálogo de publicaciones (solo stock en raíz de categorías)...")
    sync_stock_catalog(dry_run=False)


if __name__ == "__main__":
    sync_from_google_drive()
