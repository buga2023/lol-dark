"""Registra cada volta do laço de melhoria no vault (Second-Brain) e no PROGRESSO.md do repositório.

Página: ~/Desktop/Second-Brain/wiki/projetos/wardado-melhorias.md — tabela de voltas + pontos de melhoria por área.
O vault é público: entram decisões, medidas e lógica; nada de credencial ou dado pessoal.
Uso: .venv/bin/python tools/registrar_vault.py entregas/exemplo-A [--sem-push]
"""
import json
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VAULT = Path.home() / "Desktop" / "Second-Brain"
PAGINA = VAULT / "wiki" / "projetos" / "wardado-melhorias.md"
PROGRESSO = RAIZ / "progress.md"

CABECALHO = """---
title: Wardado Clips — laço de melhoria
tipo: projeto
tags: [projeto, wardado, melhoria-continua, video]
date: 2026-11-18
fontes: []
---
# Wardado Clips — laço de melhoria

Cada vídeo produzido passa pelo `qa.py`, pelo crítico (≥ 80), pela nota editorial (≥ 4) e por um revisor independente
(Claude sem o contexto da produção). Os pontos de melhoria de cada volta ficam aqui, por área, e viram regra na skill
certa quando se repetem. Arquitetura: [wardado-clips](wardado-clips.md).

## Voltas

| Quando | Vídeo | Pauta | QA | Crítico | Editorial (g/â/c/f) | Revisor | Voz |
| --- | --- | --- | --- | --- | --- | --- | --- |
<!-- voltas -->

## Pontos de melhoria

<!-- pontos -->

## Related

- [wardado-clips](wardado-clips.md)
- [lol-dark (memória)](../../memory/projects/lol-dark.md)
"""


def registrar(pasta, push=True):
    pasta = Path(pasta)
    res = json.loads((pasta / "resumo.json").read_text())
    rev = json.loads((pasta / "revisao.json").read_text()) if (pasta / "revisao.json").exists() else {}
    if not PAGINA.exists():
        PAGINA.write_text(CABECALHO)
    s = PAGINA.read_text()
    e = (res.get("editorial") or [{}])[-1]
    n = e.get("notas", {})
    quando = time.strftime("%Y-%m-%d %H:%M")
    linha = (f"| {quando} | {res['letra']} ({res['formato']}) | {res.get('pauta')} | {res['resultado']} "
             f"({res.get('voltas_qa')}v) | {e.get('nota_critico', '—')} | {n.get('gancho', '—')}/{n.get('angulo', '—')}/"
             f"{n.get('clareza', '—')}/{n.get('fecho', '—')} | {rev.get('veredito', '—')} {rev.get('nota_0_10', '')} | "
             f"{(res.get('voz') or {}).get('provedor', '—').split(' ')[0]} |")
    s = s.replace("<!-- voltas -->", linha + "\n<!-- voltas -->")
    pts = [f"- **{p.get('area', '?')}** ({quando}, {res['letra']}): {p.get('problema', '')} → {p.get('mudanca', '')}"
           for p in rev.get("pontos", [])]
    if res.get("descartadas"):
        pts += [f"- **pauta** ({quando}, {res['letra']}): {d['id']} descartada — {d['motivo']}" for d in res["descartadas"]]
    if pts:
        s = s.replace("<!-- pontos -->", "\n".join(pts) + "\n<!-- pontos -->")
    PAGINA.write_text(s)
    with open(PROGRESSO, "a") as f:
        f.write(f"\n- {quando} {res['letra']} {res.get('pauta')}: {res['resultado']}; revisor {rev.get('veredito', '—')} "
                f"({rev.get('motivo', '')})\n")
    if push:
        idx = VAULT / "wiki" / "index.md"
        t = idx.read_text()
        if "wardado-melhorias" not in t:
            t = t.replace("- [wardado-clips](projetos/wardado-clips.md)",
                          "- [wardado-melhorias](projetos/wardado-melhorias.md): laço de melhoria do Wardado — voltas, "
                          "notas e pontos de ajuste por área.\n- [wardado-clips](projetos/wardado-clips.md)")
            idx.write_text(t)
        subprocess.run(["git", "-C", str(VAULT), "add", "wiki"], check=False)
        subprocess.run(["git", "-C", str(VAULT), "commit", "-qm", f"wardado: volta {res['letra']} {quando}"], check=False)
        subprocess.run(["git", "-C", str(VAULT), "pull", "-q", "--rebase"], check=False)
        subprocess.run(["git", "-C", str(VAULT), "push", "-q"], check=False)


if __name__ == "__main__":
    registrar(sys.argv[1], push="--sem-push" not in sys.argv)
