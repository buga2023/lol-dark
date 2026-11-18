#!/usr/bin/env python3
"""QA técnico de um Short do Wardado Clips.

Uso: python tools/qa.py video.mp4 [--json laudo.json] [--esperada SEGUNDOS]
Sai com código 0 se todas as travas passam, 1 se alguma reprova.
Avisos não reprovam, mas entram no laudo para o loop de correção.
Requer ffmpeg/ffprobe no PATH e Pillow.
"""
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from PIL import Image

# Limites. Ajuste aqui, nunca dentro das funções.
LARGURA, ALTURA, FPS = 1080, 1920, 30
DURACAO = (25.0, 45.0)            # segundos
TOLERANCIA_CENAS = 0.5            # duração do MP4 x soma das cenas
TAMANHO_MAX_MB = 50               # teto do Telegram para bot
PRETO_MAX = 0.5                   # segundos de tela preta tolerados
BITRATE_MIN = 6_000_000           # bits/s do vídeo (aviso: vídeo parado comprime muito)
LUFS = (-15.0, -13.0)             # volume integrado
PICO_MAX = -1.0                   # dBTP
JANELA = 2.0                      # segundos sem mudança visual tolerados
MOVIMENTO_MIN = 0.003             # score médio de mudança por janela
JANELAS_PARADAS_MAX = 0.25        # fração de janelas abaixo do mínimo
CAUDA_MAX_QUEDA = 6.0             # dB que o último 0,8 s pode cair
SSIM_LOOP_MIN = 0.75              # primeiro x último quadro
BRILHO_MIN = -18.0                # dB: energia acima de 8 kHz relativa ao total (aviso)
COBERTURA_MIN = 0.40              # fração da área segura ocupada (aviso)
SEGURA = (0.15, 0.75, 0.0, 0.88)  # topo, base, esquerda, direita


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.stdout + p.stderr


def ffmpeg(video, *filtros, pre=()):
    return run(["ffmpeg", "-hide_banner", "-nostats", *pre, "-i", video, *filtros, "-f", "null", "-"])


def probe(video):
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", video])
    return json.loads(out)


def media_volume(video, filtro="anull", pre=()):
    out = ffmpeg(video, "-vn", "-af", f"{filtro},volumedetect", pre=pre)
    m = re.search(r"mean_volume: (-?[\d.]+) dB", out)
    return float(m.group(1)) if m else None


def quadro(video, destino, pre):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *pre, "-i", video, "-frames:v", "1", "-update", "1", destino])
    return destino


