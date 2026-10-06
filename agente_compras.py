import os
import re
import requests
import feedparser

# ---------------------- CONFIGURACIÓN ----------------------
FORUM_RSS_URL = "https://foros.3dgames.com.ar/external.php?type=RSS2&forumids=246"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TXT_PATH = "vistos.txt"
# -----------------------------------------------------------


def cargar_vistos():
    if not os.path.exists(TXT_PATH):
        with open(TXT_PATH, "w", encoding="utf-8") as f:
            pass
        return set()
    with open(TXT_PATH, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def guardar_visto(item_id):
    with open(TXT_PATH, "a", encoding="utf-8") as f:
        f.write(f"{item_id}\n")


def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[telegram Error]: Falta configurar credenciales\n{mensaje}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    chat_ids = [c.strip() for c in TELEGRAM_CHAT_ID.split(",") if c.strip()]
    
    for chat_id in chat_ids:
        payload = {
            "chat_id": chat_id,
            "text": mensaje,
            "disable_web_page_preview": False,
        }
        try:
            r = requests.post(url, json=payload, timeout=15)
            print(f"[telegram] chat_id={chat_id} status={r.status_code}")
        except Exception as e:
            print(f"[telegram] chat_id={chat_id} error: {e}")


def extraer_thread_id(link):
    match = re.search(r'threads/(\d+)', link)
    if match:
        return match.group(1)
    return link.split('?')[0]


def check_forum(vistos):
    # Encabezados completos para evitar el bloqueo 403 Forbidden de 3DGames
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }
    
    session = requests.Session()
    try:
        response = session.get(FORUM_RSS_URL, headers=headers, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as e:
        print(f"[forum] error al descargar RSS: {e}")
        return

    print(f"[forum] Ítems encontrados en el RSS: {len(feed.entries)}")
    nuevos = []

    for entry in feed.entries:
        thread_id = extraer_thread_id(entry.link)
        entry_key = f"forum:{thread_id}"

        if entry_key in vistos:
            continue

        clean_link = entry.link.split('?')[0]

        vistos.add(entry_key)
        guardar_visto(entry_key)

        entry_copy = entry
        entry_copy.link = clean_link
        nuevos.append(entry_copy)

    if not nuevos:
        print("[forum] No hay temas nuevos.")
        return

    encabezado = f"💬 {len(nuevos)} tema(s) nuevo(s) en Compra/Venta 3DG\n\n"
    bloque = encabezado
    for entry in nuevos:
        linea = f"• {entry.title}\n{entry.link}\n\n"
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
        print(f"[forum] error fatal: {e}")


if __name__ == "__main__":
    main()
