"""Escreve entregas/exemplo-X/notas.md e entregas/RELATORIO.md a partir de entregas/*/resumo.json.

O campo 'fraco' de cada vídeo vem de entregas/exemplo-X/fraco.md (escrito à mão depois de assistir/olhar os quadros).
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENT = RAIZ / "entregas"


def notas(r, pasta):
    linhas = [f"# Exemplo {r['letra']} — {r.get('titulo', 'não saiu')}", "",
              f"- Formato: `{r['formato']}` · variação {r['variacao']} · gancho `{r.get('gancho_tipo')}`",
              f"- Pauta: {r.get('pauta')} — {r.get('pergunta')}",
              f"- Resultado do QA: **{r['resultado']}** em {r['voltas_qa']} volta(s); duração {r.get('duracao')} s",
              f"- Voz: {(r.get('voz') or {}).get('provedor', '—')}", "", "## Notas editoriais (1 a 5)", ""]
    for e in r.get("editorial", []):
        n = e["notas"]
        linhas.append(f"- Volta {e['volta']} (crítico {e['nota_critico']}/100): gancho {n['gancho']}, ângulo {n['angulo']}, "
                      f"clareza {n['clareza']}, fecho {n['fecho']} → {'aprovada' if e['aprovado'] else 'reprovada'}")
        linhas.append(f"  - O que o espectador aprende: {e.get('o_que_aprendi', '')}")
        linhas.append(f"  - Comentário: {e.get('comentario', '')}")
    linhas += ["", "## Voltas de QA", ""]
    if not r.get("mudancas_qa"):
        linhas.append(f"- Aprovado na volta {r['voltas_qa']}, sem mudança." if r["resultado"] == "APROVADO" else "- —")
    for m in r.get("mudancas_qa", []):
        linhas.append(f"- Volta {m['volta']}: reprovou em {', '.join(m['falhas'])}. Mudança: {'; '.join(m['mudanca'])}")
    if r.get("avisos"):
        linhas.append(f"- Avisos (não reprovam): {', '.join(r['avisos'])}")
    voz = r.get("voz") or {}
    if voz:
        linhas += ["", "## Voz", "", f"- Duração {voz.get('duracao')} s; ritmo médio {(voz.get('medidas') or {}).get('ritmo_medio')} "
                   f"palavras/s; inteligibilidade (whisper x roteiro) {(voz.get('medidas') or {}).get('inteligibilidade')}",
                   f"- Falhas nas metas de voz: {voz.get('falhas') or 'nenhuma'}"]
    if r.get("descartadas"):
        linhas += ["", "## Pautas descartadas neste vídeo", ""]
        linhas += [f"- {d['id']}: {d['pergunta']} — {d['motivo']}" for d in r["descartadas"]]
    fraco = pasta / "fraco.md"
    linhas += ["", "## O que ainda acho fraco", "", fraco.read_text().strip() if fraco.exists() else "(a preencher)"]
    (pasta / "notas.md").write_text("\n".join(linhas) + "\n")


def main():
    res = []
    for p in sorted(ENT.glob("exemplo-*")):
        f = p / "resumo.json"
        if f.exists():
            r = json.loads(f.read_text())
            notas(r, p)
            res.append(r)
    tab = ["| Vídeo | Formato | Pauta | Duração | QA | Nota editorial (g/â/c/f) | Crítico |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in res:
        e = (r.get("editorial") or [{}])[-1]
        n = e.get("notas", {})
        tab.append(f"| {r['letra']} | {r['formato']} | {r.get('pauta')} | {r.get('duracao') or '—'} s | {r['resultado']} "
                   f"({r['voltas_qa']} volta/s) | {n.get('gancho', '—')}/{n.get('angulo', '—')}/{n.get('clareza', '—')}/"
                   f"{n.get('fecho', '—')} | {e.get('nota_critico', '—')} |")
    desc = [f"- {r['letra']}: {d['id']} — {d['pergunta']} ({d['motivo']})" for r in res for d in r.get("descartadas", [])]
    extra = ENT / "RELATORIO_extra.md"
    texto = ["# Relatório — vídeos de exemplo (fase 1)", "", "Nada foi publicado nem enviado ao Telegram. `config/modo.txt` não foi tocado.",
             "", "\n".join(tab), "", "## Pautas descartadas", "", "\n".join(desc) or "- nenhuma", "",
             extra.read_text().strip() if extra.exists() else ""]
    (ENT / "RELATORIO.md").write_text("\n".join(texto) + "\n")
    print((ENT / "RELATORIO.md").read_text())


if __name__ == "__main__":
    sys.exit(main())
