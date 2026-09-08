import os
import requests
import feedparser

# ---------------------- CONFIG ----------------------
WATCHES = [
    {
        "nombre": "FiiO KA13",
        "meli_query": "fiio ka13",
        "meli_site": "MLA",
        "forum_keywords": ["ka13", "fiio ka13"],
    },
]

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


def check_meli(vistos, watch):
    url = f"https://api.mercadolibre.com/sites/{watch['meli_site']}/search"
    params = {"q": watch["meli_query"], "condition": "used", "limit": 50}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    for item in data.get("results", []):
        item_id = f"meli:{item['id']}"
        if item_id in vistos:
            continue
        vistos.add(item_id)
        guardar_visto(item_id)
        mensaje = (
            f"🛒 ML usado - {watch['nombre']}\n"
            f"{item['title']}\n"
            f"${item['price']} - {item['permalink']}"
        )
        print(mensaje)
        enviar_telegram(mensaje)


def check_forum(vistos):
    feed = feedparser.parse(FORUM_RSS_URL)
    for entry in feed.entries:
        entry_id = f"forum:{entry.link}"
        if entry_id in vistos:
            continue
        vistos.add(entry_id)
        guardar_visto(entry_id)

        titulo = entry.title.lower()
        for watch in WATCHES:
            if any(kw.lower() in titulo for kw in watch["forum_keywords"]):
                mensaje = f"💬 Foro 3DG - {watch['nombre']}\n{entry.title}\n{entry.link}"
                print(mensaje)
                enviar_telegram(mensaje)
                break


def main():
    vistos = cargar_vistos()
    for watch in WATCHES:
        try:
            check_meli(vistos, watch)
        except Exception as e:
            print(f"[meli:{watch['nombre']}] error: {e}")
    try:
        check_forum(vistos)
    except Exception as e:
        print(f"[forum] error: {e}")


if __name__ == "__main__":
    main()
