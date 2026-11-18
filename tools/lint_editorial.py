"""Lint editorial (spec, regras anti-slop): roda entre o roteirista e o verificador.

- frases proibidas e cara de IA (lista em comum.PROIBIDAS, via validar_roteiro)
- nada copiado da fonte: nenhuma sequência de 8+ palavras igual ao texto da fonte
- gancho_tipo diferente dos últimos 3 vídeos
"""
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

COPIA_MAX = 8


def _tokens(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9%]+", t)


def copias(narracao, fonte, n=COPIA_MAX):
    fonte_ngr = set()
    tf = _tokens(fonte)
    for i in range(len(tf) - n + 1):
        fonte_ngr.add(tuple(tf[i:i + n]))
    tn = _tokens(narracao)
    return [" ".join(tn[i:i + n]) for i in range(len(tn) - n + 1) if tuple(tn[i:i + n]) in fonte_ngr]


def lint(roteiro, textos_fonte, historico=()):
    problemas = []
    tudo = " ".join(textos_fonte.values())
    for c in roteiro["cenas"]:
        cp = copias(c["narracao"], tudo)
        if cp:
            problemas.append(f"cena {c['n']}: trecho copiado da fonte ('{cp[0]}...'); reescreva com o ângulo do canal")
    tipo = roteiro.get("gancho_tipo")
    recentes = [h.get("gancho_tipo") for h in list(historico)[-3:] if h.get("gancho_tipo")]
    if tipo and tipo in recentes:
        problemas.append(f"gancho_tipo '{tipo}' repete um dos últimos 3 vídeos ({recentes})")
    return problemas
