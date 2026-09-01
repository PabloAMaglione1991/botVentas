import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SESSION_FILE = BASE_DIR / os.getenv("IG_SESSION_FILE", "session.json")


def login_with_session_id():
    from instagrapi import Client

    print("\n" + "="*60)
    print(" 🔑 ASISTENTE DE INICIO DE SESIÓN - AHORA CUOTAS")
    print("="*60)
    print("Instagram bloquea los logins automatizados directos por seguridad,")
    print("pero permite usar la sesión activa de tu navegador web (Chrome/Edge).\n")
    print("📌 CÓMO OBTENER TU 'SESSIONID' EN 3 PASOS:")
    print(" 1. Abrí instagram.com en tu navegador (Chrome o Edge) e iniciá sesión con @tiendasfahoracuotas.")
    print(" 2. Presioná F12 en tu teclado para abrir las herramientas de desarrollador.")
    print(" 3. Andá a la pestaña 'Aplicación' (o 'Application') -> 'Cookies' -> 'https://www.instagram.com'.")
    print(" 4. Buscá la cookie llamada 'sessionid' y copiá su valor completo (es un texto largo).\n")
    print("="*60)

    session_id = input("\n👉 Pegá acá el valor de 'sessionid' y presioná Enter: ").strip()

    if not session_id:
        print("❌ No ingresaste ningún sessionid.")
        return False

    print("\n⏳ Conectando con Instagram usando tu sesión del navegador...")
    cl = Client()
    try:
        cl.login_by_sessionid(session_id)
        user_info = cl.account_info()
        print(f"✅ ¡ÉXITO! Conectado a la cuenta: @{user_info.username} ({user_info.full_name})")
        
        cl.dump_settings(SESSION_FILE)
        print(f"💾 Sesión guardada correctamente en '{SESSION_FILE}'.")
        print("🚀 Ya podés ejecutar 'python auto_pilot.py' sin bloqueos.")
        return True
    except Exception as e:
        print(f"❌ Error al conectar con ese sessionid: {e}")
        return False


if __name__ == "__main__":
    login_with_session_id()
