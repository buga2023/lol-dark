"""Gera um roteiro de referência para cada pauta de data/pautas_evergreen.json, com fonte conferida e crítico >= 80.

Não inventa: pauta sem fonte fica registrada como 'sem_fonte'; roteiro que não chega a 80 fica como 'reprovado'.
Retomável: pula o que já tem resultado em data/roteiros_referencia/indice.json.
Uso: .venv/bin/python tools/roteiros_referencia.py [id ...]
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import ESTADO, RAIZ, ler_jsonl  # noqa: E402

SAIDA = RAIZ / "data" / "roteiros_referencia"
INDICE = SAIDA / "indice.json"
DE_PATCH = {"numero-do-patch", "ganhou-perdeu", "build-do-patch"}


def main():
    from pesquisar import pesquisar
    from roteirizar import roteirizar
    SAIDA.mkdir(parents=True, exist_ok=True)
    indice = json.loads(INDICE.read_text()) if INDICE.exists() else {}
    ev = json.loads((RAIZ / "data" / "pautas_evergreen.json").read_text())
    itens = ler_jsonl(ESTADO / "itens.jsonl")
    patches = [i for i in itens if i["fonte"] == "patch" and re.search(r"patch-(\d+)-(\d+)-notes", i["url"])]
    patches.sort(key=lambda i: [int(x) for x in re.findall(r"patch-(\d+)-(\d+)-notes", i["url"])[0]], reverse=True)
    so = set(sys.argv[1:])
    for k, p in enumerate(ev["pautas"]):
        if (so and p["id"] not in so) or (not so and p["id"] in indice):
            continue
        reg = {"serie": p["serie"], "pergunta": p["pergunta"], "quando": time.strftime("%Y-%m-%d %H:%M")}
        try:
            if p["serie"] == "dados-da-semana":
                reg["status"] = "parada: sem fonte de dados autorizada (exige chave da Riot)"
            else:
                if p["serie"] in DE_PATCH:
                    item = patches[0] if patches else None
                elif p["serie"] == "agenda-competitiva":
                    import esports
                    its = esports.itens()
                    item = its[0] if its else None
                else:
                    item = pesquisar(p)
                if item is None:
                    reg["status"] = "sem_fonte"
                else:
                    pauta = {"id": f"2026-11-18-{p['id']}", "tipo": "noticia" if p["formato"] in ("patch60", "noticia") else "curiosidade",
                             "formato": p["formato"], "variacao": k % 3,
                             "instrucoes": f"Responda esta pergunta da pauta, e só ela: {p['pergunta']} "
                                           "Se a fonte não citar campeão, use asset 'ilustracao:champion/<Chave>'."}
                    rot, rodadas = roteirizar(pauta, item, [], log=lambda t: print("  " + t, flush=True))
                    reg["notas"] = [r.get("nota") for r in rodadas]
                    if rot:
                        rot["fontes_conferidas"] = item.get("fontes") or [{"url": item["url"]}]
                        (SAIDA / f"{p['id']}.json").write_text(json.dumps(rot, ensure_ascii=False, indent=1))
                        reg["status"], reg["nota"], reg["titulo"] = "aprovado", rot["nota_critico"]["nota"], rot["titulo"]
                    else:
                        reg["status"] = "reprovado (não chegou a 80)"
        except Exception as e:
            reg["status"] = f"erro: {str(e)[:120]}"
        indice[p["id"]] = reg
        INDICE.write_text(json.dumps(indice, ensure_ascii=False, indent=1))
        print(p["id"], reg["status"], reg.get("nota", ""), flush=True)


if __name__ == "__main__":
    main()
