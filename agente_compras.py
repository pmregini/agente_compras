import os
import requests
import feedparser

# ---------------------- CONFIG ----------------------

# Foro: se avisa de TODOS los temas nuevos de este subforo, sin filtrar
FORUM_RSS_URL = "https://foros.3dgames.com.ar/external.php?type=RSS2&forumids=246"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

TXT_PATH = "vistos.txt"
# ------------------------------------------------------


def cargar_vistos():
    if not os.path.exists(TXT_PATH):
        return set()
    with open(TXT_PATH, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def guardar_visto(item_id):
    with open(TXT_PATH, "a", encoding="utf-8") as f:
        f.write(f"{item_id}\n")


def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[telegram] config ausente: {mensaje}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "disable_web_page_preview": False}
    try:
        r = requests.post(url, json=payload, timeout=15)
        print(f"[telegram] status={r.status_code}")
    except Exception as e:
        print(f"[telegram] error: {e}")


def check_forum(vistos):
    """Junta TODOS los temas nuevos del subforo y los manda en un solo mensaje agrupado."""
    feed = feedparser.parse(FORUM_RSS_URL)
    nuevos = []

    for entry in feed.entries:
        entry_id = f"forum:{entry.link}"
        if entry_id in vistos:
            continue
        vistos.add(entry_id)
        guardar_visto(entry_id)
        nuevos.append(entry)

    if not nuevos:
        return

    encabezado = f"💬 {len(nuevos)} tema(s) nuevo(s) en Compra/Venta 3DG\n\n"
    bloque = encabezado
    for entry in nuevos:
        linea = f"• {entry.title}\n{entry.link}\n\n"
        # Telegram corta mensajes largos (~4096 caracteres); si se pasa, mandamos en partes.
        if len(bloque) + len(linea) > 3500:
            print(bloque)
            enviar_telegram(bloque)
            bloque = ""
        bloque += linea

    if bloque.strip():
        print(bloque)
        enviar_telegram(bloque)


def main():
    vistos = cargar_vistos()
    try:
        check_forum(vistos)
    except Exception as e:
        print(f"[forum] error: {e}")


if __name__ == "__main__":
    main()
