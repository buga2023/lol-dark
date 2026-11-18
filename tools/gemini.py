"""Cliente mínimo da API do Gemini (AI Studio). Não imprime a resposta crua."""
import json
import os
import re
import time

import requests

MODELO = os.environ.get("LOL_GEMINI_MODELO", "gemini-2.5-flash")


def gerar_json(sistema, usuario, temperatura=0.8, modelo=None, tentativas=3):
    chave = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo or MODELO}:generateContent"
    corpo = {"systemInstruction": {"parts": [{"text": sistema}]},
             "contents": [{"role": "user", "parts": [{"text": usuario}]}],
             "generationConfig": {"temperature": temperatura, "responseMimeType": "application/json"}}
    ultimo = None
    for i in range(tentativas):
        r = requests.post(url, headers={"x-goog-api-key": chave}, json=corpo, timeout=180)
        if r.status_code in (429, 500, 503):
            ultimo = f"HTTP {r.status_code}"
            time.sleep(20 * (i + 1))
            continue
        if r.status_code != 200:
            raise RuntimeError(f"Gemini HTTP {r.status_code}")
        txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        txt = re.sub(r"^```(?:json)?|```$", "", txt.strip()).strip()
        return json.loads(txt)
    raise RuntimeError(f"Gemini indisponível: {ultimo}")
