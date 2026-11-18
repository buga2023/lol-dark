"""Passo 2: itens novos -> 1 pauta. Não repete item, campeão ou tema dos últimos 14 dias; patch tem prioridade."""
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import ESTADO, RAIZ, anexar_jsonl, ler_jsonl  # noqa: E402

JANELA_DIAS = 14
# formato -> tipo de item que ele cobre. Só entra o formato que já tem composição pronta.
# tipo de fonte -> (formato, tipo do roteiro). Só entra o formato que já tem composição pronta.
FORMATOS = {"patch": ("patch60", "noticia"), "noticias": ("noticia", "noticia"), "esports": ("noticia", "noticia"),
            "lore": ("voce-sabia", "curiosidade")}


def formato_de(fonte):
    f = FORMATOS.get(fonte)
    return f if f and (RAIZ / "compositions" / f"{f[0]}.css").exists() else None


def tema(item):
    m = re.search(r"patch-(\d+)-(\d+)", item["url"])
    return f"patch-{m.group(1)}-{m.group(2)}" if m else item["url"].rstrip("/").rsplit("/", 1)[-1]


def curar(itens=None, pautas=None, agora=None):
    itens = ler_jsonl(ESTADO / "itens.jsonl") if itens is None else itens
    pautas = ler_jsonl(ESTADO / "pautas.jsonl") if pautas is None else pautas
    agora = agora or datetime.now(timezone.utc)
    limite = agora - timedelta(days=JANELA_DIAS)
    recentes = [p for p in pautas if datetime.fromisoformat(p["criada_em"]) >= limite]
    usados = {p["item_id"] for p in pautas}
    temas = {p["tema"] for p in recentes}
    campeoes = {c for p in recentes for c in p.get("campeoes", [])}
    ultimo_formato = recentes[-1]["formato"] if recentes else None
    cands = []
    for it in itens:
        if it["id"] in usados or tema(it) in temas:
            continue
        ft = formato_de(it["fonte"])
        if not ft:
            continue
        # patch novo primeiro; depois alterna formato; depois o mais recente
        prioridade = (it["fonte"] == "patch", ft[0] != ultimo_formato, it["coletado_em"])
        cands.append((prioridade, it, ft))
    if not cands:
        return None
    cands.sort(key=lambda x: x[0], reverse=True)
    _, it, (formato, tipo) = cands[0]
    variacoes_recentes = [p.get("variacao") for p in recentes[-1:] if p["formato"] == formato]
    variacao = next(v for v in (0, 1, 2) if v not in variacoes_recentes)
    return {"id": f"{agora:%Y-%m-%d}-{tema(it)}"[:60], "item_id": it["id"], "tema": tema(it), "formato": formato,
            "tipo": tipo, "variacao": variacao, "campeoes_evitar": sorted(campeoes),
            "criada_em": agora.isoformat(timespec="seconds"), "estado": "pauta", "tentativas": 0}


if __name__ == "__main__":
    p = curar()
    if p:
        anexar_jsonl(ESTADO / "pautas.jsonl", [p])
    print(p)
