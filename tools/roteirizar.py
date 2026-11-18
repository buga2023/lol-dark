"""Passo 3: pauta + fontes -> roteiro.json, em loop com o crítico até nota >= 80 (máx. 3 rodadas)."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import RAIZ, SCHEMA  # noqa: E402
from critico import NOTA_MINIMA, avaliar  # noqa: E402

RODADAS = int(os.environ.get("LOL_RODADAS", "3"))
SKILL = RAIZ / ".claude" / "skills" / "roteiro-short-lol" / "SKILL.md"


def sistema():
    s = SKILL.read_text().split("---", 2)[-1]
    return (s + "\n\nSCHEMA (siga exatamente; inclua 'angulo'; 'duracao' sempre null; 'asset' é "
            "'ddragon:champion/<ChaveDataDragon>' ou 'nenhum'; nas cenas de mudança de patch preencha 'antes' e 'depois' "
            "com o número curto e 'rotulo' com o que ele mede; a cena 1 e a última usam asset 'nenhum'):\n"
            + SCHEMA.read_text())


def escrever(pauta, fonte, historico, gerar=None, feedback=None, anterior=None):
    if gerar is None:
        from gemini import gerar_json as gerar
    entrada = {"pauta": {k: pauta[k] for k in ("id", "tipo", "formato", "variacao")},
               "campeoes_evitar": pauta.get("campeoes_evitar", []),
               "fontes": [{"id": "f1", "url": fonte["url"], "coletado_em": fonte["coletado_em"], "texto_bruto": fonte["texto_bruto"][:30000]}],
               "historico": historico}
    msg = json.dumps(entrada, ensure_ascii=False)
    if feedback and anterior is None:
        msg += f"\n\nO vídeo anterior desta pauta foi reprovado. Corrija: {json.dumps(feedback, ensure_ascii=False)}"
    elif feedback:
        msg += ("\n\nA versão anterior foi REPROVADA pelo editor. Reescreva corrigindo cada ponto.\n"
                f"VERSÃO ANTERIOR: {json.dumps(anterior, ensure_ascii=False)}\nPROBLEMAS: {json.dumps(feedback, ensure_ascii=False)}")
    return gerar(sistema(), msg, temperatura=0.9)


def roteirizar(pauta, fonte, historico, gerar=None, juiz=None, log=print):
    """Devolve (roteiro_aprovado | None, lista de rodadas com nota)."""
    rodadas, anterior = [], None
    feedback = pauta.get("comentario") or None  # melhorias do juiz de vídeo ou do botão Refazer
    for i in range(RODADAS):
        rot = escrever(pauta, fonte, historico, gerar, feedback, anterior)
        if rot.get("sem_pauta"):
            rodadas.append({"rodada": i + 1, "sem_pauta": rot.get("motivo")})
            return None, rodadas
        rot["id"], rot["formato"], rot["variacao"] = pauta["id"], pauta["formato"], pauta["variacao"]
        rot["fontes"] = [{"id": "f1", "url": fonte["url"], "coletado_em": fonte["coletado_em"]}]
        for c in rot.get("cenas", []):
            c["duracao"] = None
        try:
            av = avaliar(rot, {"f1": fonte["texto_bruto"]}, juiz)
        except Exception as e:
            av = {"nota": 0, "aprovado": False, "problemas": [f"crítico falhou: {e}"], "melhorias": []}
        rodadas.append({"rodada": i + 1, "nota": av["nota"], "problemas": av["problemas"], "melhorias": av.get("melhorias", [])})
        log(f"rodada {i + 1}: nota {av['nota']} {'APROVADO' if av['aprovado'] else 'reprovado'} {av['problemas'][:3]}")
        if av["aprovado"]:
            rot["nota_critico"] = {"nota": av["nota"], "criterios": av.get("criterios", {}), "rodada": i + 1}
            return rot, rodadas
        feedback = av["problemas"] + av.get("melhorias", [])
        anterior = rot
    return None, rodadas


if __name__ == "__main__":
    pauta = json.loads(Path(sys.argv[1]).read_text())
    fonte = json.loads(Path(sys.argv[2]).read_text())
    rot, rodadas = roteirizar(pauta, fonte, [])
    print(json.dumps({"aprovado": bool(rot), "rodadas": rodadas}, ensure_ascii=False, indent=1))
    if rot:
        Path(sys.argv[3] if len(sys.argv) > 3 else "roteiro.json").write_text(json.dumps(rot, ensure_ascii=False, indent=1))
