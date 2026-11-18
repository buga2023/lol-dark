"""Pautas perenes: o Claude pesquisa a pergunta na web; o código confere a fonte antes de virar roteiro.

Regra (data/pautas_evergreen.json): nunca responder de memória. Só segue se:
- cada URL é de domínio oficial ou primário (DOMINIOS);
- a página baixada por nós contém de verdade os trechos citados pelo Claude.
Sem isso: None (pauta 'sem_fonte').
"""
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

sys.path.insert(0, str(Path(__file__).parent))
from coletar import UA, texto_limpo  # noqa: E402

DOMINIOS = ("leagueoflegends.com", "riotgames.com", "lolesports.com", "wiki.leagueoflegends.com",
            "ddragon.leagueoflegends.com", "cblol.gg")
SISTEMA = ("Você é pesquisador de um canal de League of Legends. Responda a pergunta SOMENTE com o que encontrar em "
           "fontes oficiais da Riot (leagueoflegends.com, universe.leagueoflegends.com, riotgames.com, lolesports.com, "
           "cblol.gg) ou na wiki da comunidade que a Riot indica (wiki.leagueoflegends.com). Use WebSearch e WebFetch. "
           "Nunca responda de memória. Para cada fonte, copie de 1 a 3 trechos LITERAIS da página (como aparecem nela) "
           "que sustentam a resposta. Se não achar fonte desses domínios, devolva {\"sem_fonte\": true, \"motivo\": \"...\"}. "
           "Formato: {\"resposta\": \"...\", \"fontes\": [{\"url\": \"https://...\", \"trechos\": [\"...\"]}]}")


def _norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%]+", " ", t)).strip()


def dominio_ok(url):
    host = urlparse(url).hostname or ""
    return any(host == d or host.endswith("." + d) for d in DOMINIOS)


class _R:
    def __init__(self, text, code):
        self.text, self.status_code = text, code

    def raise_for_status(self):
        if self.status_code != 200:
            raise RuntimeError(f"HTTP {self.status_code}")


def baixar(url, headers=None, timeout=30):
    """Baixa com curl: a wiki oficial devolve 403 ao cliente Python (requests) e 200 ao curl."""
    import subprocess
    r = subprocess.run(["curl", "-sL", "--max-time", str(timeout), "-A", "WardadoClips-fontes/1.0", "-w", "\n%{http_code}", url],
                       capture_output=True, text=True, timeout=timeout + 10)
    corpo, _, code = r.stdout.rpartition("\n")
    return _R(corpo, int(code or 0))


def conferir(fontes, get=baixar):
    """Baixa cada fonte e mantém só as que contêm de fato algum trecho citado. Devolve [(url, texto)]."""
    ok = []
    for f in fontes:
        url = f.get("url", "")
        if not dominio_ok(url):
            continue
        try:
            r = get(url, headers=UA, timeout=30)
            r.raise_for_status()
        except Exception:
            continue
        texto = texto_limpo(r.text) if "<" in r.text[:500] else r.text
        alvo = _norm(texto)
        bons = [t for t in f.get("trechos", []) if len(_norm(t)) >= 20 and _norm(t) in alvo]
        if bons:
            ok.append((url, texto[:30000], bons))
    return ok


def pesquisar(pauta_ev, chamar=None, get=baixar):
    if chamar is None:
        from llm import claude
        chamar = lambda s, u: claude(s, u, ferramentas="WebSearch,WebFetch", timeout=1200)  # noqa: E731
    r = chamar(SISTEMA, f"PERGUNTA: {pauta_ev['pergunta']}")
    if r.get("sem_fonte") or not r.get("fontes"):
        return None
    conf = conferir(r["fontes"], get)
    if not conf:
        return None
    url = conf[0][0]
    texto = f"PERGUNTA DA PAUTA: {pauta_ev['pergunta']}\n\n" + "\n\n".join(f"[FONTE {u}]\n{t}" for u, t, _ in conf)
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {"id": pauta_ev["id"], "url": url, "fonte": "evergreen", "titulo": pauta_ev["pergunta"], "texto_bruto": texto,
            "coletado_em": agora, "hash": hashlib.sha256(url.encode()).hexdigest()[:16],
            "urls": [u for u, _, _ in conf], "fontes": [{"url": u, "trechos": tr} for u, _, tr in conf],
            "resposta": r.get("resposta", "")}


if __name__ == "__main__":
    ev = json.loads((Path(__file__).parent.parent / "data" / "pautas_evergreen.json").read_text())
    p = next(x for x in ev["pautas"] if x["id"] == sys.argv[1])
    it = pesquisar(p)
    print(json.dumps({k: v for k, v in (it or {"sem_fonte": True}).items() if k != "texto_bruto"}, ensure_ascii=False, indent=1))