def cobertura_area_segura(caminho):
    im = Image.open(caminho).convert("RGB").resize((270, 480))
    w, h = im.size
    topo, base, esq, dir_ = SEGURA
    caixa = im.crop((int(w * esq), int(h * topo), int(w * dir_), int(h * base)))
    b = caixa.tobytes()
    px = [(b[i], b[i + 1], b[i + 2]) for i in range(0, len(b), 3)]
    fundo = Counter((r // 16, g // 16, b // 16) for r, g, b in px).most_common(1)[0][0]
    fr, fg, fb = (c * 16 + 8 for c in fundo)
    ocupado = sum(1 for r, g, b in px if abs(r - fr) + abs(g - fg) + abs(b - fb) > 60)
    return ocupado / len(px)


def avaliar(video, esperada=None):
    """Roda todas as travas e avisos; devolve o laudo (nunca sai do processo)."""
    video = str(video)
    laudo = {"video": video, "travas": [], "avisos": []}

    def trava(nome, ok, valor, esperado, conserto):
        laudo["travas"].append({"nome": nome, "ok": bool(ok), "valor": valor, "esperado": esperado, "conserto": conserto})

    def aviso(nome, ok, valor, esperado, conserto):
        laudo["avisos"].append({"nome": nome, "ok": bool(ok), "valor": valor, "esperado": esperado, "conserto": conserto})

    info = probe(video)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    num, den = v["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    laudo["duracao"] = round(dur, 2)
    laudo["mb"] = round(Path(video).stat().st_size / 1e6, 1)

    trava("formato", (v["width"], v["height"]) == (LARGURA, ALTURA) and abs(fps - FPS) < 0.01,
          f'{v["width"]}x{v["height"]} @ {fps:g} fps', f"{LARGURA}x{ALTURA} @ {FPS} fps",
          "Corrigir dimensões e fps da composição.")
    trava("duracao", DURACAO[0] <= dur <= DURACAO[1], round(dur, 2), f"{DURACAO[0]:g} a {DURACAO[1]:g} s",
          "Devolver ao roteirista para cortar ou completar o texto.")
    if esperada is not None:
        trava("duracao_cenas", abs(dur - esperada) <= TOLERANCIA_CENAS, round(dur, 2), f"{esperada:.2f} ± {TOLERANCIA_CENAS} s",
              "Render cortou ou esticou: conferir data-duration do root e das cenas.")
    trava("tamanho", laudo["mb"] < TAMANHO_MAX_MB, f'{laudo["mb"]} MB', f"< {TAMANHO_MAX_MB} MB",
          "Reduzir bitrate na masterização (maxrate) para caber no Telegram.")
    out = ffmpeg(video, "-an", "-vf", f"blackdetect=d={PRETO_MAX}:pix_th=0.10")
    pretos = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", out)
    trava("tela_preta", not pretos, pretos or "nenhum", f"nenhum trecho > {PRETO_MAX} s",
          "Cena sem conteúdo: conferir data-start/duração das cenas e mídia que não carregou.")
    br = int(v.get("bit_rate") or 0)
    aviso("bitrate_video", br >= BITRATE_MIN, f"{br / 1e6:.1f} Mbps", f">= {BITRATE_MIN / 1e6:g} Mbps",
          "Bitrate baixo indica vídeo parado ou render em rascunho: conferir --quality high e a trava de movimento.")
    trava("tem_audio", a is not None, bool(a), True, "Refazer a narração; o render saiu sem faixa de áudio.")
    if a is None:
        return fechar(laudo)

    # Volume
    out = ffmpeg(video, "-vn", "-af", "ebur128=peak=true")
    resumo = out[out.rfind("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", resumo).group(1))
    pico = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", resumo).group(1))
    trava("volume", LUFS[0] <= lufs <= LUFS[1], f"{lufs:.1f} LUFS", f"{LUFS[0]:g} a {LUFS[1]:g} LUFS",
          "Rodar a masterização (loudnorm I=-14).")
    trava("pico", pico <= PICO_MAX, f"{pico:.1f} dBTP", f"<= {PICO_MAX:g} dBTP", "Rodar a masterização (TP=-1.5).")

    # Brilho da voz
    total = media_volume(video)
    agudos = media_volume(video, "highpass=f=8000")
    if total is not None and agudos is not None:
        rel = agudos - total
        aviso("brilho_voz", rel >= BRILHO_MIN, f"{rel:.1f} dB", f">= {BRILHO_MIN:g} dB",
              "Voz abafada: usar modelo de voz com saída mais rica ou realce leve de agudos na masterização.")

    # Loop de áudio: o fim não pode apagar
    cauda = media_volume(video, pre=("-sseof", "-0.8"))
    if total is not None and cauda is not None:
        queda = total - cauda
        trava("loop_audio", queda <= CAUDA_MAX_QUEDA, f"cauda {queda:.1f} dB abaixo da média", f"<= {CAUDA_MAX_QUEDA:g} dB",
              "Tirar o fade final e encostar a última palavra no corte; trilha contínua até o último quadro.")

    # Movimento por janela
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-an", "-vf",
               "select='gte(scene,0)',metadata=print:file=-", "-f", "null", "-"])
    scores = [float(x) for x in re.findall(r"scene_score=([\d.]+)", out)]
    n = int(JANELA * fps)
    janelas = [sum(scores[i:i + n]) / n for i in range(0, len(scores) - n + 1, n)]
    paradas = [round(i * JANELA, 1) for i, s in enumerate(janelas) if s < MOVIMENTO_MIN]
    frac = len(paradas) / max(1, len(janelas))
    trava("movimento", frac <= JANELAS_PARADAS_MAX, f"{len(paradas)}/{len(janelas)} janelas paradas, inícios em {paradas}",
          f"<= {JANELAS_PARADAS_MAX:.0%} das janelas de {JANELA:g} s",
          "Adicionar movimento nas cenas listadas: zoom lento na arte, entrada animada do número, troca de enquadramento.")

    # Loop visual e ocupação
    with tempfile.TemporaryDirectory() as tmp:
        primeiro = quadro(video, f"{tmp}/a.png", ("-ss", "0"))
        ultimo = quadro(video, f"{tmp}/b.png", ("-sseof", "-0.1"))
        out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", primeiro, "-i", ultimo, "-lavfi", "ssim", "-f", "null", "-"])
        m = re.search(r"All:([\d.]+)", out)
        ssim = float(m.group(1)) if m else 0.0
        trava("loop_visual", ssim >= SSIM_LOOP_MIN, round(ssim, 3), f">= {SSIM_LOOP_MIN:g}",
              "Fazer o último quadro repetir o layout do primeiro.")
        cobs = []
        for i in range(1, 6):
            f = quadro(video, f"{tmp}/c{i}.png", ("-ss", f"{dur * i / 6:.2f}"))
            cobs.append(cobertura_area_segura(f))
        cob = sum(cobs) / len(cobs)
        aviso("ocupacao", cob >= COBERTURA_MIN, f"{cob:.0%} da área segura", f">= {COBERTURA_MIN:.0%}",
              "Tela vazia: aumentar arte, número e legenda para ocupar a área segura inteira.")

    return fechar(laudo)


def fechar(laudo):
    laudo["aprovado"] = all(t["ok"] for t in laudo["travas"])
    laudo["consertos"] = [t["conserto"] for t in laudo["travas"] + laudo["avisos"] if not t["ok"]]
    # visão compacta usada pela esteira e pelos testes
    laudo["checks"] = {t["nome"]: t["ok"] for t in laudo["travas"]}
    return laudo


def laudo(mp4, duracao_esperada=None):
    """Compatibilidade com a esteira: mesmo laudo, sem imprimir nem sair."""
    return avaliar(mp4, duracao_esperada)


def imprimir(laudo_):
    for grupo, rotulo in (("travas", "TRAVA"), ("avisos", "AVISO")):
        for t in laudo_[grupo]:
            print(f'{"ok " if t["ok"] else "FALHA"} {rotulo:5} {t["nome"]:14} {t["valor"]}  (esperado {t["esperado"]})')
    print("\nAPROVADO" if laudo_["aprovado"] else "\nREPROVADO")
    for c in laudo_["consertos"]:
        print(" -", c)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    esperada = float(sys.argv[sys.argv.index("--esperada") + 1]) if "--esperada" in sys.argv else None
    l = avaliar(sys.argv[1], esperada)
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(l, ensure_ascii=False, indent=2))
    imprimir(l)
    sys.exit(0 if l["aprovado"] else 1)


if __name__ == "__main__":
    main()
