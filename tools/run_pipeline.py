"""Passo 11: orquestra curar -> roteirizar (loop com crítico >= 80) -> narrar -> compor -> qa -> entregar/publicar.

Modos (LOL_MODO):
  auto       publica sozinho o que passou no crítico e no QA, e avisa no Telegram (padrão)
  aprovacao  manda para o Telegram com botões e espera o clique

Flags: --dry-run (não chama Telegram nem YouTube), --ate <etapa>, --pauta <id>, --roteiro <arquivo> (pula a escrita).
No máximo 3 tentativas por pauta; falha deixa a pauta em `erro` e manda alerta.
"""
import argparse
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import ESTADO, TMP, alertar, anexar_jsonl, gravar_jsonl, ler_jsonl  # noqa: E402

ETAPAS = ["curar", "roteirizar", "narrar", "compor", "qa", "entregar"]
MAX_TENTATIVAS = 3
ORDEM_ESTADO = ["pauta", "roteirizado", "verificado", "narrado", "renderizado", "qa_ok", "aguardando_ok",
                "aprovado", "publicado"]


def salvar(pautas):
    gravar_jsonl(ESTADO / "pautas.jsonl", pautas)


def historico(pautas):
    return [{"tema": p["tema"], "gancho": p.get("gancho", ""), "formato": p["formato"]} for p in pautas[-14:]
            if p.get("gancho")]


