"""Passo 3: pauta + fontes -> roteiro.json, em loop com o crítico até nota >= 80 (máx. 3 rodadas)."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import RAIZ, SCHEMA  # noqa: E402
from critico import NOTA_MINIMA, RUBRICA, avaliar  # noqa: E402

RODADAS = int(os.environ.get("LOL_RODADAS", "5"))
RODADAS_AGY = int(os.environ.get("LOL_RODADAS_AGY", "2"))  # depois disso, o Claude reescreve a partir das críticas
SKILL = RAIZ / ".claude" / "skills" / "roteiro-short-lol" / "SKILL.md"


def exemplos_ref():
    pasta = RAIZ / "data" / "exemplos_aprovados"
    out = []
    for f in sorted(pasta.glob("*.json"))[:2]:
        r = json.loads(f.read_text())
        out.append({"nota_do_critico": (r.get("nota_critico") or {}).get("nota"), "angulo": r.get("angulo"),
                    "gancho_tipo": r.get("gancho_tipo"),
                    "cenas": [{k: c.get(k) for k in ("narracao", "texto_tela", "antes", "depois", "rotulo")} for c in r["cenas"]]})
    return out


def sistema():
    s = SKILL.read_text().split("---", 2)[-1]
    ref = exemplos_ref()
    if ref:
        s += ("\n\nEXEMPLO DE ROTEIRO APROVADO PELO EDITOR (referência de padrão e de tom; NÃO copie o tema nem as frases):\n"
              + json.dumps(ref, ensure_ascii=False))
    return (s + "\n\nFOCO: um Short de 25 a 45 s defende UMA ideia. Prefira 1 ou 2 campeões com a consequência prática "
            "de cada mudança para quem joga a uma lista de 4 campeões só com números. Conte as palavras antes de devolver: "
            "60 a 110 no total. Em cena com 'antes' e 'depois', o texto_tela tem no máximo 22 caracteres."
            "\n\nCOMO O EDITOR VAI DAR NOTA (soma 100; só publica com 80+):\n"
            + "\n".join(f"- {k} ({p}): {q}" for k, (p, q) in RUBRICA.items())
            + "\nOpinião marcada como opinião ('pra mim') é desejada; só não apresente opinião como fato."
            "\n\nSCHEMA (siga exatamente; inclua 'angulo'; 'duracao' sempre null; 'asset' é "
            "'ddragon:champion/<ChaveDataDragon>' ou 'nenhum'; preencha 'gancho_tipo' (numero, contradicao, pergunta, "
            "consequencia ou detalhe) com a estrutura usada na cena 1; nas cenas de mudança de patch preencha 'antes' e 'depois' "
            "com o número curto e 'rotulo' com o que ele mede; a cena 1 e a última usam asset 'nenhum'):\n"
            + SCHEMA.read_text())


def escrever(pauta, fonte, historico, gerar=None, feedback=None, anterior=None, rodada=1):
    if gerar is None:
        from llm import ESCRITOR_REGISTRO, claude, gerar_json

        def gerar(si, u, temperatura=0.9):
            if rodada > RODADAS_AGY and os.environ.get("LOL_LLM_ESCRITOR", "agy") == "agy":
                ESCRITOR_REGISTRO.append(f"rodada {rodada}: Claude reescreve a partir das críticas")
                return claude(si, u)
            return gerar_json(si, u, temperatura=temperatura, papel="escritor")
    entrada = {"pauta": {k: pauta[k] for k in ("id", "tipo", "formato", "variacao")},
               "campeoes_evitar": pauta.get("campeoes_evitar", []),
               "fontes": [{"id": "f1", "url": fonte["url"], "coletado_em": fonte["coletado_em"], "texto_bruto": fonte["texto_bruto"][:30000]}],
               "historico": historico}
    msg = json.dumps(entrada, ensure_ascii=False)
    if pauta.get("instrucoes"):
        msg += f"\n\nINSTRUÇÕES DESTA PAUTA (obrigatórias): {pauta['instrucoes']}"
    if feedback and anterior is None:
        msg += f"\n\nO vídeo anterior desta pauta foi reprovado. Corrija: {json.dumps(feedback, ensure_ascii=False)}"
    elif feedback:
        msg += ("\n\nA versão anterior foi REPROVADA pelo editor. Reescreva corrigindo cada ponto.\n"
                f"VERSÃO ANTERIOR ({sum(len(c['narracao'].split()) for c in anterior.get('cenas', []))} palavras; "
                f"o limite é 60 a 110): {json.dumps(anterior, ensure_ascii=False)}\nPROBLEMAS: {json.dumps(feedback, ensure_ascii=False)}")
    return gerar(sistema(), msg, temperatura=0.9)


N_RASCUNHOS = int(os.environ.get("LOL_RASCUNHOS", "3"))


def _pre_nota(rot, fonte):
    """Pré-checagem barata, sem LLM: falhas determinísticas pesam muito; perto de 85 palavras é o ponto doce."""
    from critico import avaliar
    try:
        pr = avaliar(dict(rot, **{"fontes": rot.get("fontes") or [{"id": "f1", "url": "https://x", "coletado_em": "x"}]}),
                     {"f1": fonte["texto_bruto"]}, juiz=lambda *a, **k: {"criterios": {}})["problemas"]
    except Exception as e:
        pr = [str(e)]
    n = sum(len(c.get("narracao", "").split()) for c in rot.get("cenas", []))
    return len(pr) * 100 + abs(n - 85)


def melhor_de(n, pauta, fonte, historico, gerar, feedback, anterior, rodada, log):
    if n <= 1:
        return escrever(pauta, fonte, historico, gerar, feedback, anterior, rodada=rodada)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(n) as ex:
        futs = [ex.submit(escrever, pauta, fonte, historico, None, feedback, anterior, rodada) for _ in range(n)]
        cands = []
        for f in futs:
            try:
                cands.append(f.result())
            except Exception as e:
                log(f"rascunho falhou: {str(e)[:80]}")
    if not cands:
        raise RuntimeError("nenhum rascunho gerado")
    for c in cands:
        c.setdefault("id", pauta["id"]); c["formato"], c["variacao"] = pauta["formato"], pauta["variacao"]
        c["fontes"] = [{"id": "f1", "url": fonte["url"], "coletado_em": fonte["coletado_em"]}]
        for ce in c.get("cenas", []):
            ce["duracao"] = None
    cands.sort(key=lambda c: _pre_nota(c, fonte))
    log(f"rodada {rodada}: {len(cands)} rascunhos, escolhido o de menor falha ({_pre_nota(cands[0], fonte)})")
    return cands[0]


def roteirizar(pauta, fonte, historico, gerar=None, juiz=None, log=print):
    """Devolve (roteiro_aprovado | None, lista de rodadas com nota)."""
    rodadas, anterior, critica_ant = [], None, None
    feedback = pauta.get("comentario") or None  # melhorias do juiz de vídeo ou do botão Refazer
    acumulado = []
    for i in range(RODADAS):
        rot = melhor_de(N_RASCUNHOS if gerar is None else 1, pauta, fonte, historico, gerar, feedback, anterior, i + 1, log)
        if rot.get("sem_pauta"):
            rodadas.append({"rodada": i + 1, "sem_pauta": rot.get("motivo")})
            return None, rodadas
        rot["id"], rot["formato"], rot["variacao"] = pauta["id"], pauta["formato"], pauta["variacao"]
        rot["fontes"] = [{"id": "f1", "url": fonte["url"], "coletado_em": fonte["coletado_em"]}]
        for c in rot.get("cenas", []):
            c["duracao"] = None
        try:
            av = avaliar(rot, {"f1": fonte["texto_bruto"]}, juiz, historico, critica_ant)
        except Exception as e:
            av = {"nota": 0, "aprovado": False, "problemas": [f"crítico falhou: {e}"], "melhorias": []}
        rodadas.append({"rodada": i + 1, "nota": av["nota"], "problemas": av["problemas"], "melhorias": av.get("melhorias", [])})
        log(f"rodada {i + 1}: nota {av['nota']} {'APROVADO' if av['aprovado'] else 'reprovado'} {av['problemas'][:3]}")
        if av["aprovado"]:
            rot["nota_critico"] = {"nota": av["nota"], "criterios": av.get("criterios", {}), "rodada": i + 1}
            return rot, rodadas
        critica_ant = {"nota": av["nota"], "problemas": av["problemas"], "melhorias": av.get("melhorias", [])}
        acumulado.append({"rodada": i + 1, "nota": av["nota"], "pontos": av["problemas"] + av.get("melhorias", [])})
        feedback = acumulado
        anterior = rot
    return None, rodadas


if __name__ == "__main__":
    pauta = json.loads(Path(sys.argv[1]).read_text())
    fonte = json.loads(Path(sys.argv[2]).read_text())
    rot, rodadas = roteirizar(pauta, fonte, [])
    print(json.dumps({"aprovado": bool(rot), "rodadas": rodadas}, ensure_ascii=False, indent=1))
    if rot:
        Path(sys.argv[3] if len(sys.argv) > 3 else "roteiro.json").write_text(json.dumps(rot, ensure_ascii=False, indent=1))
