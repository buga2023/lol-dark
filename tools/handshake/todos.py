"""T1: cada serviço externo responde? Imprime só OK/FALHA, nunca a resposta crua."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import RAIZ, duracao, telegram  # noqa: E402

res = {}


def teste(nome):
    def dec(f):
        try:
            res[nome] = "OK " + (f() or "")
        except Exception as e:
            res[nome] = f"FALHA {e.__class__.__name__}: {str(e)[:120]}"
        return f
    return dec


@teste("data_dragon")
def _():
    return requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=20).json()[0]


@teste("patch_notes")
def _():
    r = requests.get("https://www.leagueoflegends.com/pt-br/news/tags/patch-notes/", timeout=20)
    r.raise_for_status()
    return str(r.status_code)


@teste("gemini")
def _():
    from gemini import gerar_json
    return str(gerar_json("Responda só JSON.", 'Devolva {"ok": true}', temperatura=0).get("ok"))


@teste("tts_pt")
def _():
    out = Path(tempfile.mkdtemp()) / "t.wav"
    subprocess.run(["npx", "--no-install", "hyperframes", "tts", "Ezreal ganhou dano no ultimate.", "-v", "pm_alex",
                    "-l", "pt-br", "-o", str(out)], cwd=RAIZ, check=True, capture_output=True, timeout=600)
    return f"{duracao(out):.1f}s"


@teste("telegram")
def _():
    telegram("sendMessage", {"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": "lol-dark: handshake ok"})


@teste("youtube")
def _():
    from publicar import token
    r = requests.get("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                     headers={"Authorization": f"Bearer {token()}"}, timeout=20).json()
    return r["items"][0]["snippet"]["title"]


for k, v in res.items():
    print(f"{k:12} {v}")
sys.exit(0 if all(v.startswith("OK") for v in res.values()) else 1)
