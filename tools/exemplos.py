"""Fase 1 (docs/SPEC.md): produz os 3 vídeos de exemplo seguindo a skill wardado-canal. Não publica nada.

Uso: .venv/bin/python tools/exemplos.py [A B C]
Saída: entregas/exemplo-<X>/{video.mp4, roteiro.json, fontes.json, laudo.json, publicacao.json, notas.md}
       entregas/RELATORIO.md é escrito à parte, a partir de entregas/*/resumo.json.
"""
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import ESTADO, RAIZ, TMP, ler_jsonl, numeros  # noqa: E402

ENTREGAS = RAIZ / "entregas"
AVISO_RIOT = ("Wardado Clips was created under Riot Games' \"Legal Jibber Jabber\" policy using assets owned by Riot "
              "Games. Riot Games does not endorse or sponsor this project.")
SPECS = {
    "A": {"formato": "patch60", "variacao": 0, "gancho_tipo": "contradicao", "series": None,
          "instrucoes": "Formato patch60 sobre o patch mais recente. Escolha NO MÁXIMO 3 mudanças e defenda um VEREDITO "
                        "já na cena 1 (o gancho é o veredito, estrutura 'contradicao'). gancho_tipo='contradicao'. "
                        "Cada número com a consequência prática para quem joga."},
    "B": {"formato": "voce-sabia", "variacao": 1, "gancho_tipo": "pergunta",
          "series": ["voce-sabia", "itens-e-coisas-removidas"],
          "instrucoes": "Formato voce-sabia. Gancho na estrutura 'pergunta com aposta' (gancho_tipo='pergunta'), "
                        "que já entrega um pedaço do fato. Use asset 'ddragon:champion/<Chave>' só para campeões que "
                        "aparecem na fonte; se a fonte não citar campeão, use 'ilustracao:champion/<Chave>' de um "
                        "campeão neutro e NÃO afirme nada sobre ele."},
    "C": {"formato": "voce-sabia", "variacao": 2, "gancho_tipo": "detalhe",
          "series": ["de-onde-vem", "o-jogo-nao-te-conta"],
          "instrucoes": "Formato voce-sabia. Gancho na estrutura 'detalhe escondido' (gancho_tipo='detalhe'). "
                        "Use asset 'ddragon:champion/<Chave>' só para campeões citados na fonte; se não houver, use "
                        "'ilustracao:champion/<Chave>' e NÃO afirme nada sobre o campeão da ilustração."},
}


def log(pasta, texto):
    print(texto, flush=True)
    with open(pasta / "log.txt", "a") as f:
        f.write(time.strftime("%H:%M:%S ") + texto + "\n")


def fontes_patch(roteiro, item):
    """Trechos da nota de patch que sustentam cada número dito no roteiro."""
    linhas = [l.strip() for l in item["texto_bruto"].splitlines() if l.strip()]
    trechos = []
    for c in roteiro["cenas"]:
        dito = " ".join(filter(None, [c["narracao"], c["texto_tela"], c.get("antes"), c.get("depois")]))
        nums = numeros(dito)
        if not nums:
            continue
        melhor = max(linhas, key=lambda l: len(nums & numeros(l)))
        if nums & numeros(melhor) and melhor not in trechos:
            trechos.append(melhor[:400])
    return [{"url": item["url"], "trechos": trechos or [item["texto_bruto"][:400]]}]


def publicacao(roteiro, fontes, tema):
    from metadados import gerar
    return gerar(roteiro, fontes, tema)


