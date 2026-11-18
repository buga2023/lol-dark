"""Crítico: nota de 0 a 100 para o roteiro. Só passa com >= 80 e sem nenhum problema determinístico.

Duas camadas:
1. Determinística (Python): schema, palavras, frases, proibidas, números com fonte. Qualquer falha = nota 0.
2. Juiz (Gemini, temperatura 0): rubrica fixa abaixo, pesos somam 100.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from verificar import verificar  # noqa: E402

NOTA_MINIMA = 80
RUBRICA = {
    "gancho": (20, "A cena 1 funciona sozinha, entrega um pedaço do fato (não só promete) e prende em 2 segundos?"),
    "angulo": (15, "Existe um ângulo próprio (consequência para quem joga ou surpresa) e ele aparece na narração?"),
    "aprendizado": (15, "Um jogador Ouro aprende algo concreto que não sabia?"),
    "fidelidade": (15, "Tudo o que é dito é sustentado pelo texto da fonte, sem exagero nem extrapolação?"),
    "autenticidade": (15, "Zero cara de 'AI slop': nada de clichê, adjetivo vazio, frase genérica que serviria a qualquer "
                          "tema ou estrutura de lista previsível. Tem opinião marcada e detalhe que só quem joga notaria?"),
    "voz": (10, "Soa como uma amiga que joga explicando no Discord, português do Brasil falado e natural?"),
    "ritmo": (5, "Frases curtas, uma ideia por frase, um fato novo por cena?"),
    "loop": (5, "A última cena responde ao gancho e emenda de volta na primeira?"),
}
SISTEMA = ("Você é editor-chefe de um canal de Shorts de League of Legends em português. Avalie o roteiro com rigor. "
           "Calibração da soma: 80 ou mais = você publicaria hoje sem mudança relevante; 60 a 79 = bom, mas com falhas que "
           "um editor corrigiria; abaixo de 60 = fraco. Opinião marcada como opinião ('pra mim', 'minha aposta') é "
           "permitida e desejada; só puna opinião apresentada como fato. Se receber a sua crítica anterior, confira ponto a "
           "ponto o que foi resolvido e mantenha a mesma direção editorial; não troque de direção sem motivo forte. Para cada critério dê uma nota de 0 até o peso indicado e uma frase de justificativa. "
           "Responda só JSON: {\"criterios\": {\"<nome>\": {\"nota\": n, \"motivo\": \"...\"}}, \"melhorias\": [\"...\"]}")


def avaliar(roteiro, textos_fonte, juiz=None, historico=(), critica_anterior=None):
    from lint_editorial import lint
    problemas = lint(roteiro, textos_fonte, historico) + verificar(roteiro, textos_fonte)
    if problemas:
        return {"nota": 0, "aprovado": False, "problemas": problemas, "criterios": {}, "melhorias": problemas}
    if juiz is None:
        from llm import gerar_json
        juiz = gerar_json
    rub = "\n".join(f"- {k} (peso {p}): {q}" for k, (p, q) in RUBRICA.items())
    fontes = "\n\n".join(f"[{k}]\n{v[:12000]}" for k, v in textos_fonte.items())
    usuario = f"RUBRICA:\n{rub}\n\nROTEIRO:\n{json.dumps(roteiro, ensure_ascii=False)}\n\nFONTES:\n{fontes}"
    if critica_anterior:
        usuario += f"\n\nSUA CRÍTICA DA VERSÃO ANTERIOR (confira o que foi resolvido):\n{json.dumps(critica_anterior, ensure_ascii=False)}"
    r = juiz(SISTEMA, usuario, temperatura=0)
    crit = r.get("criterios", {})
    nota = 0
    for k, (peso, _) in RUBRICA.items():
        nota += max(0, min(peso, float(crit.get(k, {}).get("nota", 0))))
    nota = round(nota)
    return {"nota": nota, "aprovado": nota >= NOTA_MINIMA, "problemas": [], "criterios": crit,
            "melhorias": r.get("melhorias", [])}
