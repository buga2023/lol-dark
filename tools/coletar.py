"""Passo 1: fontes -> itens.jsonl. Deduplica por hash da URL. Fonte fora do ar não derruba a execução."""
import hashlib
import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from comum import ESTADO, alertar, anexar_jsonl, ler_jsonl  # noqa: E402

BASE = "https://www.leagueoflegends.com"
FONTES = {
    "patch": f"{BASE}/pt-br/news/tags/patch-notes/",
    "noticias": f"{BASE}/pt-br/news/game-updates/",
    "esports": f"{BASE}/pt-br/news/esports/",
}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) lol-dark-coletor"}
MAX_NOVOS_POR_FONTE = 3


def h(url):
    return hashlib.sha256(url.rstrip("/").encode()).hexdigest()[:16]


def texto_limpo(pagina):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", pagina, flags=re.S)
    t = re.sub(r"<(h[1-4])[^>]*>", "\n## ", t)
    t = re.sub(r"<li[^>]*>", "\n- ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def titulo(pagina):
    m = re.search(r"<title>(.*?)</title>", pagina, re.S)
    return html.unescape(m.group(1)).split("|")[0].strip() if m else ""


def links(indice, fonte):
    padrao = r'/pt-br/news/(?:game-updates|esports|dev|lore|community)/[a-z0-9-]+/?'
    vistos = list(dict.fromkeys(re.findall(padrao, indice)))
    if fonte == "patch":
        vistos = [u for u in vistos if "patch" in u]
        vistos.sort(key=lambda u: [int(x) for x in re.findall(r"\d+", u)], reverse=True)
    return [BASE + u.rstrip("/") + "/" for u in vistos]


def coletar(arq=None, get=requests.get):
    arq = Path(arq or ESTADO / "itens.jsonl")
    conhecidos = {i["hash"] for i in ler_jsonl(arq)}
    novos, falhas = [], []
    for fonte, url in FONTES.items():
        try:
            r = get(url, headers=UA, timeout=30)
            r.raise_for_status()
            candidatos = [u for u in links(r.text, fonte) if h(u) not in conhecidos][:MAX_NOVOS_POR_FONTE]
        except Exception as e:
            falhas.append(f"{fonte}: {e.__class__.__name__}")
            continue
        for u in candidatos:
            try:
                p = get(u, headers=UA, timeout=30)
                p.raise_for_status()
            except Exception as e:
                falhas.append(f"{u}: {e.__class__.__name__}")
                continue
            item = {"id": h(u), "url": u, "fonte": fonte, "titulo": titulo(p.text), "texto_bruto": texto_limpo(p.text)[:60000],
                    "coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "hash": h(u)}
            novos.append(item)
            conhecidos.add(item["hash"])
    anexar_jsonl(arq, novos)
    if len(falhas) == len(FONTES):
        alertar("coleta voltou vazia: todas as fontes falharam (" + "; ".join(falhas) + ")")
    return novos, falhas


if __name__ == "__main__":
    n, f = coletar()
    print(f"{len(n)} novos; falhas: {f}")
