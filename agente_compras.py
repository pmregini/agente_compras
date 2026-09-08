import os
import json
import requests
import feedparser

# ---------------------- CONFIG ----------------------

# Productos puntuales a rastrear en Mercado Libre (usados)
WATCHES = [
    {
        "nombre": "Echo Show",
        "meli_query": "echo show",
        "meli_site": "MLA",
    },
      {
        "nombre": "Hiby",
        "meli_query": "Hiby",
        "meli_site": "MLA",
    },
      {
        "nombre": "Fiio",
        "meli_query": "fiio",
        "meli_site": "MLA",
    },
      {
        "nombre": "Amazon Echo",
        "meli_query": "Amazon echo",
        "meli_site": "MLA",
    },
    # agregá más productos acá, mismo formato
]

# Foro: se avisa de TODOS los temas nuevos de este subforo, sin filtrar
FORUM_RSS_URL = "https://foros.3dgames.com.ar/external.php?type=RSS2&forumids=246"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ML_CLIENT_ID = os.environ.get("ML_CLIENT_ID")
ML_CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")
ML_TOKEN_PATH = "ml_token.json"

TXT_PATH = "vistos.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
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


def get_meli_access_token():
    """Renueva el access_token de ML usando el refresh_token guardado en ml_token.json."""
    if not os.path.exists(ML_TOKEN_PATH):
        print("[meli] falta ml_token.json - corré primero el workflow 'Vincular Mercado Libre'")
        return None
    if not ML_CLIENT_ID or not ML_CLIENT_SECRET:
        print("[meli] faltan los secrets ML_CLIENT_ID / ML_CLIENT_SECRET")
        return None

    with open(ML_TOKEN_PATH) as f:
        tok = json.load(f)

    resp = requests.post(
        "https://api.mercadolibre.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": ML_CLIENT_ID,
            "client_secret": ML_CLIENT_SECRET,
            "refresh_token": tok["refresh_token"],
        },
        headers={"accept": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    nuevo_tok = {"access_token": data["access_token"], "refresh_token": data["refresh_token"]}
    with open(ML_TOKEN_PATH, "w") as f:
        json.dump(nuevo_tok, f)

    return nuevo_tok["access_token"]


def check_meli(vistos, watch, access_token):
    """Avisa solo si aparece un producto usado que matchea el watch puntual."""
    url = f"https://api.mercadolibre.com/sites/{watch['meli_site']}/search"
    params = {"q": watch["meli_query"], "condition": "used", "limit": 50}
    auth_headers = {**HEADERS, "Authorization": f"Bearer {access_token}"}
    r = requests.get(url, params=params, headers=auth_headers, timeout=15)
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
    """Avisa de CADA tema nuevo del subforo, sin filtro de keywords."""
    feed = feedparser.parse(FORUM_RSS_URL)
    for entry in feed.entries:
        entry_id = f"forum:{entry.link}"
        if entry_id in vistos:
            continue
        vistos.add(entry_id)
        guardar_visto(entry_id)

        mensaje = f"💬 Tema nuevo en Compra/Venta 3DG\n{entry.title}\n{entry.link}"
        print(mensaje)
        enviar_telegram(mensaje)


def main():
    vistos = cargar_vistos()

    access_token = None
    try:
        access_token = get_meli_access_token()
    except Exception as e:
        print(f"[meli] error renovando token: {e}")

    if access_token:
        for watch in WATCHES:
            try:
                check_meli(vistos, watch, access_token)
            except Exception as e:
                print(f"[meli:{watch['nombre']}] error: {e}")
    else:
        print("[meli] omitido - sin access_token válido")

    try:
        check_forum(vistos)
    except Exception as e:
        print(f"[forum] error: {e}")


if __name__ == "__main__":
    main()
