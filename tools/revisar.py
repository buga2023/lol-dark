"""Revisor independente (contexto novo): veredito binário + pontos de melhoria de um vídeo entregue.

Lê entregas/<pasta>/{roteiro.json, laudo.json, notas.md} e duas folhas de quadros do vídeo; chama o Claude headless
sem nada do contexto da produção e grava entregas/<pasta>/revisao.json.
Uso: .venv/bin/python tools/revisar.py entregas/exemplo-A
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from llm import claude  # noqa: E402

SISTEMA = ("Você é um editor sênior de Shorts de games que nunca viu este canal antes. Julgue com a régua de quem "
           "rola o feed: o vídeo segura nos 2 primeiros segundos, ensina algo, parece feito por gente (não 'AI slop'), "
           "é legível no celular e fecha bem? Use as skills do canal como régua: .claude/skills/wardado-canal, "
           "edicao-wardado, roteiro-short-lol. Seja específico e acionável: cada ponto diz a área (roteiro, edicao, voz, "
           "som, pauta, legenda), o problema visto e a mudança concreta. Não elogie.")


def folhas(mp4, pasta):
    """Folhas de quadros direto do MP4 (sem depender do projeto HyperFrames, que pode ter sido apagado)."""
    pasta.mkdir(exist_ok=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                               capture_output=True, text=True).stdout or 30)
    saidas = []
    for nome, tempos in (("gancho", [0, 0.7, 1.5, 2.2]), ("geral", [dur * i / 9 for i in range(9)] + [dur - 0.05])):
        arqs = []
        for i, t in enumerate(tempos):
            a = pasta / f"{nome}_{i:02d}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1",
                            "-vf", "scale=270:-1", str(a)])
            arqs.append(a)
        sheet = pasta / f"{nome}.jpg"
        cols = 4 if nome == "gancho" else 5
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", str(pasta / f"{nome}_*.jpg"),
                        "-filter_complex", f"tile={cols}x{(len(arqs) + cols - 1) // cols}", str(sheet)])
        saidas.append(sheet)
    return saidas


def revisar(pasta):
    pasta = Path(pasta)
    rot = json.loads((pasta / "roteiro.json").read_text())
    laudo = json.loads((pasta / "laudo.json").read_text())
    sh = folhas(pasta / "video.mp4", pasta / "quadros")
    usuario = (f"Leia as imagens {sh[0]} (gancho: 0; 0,7; 1,5; 2,2 s) e {sh[1]} (10 quadros do vídeo inteiro).\n"
               f"ROTEIRO: {json.dumps({k: rot[k] for k in ('titulo', 'angulo', 'cenas')}, ensure_ascii=False)}\n"
               f"LAUDO TÉCNICO: {json.dumps({'aprovado': laudo['aprovado'], 'travas': laudo['travas'], 'avisos': laudo['avisos']}, ensure_ascii=False)[:3000]}\n"
               f"A voz deste vídeo é: {rot.get('voz')}.\n"
               "Responda JSON: {\"veredito\": \"aprovado\" ou \"reprovado\", \"motivo\": \"uma frase\", "
               "\"nota_0_10\": n, \"pontos\": [{\"area\": \"...\", \"problema\": \"...\", \"mudanca\": \"...\"}]}")
    raiz = Path(__file__).resolve().parent.parent
    r = claude(SISTEMA, usuario, ferramentas="Read", diretorio=raiz)
    (pasta / "revisao.json").write_text(json.dumps(r, ensure_ascii=False, indent=1))
    return r


if __name__ == "__main__":
    print(json.dumps(revisar(sys.argv[1]), ensure_ascii=False, indent=1))
