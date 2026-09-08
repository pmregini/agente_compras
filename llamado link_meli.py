import os
import json
import requests

CLIENT_ID = os.environ["ML_CLIENT_ID"]
CLIENT_SECRET = os.environ["ML_CLIENT_SECRET"]
CODE = os.environ["ML_AUTH_CODE"]

# Tiene que ser EXACTAMENTE la misma que pusiste como Redirect URI al crear la app en ML.
REDIRECT_URI = "https://github.com/pmregini/agente_compras"

resp = requests.post(
    "https://api.mercadolibre.com/oauth/token",
    data={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": CODE,
        "redirect_uri": REDIRECT_URI,
    },
    headers={"accept": "application/json"},
    timeout=15,
)
resp.raise_for_status()
data = resp.json()

with open("ml_token.json", "w") as f:
    json.dump({"access_token": data["access_token"], "refresh_token": data["refresh_token"]}, f)

print("Vinculación OK. user_id:", data.get("user_id"))
