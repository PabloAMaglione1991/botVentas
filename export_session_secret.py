import base64
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

session_file = Path("session.json")
if not session_file.exists():
    print("❌ Error: session.json no existe. Ejecutá primero 'python login_helper.py'.")
else:
    b64_str = base64.b64encode(session_file.read_bytes()).decode("utf-8")
    out_file = Path("session_secret_for_github.txt")
    out_file.write_text(b64_str, encoding="utf-8")
    print("\n" + "="*60)
    print(" 🔑 CLAVE DE SESIÓN PARA GITHUB ACTIONS GENERADA")
    print("="*60)
    print(f"✅ Se guardó en el archivo: {out_file}")
    print("\nPasos:")
    print(" 1. Abrí el archivo 'session_secret_for_github.txt' y copiá TODO su contenido.")
    print(" 2. En GitHub: Settings -> Secrets and variables -> Actions -> New repository secret")
    print(" 3. Name: IG_SESSION_B64")
    print(" 4. Secret: (Pegás el contenido copiado)")
    print("="*60 + "\n")