def rodar(args):
    t_ini = time.time()
    pautas = ler_jsonl(ESTADO / "pautas.jsonl")
    itens = {i["id"]: i for i in ler_jsonl(ESTADO / "itens.jsonl")}
    modo = os.environ.get("LOL_MODO", "auto")

    # 1. escolher a pauta: a pedida, uma em erro/refazer para retomar, ou uma nova
    if args.pauta:
        pauta = next(p for p in pautas if p["id"] == args.pauta)
    else:
        pauta = next((p for p in pautas if p["estado"] in ("erro", "pauta") and p["tentativas"] < MAX_TENTATIVAS), None)
        if pauta is None and not args.roteiro:
            from curar import curar
            pauta = curar(list(itens.values()), pautas)
            if pauta is None:
                print("nenhuma pauta nova hoje")
                return 0
            pautas.append(pauta)
    if args.roteiro:
        rot = json.loads(Path(args.roteiro).read_text())
        if pauta is None or pauta["id"] != rot["id"]:
            pauta = {"id": rot["id"], "item_id": "manual", "tema": rot["id"], "formato": rot["formato"], "tipo": rot["tipo"],
                     "variacao": rot["variacao"], "criada_em": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
                     "estado": "verificado", "tentativas": 0}
            pautas.append(pauta)
    pasta = TMP / pauta["id"]
    pasta.mkdir(parents=True, exist_ok=True)
    arq_rot = pasta / "roteiro.json"
    salvar(pautas)
    print(f"pauta {pauta['id']} ({pauta['estado']}, tentativa {pauta['tentativas'] + 1})")

    try:
        # 2. roteiro: loop escritor x crítico, só segue com nota >= 80
        if args.roteiro:
            shutil.copy(args.roteiro, arq_rot) if Path(args.roteiro).resolve() != arq_rot.resolve() else None
        elif ORDEM_ESTADO.index(pauta["estado"] if pauta["estado"] in ORDEM_ESTADO else "pauta") < ORDEM_ESTADO.index("verificado") \
                or not arq_rot.exists():
            from roteirizar import roteirizar
            item = itens[pauta["item_id"]]
            rot, rodadas = roteirizar(pauta, item, historico(pautas))
            (pasta / "rodadas.json").write_text(json.dumps(rodadas, ensure_ascii=False, indent=1))
            if rot is None:
                pauta["estado"] = "rejeitado"
                pauta["rodadas"] = [r.get("nota") for r in rodadas]
                salvar(pautas)
                msg = f"pauta {pauta['id']} rejeitada: nenhum roteiro chegou a 80 ({pauta['rodadas']})"
                print(msg)
                if not args.dry_run:
                    alertar(msg)
                return 0
            arq_rot.write_text(json.dumps(rot, ensure_ascii=False, indent=1))
            pauta["gancho"] = rot["cenas"][0]["narracao"]
            pauta["nota"] = rot["nota_critico"]["nota"]
            pauta["estado"] = "verificado"
            salvar(pautas)
        if args.ate == "roteirizar":
            return 0

        rot = json.loads(arq_rot.read_text())
        # 3. narração com metas: tenta cada provedor de voz até bater ritmo, inteligibilidade e naturalidade
        from narrar import narrar, provedores
        from legendas import legendar
        from qualidade import avaliar_narracao
        aval_voz, leg = None, None
        for prov in provedores()[:3]:
            try:
                total = narrar(rot, pasta / "audio", prov)
            except Exception as e:
                print(f"voz {prov} falhou: {e}")
                continue
            if not 25 <= total <= 45:
                aval_voz = {"aprovado": False, "falhas": [f"{prov}: narração com {total:.1f}s, fora de 25-45 s"]}
                print(aval_voz["falhas"][0])
                continue
            leg, info = legendar(rot, pasta / "audio")
            aval_voz = avaliar_narracao(rot, pasta / "audio", info.get("inteligibilidade"))
            aval_voz["provedor"] = prov
            print(f"voz {prov}: {'APROVADA' if aval_voz['aprovado'] else 'reprovada'} {aval_voz['falhas']}")
            if aval_voz["aprovado"]:
                break
        if not aval_voz or not aval_voz["aprovado"]:
            raise RuntimeError(f"nenhuma voz bateu as metas: {aval_voz and aval_voz['falhas']}")
        rot["qualidade"] = {"narracao": aval_voz}
        arq_rot.write_text(json.dumps(rot, ensure_ascii=False, indent=1))
        pauta["estado"] = "narrado"
        pauta["voz"] = aval_voz["provedor"]
        salvar(pautas)
        if args.ate == "narrar":
            return 0

        from compor import compor
        mp4 = pasta / f"{rot['id']}.mp4"
        compor(rot, pasta / "audio", mp4, legendas=leg)
        pauta["estado"] = "renderizado"
        salvar(pautas)
        if args.ate == "compor":
            return 0

        from qa import laudo
        lq = laudo(mp4, total)
        (pasta / "laudo.json").write_text(json.dumps(lq, ensure_ascii=False, indent=1))
        if not lq["aprovado"]:
            raise RuntimeError(f"QA reprovou: {[k for k, v in lq['checks'].items() if not v]}")
        pauta["estado"] = "qa_ok"
        pauta["campeoes"] = sorted({c["asset"].split("/")[-1] for c in rot["cenas"] if c["asset"] != "nenhum"})
        salvar(pautas)
        print(f"qa ok: {mp4} ({lq['duracao']}s, {lq['mb']} MB)")
        # 5. juiz de vídeo: nota >= 80 ou não publica; o roteiro volta com as melhorias na próxima execução
        from qualidade import avaliar_video
        av = avaliar_video(mp4)
        rot["qualidade"]["video"] = av
        arq_rot.write_text(json.dumps(rot, ensure_ascii=False, indent=1))
        pauta["nota_video"] = av.get("nota")
        print(f"juiz de vídeo: {av.get('nota')} {'APROVADO' if av['aprovado'] else 'reprovado'}")
        if not av["aprovado"]:
            pauta["comentario"] = av.get("melhorias", [])
            pauta["estado"] = "pauta"
            pauta["tentativas"] += 1
            salvar(pautas)
            msg = f"vídeo {pauta['id']} reprovado pelo juiz ({av.get('nota')}/100); roteiro volta com as melhorias"
            print(msg)
            if not args.dry_run:
                alertar(msg)
            return 0
        if args.ate == "qa" or args.dry_run:
            print(f"dry-run concluído em {time.time() - t_ini:.0f}s")
            return 0

        from entregar import entregar
        if modo == "auto":
            from publicar import publicar
            vid, priv = publicar(rot, mp4)
            pauta["youtube_id"], pauta["estado"] = vid, ("publicado" if priv == "public" else "publicado_privado")
            salvar(pautas)
            extra = f"YouTube: https://youtu.be/{vid} ({priv})"
            if priv != "public":
                extra += "\nAPI ainda não auditada: poste este MP4 pelo app (YouTube, TikTok, Instagram)."
            entregar(rot, mp4, botoes=False, extra=extra)
        else:
            entregar(rot, mp4, botoes=True)
            pauta["estado"] = "aguardando_ok"
            salvar(pautas)
        return 0
    except Exception as e:
        pauta["tentativas"] += 1
        pauta["estado"] = "erro" if pauta["tentativas"] < MAX_TENTATIVAS else "descartado"
        pauta["ultimo_erro"] = str(e)[:500]
        salvar(pautas)
        traceback.print_exc()
        if not args.dry_run:
            alertar(f"pauta {pauta['id']} falhou (tentativa {pauta['tentativas']}/{MAX_TENTATIVAS}): {str(e)[:300]}")
        return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ate", choices=ETAPAS)
    ap.add_argument("--pauta")
    ap.add_argument("--roteiro")
    sys.exit(rodar(ap.parse_args()))


if __name__ == "__main__":
    main()
