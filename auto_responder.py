import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

LEADS_FILE = BASE_DIR / "responded_leads.json"
WHATSAPP_LINK = "https://wa.me/5493425107083?text=Hola!%20Vengo%20de%20Instagram%20y%20quiero%20consultar%20por%20las%20cuotas"

SALES_KEYWORDS = [
    "info", "precio", "cuanto", "cuánto", "cuota", "cuotas", "hola",
    "disponible", "stock", "tenes", "tenés", "comprar", "requisitos",
    "donde", "dónde", "envio", "envío", "interesa", "buenas"
]


def load_leads_db():
    if not LEADS_FILE.exists():
        return {"replied_comments": [], "messaged_users": [], "last_check": None}
    try:
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"replied_comments": [], "messaged_users": [], "last_check": None}


def save_leads_db(data):
    data["last_check"] = datetime.now().isoformat()
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_sales_intent(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in SALES_KEYWORDS)


def check_and_reply_interactions(cl=None):
    from instagram_publisher import get_client

    if cl is None:
        cl = get_client()

    leads_db = load_leads_db()
    replied_comments = set(leads_db.get("replied_comments", []))
    messaged_users = set(leads_db.get("messaged_users", []))

    print("\n" + "="*60)
    print(" 🤖 AUTO-RESPONDER: BUSCANDO COMENTARIOS Y DMs DE VENTAS")
    print("="*60)

    # 1. Check comments on recent posts
    try:
        user_id = cl.user_id_from_username(cl.username)
        medias = cl.user_medias(user_id, amount=10)
        print(f"👀 Revisando comentarios en las últimas {len(medias)} publicaciones...")

        for m in medias:
            try:
                comments = cl.media_comments(m.pk)
                for c in comments:
                    c_id = str(c.pk)
                    u_id = str(c.user.pk)
                    c_text = c.text

                    if c_id in replied_comments:
                        continue

                    # Check if comment has buying intent
                    if is_sales_intent(c_text):
                        print(f"\n🎯 Nuevo lead detectado en post {m.pk}:")
                        print(f"   Usuario : @{c.user.username}")
                        print(f"   Comentario : \"{c_text}\"")

                        # Like the comment
                        try:
                            cl.comment_like(c.pk)
                        except Exception:
                            pass

                        # Reply to comment
                        public_reply = f"¡Hola @{c.user.username}! Te enviamos un mensaje privado con los detalles y cuotas 📩"
                        try:
                            cl.media_comment(m.pk, public_reply, replied_to_comment_id=c.pk)
                            print(f"   ✅ Respuesta pública enviada.")
                        except Exception as e:
                            print(f"   ⚠️ No se pudo responder al comentario: {e}")

                        # Send DM to user if not messaged recently
                        if u_id not in messaged_users:
                            dm_text = f"""¡Hola {c.user.full_name or c.user.username}! 👋 

Gracias por tu consulta en Ahora Cuotas.

✔️ Requisitos: Solo DNI + 1 Servicio
✔️ Planes en cuotas: Por día, semana o mes
✔️ Entrega: En 24 horas en tu domicilio (Santa Fe y alrededores)

💬 Podés consultar los modelos disponibles y pedir tu aprobación al instante por WhatsApp acá:
{WHATSAPP_LINK}"""
                            try:
                                cl.direct_send(dm_text, user_ids=[int(u_id)])
                                print(f"   ✅ DM automático enviado con link a WhatsApp.")
                                messaged_users.add(u_id)
                            except Exception as e:
                                print(f"   ⚠️ No se pudo enviar el DM: {e}")

                        replied_comments.add(c_id)
                        time.sleep(3)

            except Exception as e:
                print(f"⚠️ Error al revisar comentarios del post {m.pk}: {e}")

    except Exception as e:
        print(f"⚠️ Error general al obtener publicaciones del perfil: {e}")

    # Save tracking DB
    leads_db["replied_comments"] = list(replied_comments)
    leads_db["messaged_users"] = list(messaged_users)
    save_leads_db(leads_db)
    print("\n✅ Chequeo de interacciones finalizado.")


if __name__ == "__main__":
    check_and_reply_interactions()
