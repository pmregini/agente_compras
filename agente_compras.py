import os
import re
import requests
import feedparser

# ---------------------- CONFIGURACIÓN ----------------------

# 1. MERCADO LIBRE: Productos específicos a monitorear
WATCHES_MELI = [
    {
        "nombre": "Echo Show",
        "query": "echo show",
        "site": "MLA",
    },
    # Podés sumar más ítems agregando bloques como este:
    # {
    #     "nombre": "Kindle Paperwhite",
    #     "query": "kindle paperwhite",
    #     "site": "MLA",
    # },
]

# 2. FORO 3DGAMES: URL del RSS del subforo Compra/Venta Usados
FORUM_RSS_URL = "https://foros.3dgames.com.ar/external.php?type=RSS2&forumids=246"

# Credenciales desde las variables de GitHub
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TXT_PATH = "vistos.txt"

# -----------------------------------------------------------


def cargar_vistos():
    """Carga los IDs procesados anteriormente. Si no existe el archivo, lo crea."""
    if not os.path.exists(TXT_PATH):
        with open(TXT_PATH, "w", encoding="utf-8") as f:
            pass
        return set()
    with open(TXT_PATH, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def guardar_visto(item_id):
    """Guarda un nuevo ID procesado en el archivo vistos.txt."""
    with open(TXT_PATH, "a", encoding="utf-8") as f:
        f.write(f"{item_id}\n")


def enviar_telegram(mensaje):
    """Manda notificaciones a Telegram (soporta múltiples IDs separados por coma)."""
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
    """
    Extrae el ID numérico único del thread de 3DGames.
    Ejemplo: de 'https://foros.3dgames.com.ar/threads/1114858-limpieza...' extrae '1114858'
    """
    match = re.search(r'threads/(\d+)', link)
    if match:
        return match.group(1)
    return link.split('?')[0]


def check_meli(vistos):
    """Revisa publicaciones usadas en Mercado Libre según la lista WATCHES_MELI."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    for watch in WATCHES_MELI:
        try:
            url = f"https://api.mercadolibre.com/sites/{watch['site']}/search"
            params = {"q": watch["query"], "condition": "used", "limit": 50}
            r = requests.get(url, params=params, headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()

            nuevos_count = 0
            for item in data.get("results", []):
                item_id = f"meli:{item['id']}"
                if item_id in vistos:
                    continue

                vistos.add(item_id)
                guardar_visto(item_id)
                nuevos_count += 1

                mensaje = (
                    f"🛒 ML Usado - {watch['nombre']}\n\n"
                    f"📦 {item['title']}\n"
                    f"💰 ${item['price']}\n"
                    f"🔗 {item['permalink']}"
                )
                print(f"[Nuevo en ML]: {item['title']}")
                enviar_telegram(mensaje)
                
            if nuevos_count == 0:
                print(f"[meli:{watch['nombre']}] Sin items nuevos.")
        except Exception as e:
            print(f"[meli:{watch['nombre']}] error: {e}")


def check_forum(vistos):
    """Descarga el RSS del foro con User-Agent de navegador y procesa todos los temas nuevos."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(FORUM_RSS_URL, headers=headers, timeout=15)
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
    
    # 1. Chequeo de Mercado Libre
    check_meli(vistos)
    
    # 2. Chequeo de Foro 3DGames
    try:
        check_forum(vistos)
    except Exception as e:
        print(f"[forum] error fatal: {e}")


if __name__ == "__main__":
    main()