def produzir(letra, usados):
    from critico import nota_editorial
    from curar import evergreen
    from roteirizar import roteirizar
    spec = SPECS[letra]
    destino = ENTREGAS / f"exemplo-{letra}"
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    res = {"letra": letra, "formato": spec["formato"], "variacao": spec["variacao"], "descartadas": [], "voltas_qa": 0,
           "mudancas_qa": [], "editorial": [], "resultado": "NÃO SAIU"}

    # ---- pautas candidatas ----
    cands = []
    if spec["series"] is None:
        itens = [i for i in ler_jsonl(ESTADO / "itens.jsonl")
                 if i["fonte"] == "patch" and re.search(r"patch-(\d+)-(\d+)-notes", i["url"])]
        itens.sort(key=lambda i: [int(x) for x in re.findall(r"patch-(\d+)-(\d+)-notes", i["url"])[0]], reverse=True)
        cands = [("patch", itens[0])] if itens else []
    else:
        for ev in evergreen()["pautas"]:
            if ev["serie"] in spec["series"] and ev["status"] == "aberta" and ev["id"] not in usados:
                cands.append(("ev", ev))

    for tipo, alvo in cands[:5]:
        if tipo == "ev":
            from pesquisar import pesquisar
            log(destino, f"[{letra}] pesquisando {alvo['id']}: {alvo['pergunta']}")
            try:
                item = pesquisar(alvo)
            except Exception as e:
                item = None
                log(destino, f"  pesquisa falhou: {e}")
            if item is None:
                res["descartadas"].append({"id": alvo["id"], "pergunta": alvo["pergunta"],
                                           "motivo": "sem fonte oficial ou primária com trecho conferido na página"})
                log(destino, f"  descartada {alvo['id']}: sem fonte conferida")
                continue
            tema, fontes = alvo["serie"], item["fontes"]
            pid = f"{time.strftime('%Y-%m-%d')}-{alvo['id']}"
        else:
            item = alvo
            tema = re.search(r"patch-(\d+-\d+)", item["url"]).group(1).replace("-", ".")
            fontes = None
            pid = f"{time.strftime('%Y-%m-%d')}-patch-{tema.replace('.', '-')}-a"
        usados.add(alvo["id"])
        pauta = {"id": pid, "tipo": "noticia" if tipo == "patch" else "curiosidade", "formato": spec["formato"],
                 "variacao": spec["variacao"], "instrucoes": spec["instrucoes"]}

        # ---- roteiro: crítico >= 80 + nota editorial >= 4 em tudo (até 2 voltas) ----
        rot = None
        for volta in range(1, 3):
            r, rodadas = roteirizar(pauta, item, [], log=lambda t: log(destino, "  " + t))
            if r is None:
                log(destino, f"  roteiro não chegou a 80: {[x.get('nota') for x in rodadas]}")
                break
            ne = nota_editorial(r)
            res["editorial"].append({"volta": volta, "nota_critico": r["nota_critico"]["nota"], **ne})
            log(destino, f"  nota editorial volta {volta}: {ne['notas']} {'OK' if ne['aprovado'] else 'reprovada'}")
            if ne["aprovado"]:
                rot = r
                break
            pauta["comentario"] = [ne["comentario"]]
        if rot is None:
            res["descartadas"].append({"id": alvo["id"], "pergunta": alvo.get("pergunta", item.get("titulo")),
                                       "motivo": "roteiro não passou no crítico (80) ou na nota editorial (4) em 2 voltas"})
            continue

        if fontes is None:
            fontes = fontes_patch(rot, item)
        res.update({"pauta": alvo["id"], "pergunta": alvo.get("pergunta", item.get("titulo")), "tema": tema})
        pasta = TMP / pid
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "fontes.json").write_text(json.dumps(fontes, ensure_ascii=False, indent=1))

        # ---- voz (reserva) + conferência pela transcrição ----
        from legendas import legendar
        from narrar import narrar
        from qualidade import avaliar_narracao
        total = narrar(rot, pasta / "audio", "kokoro")
        leg, info = legendar(rot, pasta / "audio")
        voz = avaliar_narracao(rot, pasta / "audio", info.get("inteligibilidade"))
        res["voz"] = {"provedor": "kokoro pf_dora (reserva, assets/voz/voz.json)", "duracao": round(total, 2), **voz}
        log(destino, f"  voz: {total:.1f}s, inteligibilidade {info.get('inteligibilidade')}, {voz['falhas'] or 'ok'}")

        # ---- vídeo: render + masterização + qa.py, até 3 voltas ----
        from compor import compor
        from qa import laudo
        mp4 = pasta / "video.mp4"
        knobs = {}
        lq = None
        for v in range(1, 4):
            os.environ.update(knobs)
            compor(rot, pasta / "audio", mp4, legendas=leg)
            lq = laudo(mp4, total)
            res["voltas_qa"] = v
            falhas = [t["nome"] for t in lq["travas"] if not t["ok"]]
            log(destino, f"  QA volta {v}: {'APROVADO' if lq['aprovado'] else 'reprovado ' + str(falhas)}")
            if lq["aprovado"]:
                break
            mud = []
            if "movimento" in falhas:
                knobs["LOL_SEGMENTO"] = "1.3"
                mud.append("palco alterna gameplay/arte a cada 1,3 s (era 1,8)")
            if "loop_visual" in falhas:
                knobs["LOL_FECHO_VIDEO"] = "2.0"
                mud.append("fecho mostra o gameplay nos últimos 2,0 s (era 1,2)")
            if not mud:
                mud.append(f"sem conserto automático para {falhas}; nova volta só refaz o render")
            res["mudancas_qa"].append({"volta": v, "falhas": falhas, "mudanca": mud})
        for k in ("LOL_SEGMENTO", "LOL_FECHO_VIDEO"):
            os.environ.pop(k, None)

        # ---- entrega ----
        shutil.copy(mp4, destino / "video.mp4")
        (destino / "roteiro.json").write_text(json.dumps(rot, ensure_ascii=False, indent=1))
        (destino / "fontes.json").write_text(json.dumps(fontes, ensure_ascii=False, indent=1))
        (destino / "laudo.json").write_text(json.dumps(lq, ensure_ascii=False, indent=1))
        (destino / "publicacao.json").write_text(json.dumps(publicacao(rot, fontes, tema), ensure_ascii=False, indent=1))
        res["resultado"] = "APROVADO" if lq["aprovado"] else "REPROVADO"
        res["duracao"] = lq.get("duracao")
        res["avisos"] = [t["nome"] for t in lq["avisos"] if not t["ok"]]
        import llm
        res["escritor"] = list(llm.ESCRITOR_REGISTRO)
        llm.ESCRITOR_REGISTRO.clear()
        res["titulo"] = rot["titulo"]
        res["gancho"] = rot["cenas"][0]["narracao"]
        res["gancho_tipo"] = rot.get("gancho_tipo")
        break
    (destino / "resumo.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    letras = sys.argv[1:] or ["A", "B", "C"]
    usados = set()
    for l in letras:
        r = produzir(l, usados)
        print(json.dumps({k: r.get(k) for k in ("letra", "resultado", "pauta", "duracao", "voltas_qa")}, ensure_ascii=False))
