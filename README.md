# Sistema Integral de Ventas en Instagram - Ahora Cuotas

Suite completa de automatización para venta directa financiada en Instagram conectada a Google Drive y WhatsApp.

---

## 🚀 Módulos Disponibles

### 1. Autopilot Total (`auto_pilot.py` o `iniciar_autopilot.bat`)
Orquesta todo en segundo plano:
* **Sincronización de Drive:** Actualiza stock real cada 6 horas.
* **Publicación en Feed/Reels:** Publica productos cada 20 minutos con análisis visual de Gemini 2.5 Flash.
* **Historias Diarias:** Sube 1 Story formateada en 9:16 cada 2 horas con CTA a WhatsApp.
* **Auto-Responder de Leads:** Revisa cada 10 minutos si hay comentarios (`"precio"`, `"info"`, `"cuotas"`) o DMs nuevos y les responde automáticamente con el link directo a tu WhatsApp (`wa.me/5493425107083`).

```bash
python auto_pilot.py
```

---

### 2. Generador Masivo de Reels con IA de Google (`batch_reel_generator.py`)
Transforma fotos estáticas del stock en videos verticales 9:16 para Reels:
* Analiza la imagen con **Gemini 2.5 Flash Vision** y redacta guión de venta argentino.
* Genera la locución con **Google TTS**.
* Renderiza el video con efecto zoom, placas de cuotas y música.

```bash
# Generar 5 Reels con IA
python batch_reel_generator.py --count 5

# Generar Reels para una categoría específica (ej: Motos)
python batch_reel_generator.py --category Motos --count 3
```

---

### 3. Publicador de Carruseles Multi-producto (`carousel_publisher.py`)
Publica álbumes de 3 a 5 fotos de la misma categoría:

```bash
python carousel_publisher.py --category "Celulares y Tablet"
```

---

### 4. Publicador Manual de Historias (`story_publisher.py`)
Toma un producto al azar, lo enmarca en formato 9:16 de alta resolución con zócalos de *"Solo con DNI"* y lo sube a Stories:

```bash
python story_publisher.py
```

---

### 5. Auto-Responder de Comentarios y DMs (`auto_responder.py`)
Ejecuta una pasada manual para responder todas las consultas pendientes y enviar el link de WhatsApp:

```bash
python auto_responder.py
```
