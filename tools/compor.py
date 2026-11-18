"""Passo 6: roteiro + áudios + artes -> projeto HyperFrames -> lint -> MP4.

O modelo nunca escreve HTML: este script preenche o formato com os dados do roteiro,
então o render é determinístico (mesmo roteiro e mesmos áudios, mesmo vídeo).
Regras visuais: .claude/skills/video-short-lol/SKILL.md.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from comum import RAIZ, TMP  # noqa: E402
from legendas import legendar  # noqa: E402

COMP = RAIZ / "compositions"
DDRAGON = "https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{}_0.jpg"
ARTE_CACHE = TMP / "assets"
MAX_PALAVRAS_LEGENDA = 2
e = html.escape
# olho da marca Wardado (desenhado em SVG, mesma geometria do avatar)
LOGO = ('<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round">'
        '<path d="M50 6v12M24 14l7 10M76 14l-7 10"/><path d="M8 46Q50 10 92 46Q50 82 8 46Z"/>'
        '<circle cx="50" cy="46" r="15"/><path d="M50 39l7 7-7 7-7-7z" fill="currentColor" stroke="none"/>'
        '<path d="M44 68h12L50 98z" fill="currentColor" stroke="none"/></svg>')


def baixar_arte(campeao):
    ARTE_CACHE.mkdir(parents=True, exist_ok=True)
    dest = ARTE_CACHE / f"{campeao}.jpg"
    if not dest.exists():
        r = requests.get(DDRAGON.format(campeao), timeout=60)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


def campeao(asset):
    return asset.split("/", 1)[1] if asset.startswith("ddragon:champion/") else None


def grupos_legenda(palavras):
    """2 a 3 palavras por vez, quebrando em pontuação."""
    grupos, atual = [], []
    for p in palavras:
        atual.append(p)
        if len(atual) >= MAX_PALAVRAS_LEGENDA or re.search(r"[.,:;!?]$", p["w"]):
            grupos.append(atual)
            atual = []
    if atual:
        if len(atual) == 1 and grupos and len(grupos[-1]) < 4:
            grupos[-1].extend(atual)
        else:
            grupos.append(atual)
    return grupos


def eh_chave(palavra, chaves):
    w = re.sub(r"[^\wÀ-ÿ'%]", "", palavra).lower()
    return bool(re.search(r"\d", w)) or w in chaves


def cena_tiras(sid, c, campeoes, t0, d, variacao, tl):
    tiras = "".join(f'<div class="tira"><img id="{sid}-t{i}" src="assets/{x}.jpg" alt=""></div>'
                    for i, x in enumerate(campeoes))
    partes = [f'<div class="tiras">{tiras}</div>',
              f'<h1 id="{sid}-man" class="manchete grande" data-layout-allow-overlap>{e(c["texto_tela"])}</h1>']
    if c.get("rotulo"):
        partes.append(f'<div id="{sid}-selo" class="selo">{e(c["rotulo"])}</div>')
        tl.append(f'tl.fromTo("#{sid}-selo",{{scale:2.2,opacity:0,rotation:-8}},{{scale:1,opacity:1,rotation:-3,duration:.22,ease:"back.out(2)"}},{t0 + .5:.3f});')
    # abertura varia por variação; o quadro 0 já mostra a manchete (skill: primeiro quadro diz o assunto)
    if variacao == 0:
        tl.append(f'tl.fromTo("#{sid}-man",{{scale:1.07,transformOrigin:"left top"}},{{scale:1,duration:.5,ease:"expo.out"}},{t0:.3f});')
    elif variacao == 1:
        tl.append(f'tl.fromTo("#{sid}-man",{{x:-14}},{{x:0,duration:.12,ease:"steps(3)"}},{t0:.3f});')
    else:
        tl.append(f'tl.fromTo("#{sid}-man",{{clipPath:"inset(0 18% 0 0)"}},{{clipPath:"inset(0 0% 0 0)",duration:.45,ease:"steps(6)"}},{t0:.3f});')
    for i in range(len(campeoes)):
        tl.append(f'tl.fromTo("#{sid}-t{i}",{{yPercent:{-10 + 4 * (i % 2)},scale:1.25}},{{yPercent:{2 - 4 * (i % 2)},scale:1.12,duration:{d:.2f},ease:"none"}},{t0:.3f});')
    return partes


def trilha(seed, dur, destino):
    """Trilha baixa sob a voz. Usa assets/musica/*.mp3|wav (escolha estável por vídeo) ou sintetiza um pad suave."""
    pasta = RAIZ / "assets" / "musica"
    faixas = sorted([*pasta.glob("*.mp3"), *pasta.glob("*.wav")]) if pasta.exists() else []
    if faixas:
        f = faixas[sum(map(ord, seed)) % len(faixas)]
        filtro = f"afade=t=in:d=1,afade=t=out:st={max(0, dur - 1.5):.2f}:d=1.5"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", str(f), "-t", f"{dur:.2f}", "-af", filtro,
                        "-ar", "44100", "-ac", "2", str(destino)], check=True)
        return
    # pad em lá menor com 9ª: senos lentos com tremolo, filtro passa-baixa e fades
    notas = [110.0, 164.81, 220.0, 261.63, 329.63, 493.88]
    soma = "+".join(f"{0.16 if i < 2 else 0.1}*sin(2*PI*{f}*t)*(0.75+0.25*sin(2*PI*{0.07 + 0.03 * i}*t))"
                    for i, f in enumerate(notas))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"aevalsrc={soma}:s=44100:d={dur:.2f}",
                    "-af", f"lowpass=f=1400,aecho=0.8:0.7:120|240:0.25|0.15,afade=t=in:d=1.2,"
                           f"afade=t=out:st={max(0, dur - 1.5):.2f}:d=1.5,volume=0.8", "-ac", "2", str(destino)], check=True)


def montar(roteiro, pasta_audio, destino, legendas=None):
    destino = Path(destino)
    if destino.exists():
        shutil.rmtree(destino)
    (destino / "assets").mkdir(parents=True)
    shutil.copy(COMP / "vendor" / "gsap.min.js", destino / "assets" / "gsap.min.js")
    css = (COMP / "wardado.css").read_text() + (COMP / f"{roteiro['formato']}.css").read_text()
    var = int(roteiro["variacao"])

    cenas = roteiro["cenas"]
    campeoes = list(dict.fromkeys(ch for c in cenas if (ch := campeao(c["asset"]))))
    for ch in campeoes:
        shutil.copy(baixar_arte(ch), destino / "assets" / f"{ch}.jpg")
    chaves = {x.lower() for x in campeoes}
    chaves |= {w.lower() for c in cenas for w in re.findall(r"[A-Za-zÀ-ÿ']+", c["texto_tela"].split("·")[0]) if len(w) > 3}
    if legendas is None:
        legendas, _ = legendar(roteiro, pasta_audio)

    rot1 = cenas[0].get("rotulo") or ""
    cabecalho = rot1 or "wardado clips"
    marca = rot1.split()[-1] if rot1 else ""
    corpo, audios, tl = [], [], []
    t0, z = 0.0, 1
    for c in cenas:
        n, d = c["n"], c["duracao"]
        sid = f"c{n}"
        shutil.copy(Path(pasta_audio) / f"cena{n}.wav", destino / "assets" / f"cena{n}.wav")
        audios.append(f'<audio id="voz{n}" class="clip" src="assets/cena{n}.wav" data-start="{t0:.3f}" '
                      f'data-duration="{d:.3f}" data-track-index="2" data-volume="1"></audio>')
        partes = ['<div class="fundo"></div>', f'<div class="marca" data-layout-ignore>{e(marca)}</div>',
                  f'<div class="cab"><span class="logo">{LOGO}<span>wardado clips</span></span><span>{e(cabecalho)}</span>'
                  f'<b>{n:02d}/{len(cenas):02d}</b></div>']
        ch = campeao(c["asset"])
        if not ch:
            # gancho e fecho usam o mesmo quadro de tiras: o loop emenda sem salto
            partes += cena_tiras(sid, c, campeoes, t0, d, var, tl)
        else:
            partes.append(f'<div class="foto"><img id="{sid}-img" src="assets/{ch}.jpg" alt=""></div>')
            tl.append(f'tl.fromTo("#{sid}-img",{{scale:1.2,xPercent:-3}},{{scale:1.05,xPercent:3,duration:{d:.2f},ease:"none"}},{t0:.3f});')
            partes.append(f'<h1 id="{sid}-man" class="manchete">{e(c["texto_tela"])}</h1>')
            tl.append(f'tl.fromTo("#{sid}-man",{{xPercent:-6,opacity:0}},{{xPercent:0,opacity:1,duration:.25,ease:"expo.out"}},{t0:.3f});')
            if c.get("antes") and c.get("depois"):
                partes.append(f'<div class="numeros"><span class="antes" id="{sid}-antes">{e(c["antes"])}'
                              f'<i class="risco" id="{sid}-risco"></i></span><span class="seta" id="{sid}-seta">→</span>'
                              f'<span class="depois" id="{sid}-dep">{e(c["depois"])}</span></div>')
                # o número novo entra quando é falado (skill: número aparece no momento em que é dito)
                tb = t0 + 0.6
                for w in legendas.get(n, []):
                    if c["depois"].rstrip("%") in w["w"]:
                        tb = t0 + max(0.4, w["s"])
                        break
                tl.append(f'tl.fromTo("#{sid}-antes",{{opacity:0}},{{opacity:1,duration:.15}},{t0 + .25:.3f});')
                tl.append(f'tl.fromTo("#{sid}-risco",{{scaleX:0}},{{scaleX:1,duration:.2,ease:"power3.in"}},{tb - .3:.3f});')
                tl.append(f'tl.fromTo("#{sid}-seta",{{opacity:0,x:-20}},{{opacity:1,x:0,duration:.12}},{tb - .12:.3f});')
                tl.append(f'tl.fromTo("#{sid}-dep",{{scale:1.9,opacity:0}},{{scale:1,opacity:1,duration:.22,ease:"back.out(1.6)"}},{tb:.3f});')
                tl.append(f'tl.fromTo("#{sid}-dep",{{rotation:-4}},{{rotation:0,duration:.3,ease:"elastic.out(1,.4)"}},{tb + .18:.3f});')
                audios.append(f'<audio id="baque{n}" class="clip" src="assets/baque.wav" data-start="{tb:.3f}" '
                              f'data-duration="0.4" data-track-index="3" data-volume="0.55"></audio>')
            if c.get("rotulo"):
                partes.append(f'<div class="rotulo" id="{sid}-rot">{e(c["rotulo"])}</div>')
                tl.append(f'tl.fromTo("#{sid}-rot",{{clipPath:"inset(0 100% 0 0)"}},{{clipPath:"inset(0 0% 0 0)",duration:.3,ease:"power2.out"}},{t0 + .45:.3f});')
        # legendas karaokê: grupo aparece no início da 1ª palavra; cada palavra acende quando é dita
        legs = []
        grupos = grupos_legenda(legendas.get(n, []))
        for gi, g in enumerate(grupos):
            gs = g[0]["s"]
            ge = grupos[gi + 1][0]["s"] if gi + 1 < len(grupos) else d - 0.05
            spans = []
            for wi, w in enumerate(g):
                wid = f"{sid}-g{gi}w{wi}"
                cls = ' class="chave"' if eh_chave(w["w"], chaves) else ""
                spans.append(f'<span id="{wid}"{cls}>{e(w["w"])}</span>')
                tl.append(f'tl.fromTo("#{wid}",{{opacity:.28,y:8}},{{opacity:1,y:0,duration:.08}},{t0 + max(w["s"], gs):.3f});')
            legs.append(f'<div id="{sid}-g{gi}" class="leg clip" data-start="{t0 + gs:.3f}" '
                        f'data-duration="{max(0.1, ge - gs):.3f}" data-track-index="4">{"".join(spans)}</div>')
        partes.append(f'<div class="legendas">{"".join(legs)}</div>')
        corpo.append(f'<div id="{sid}" class="cena clip" data-start="{t0:.3f}" data-duration="{d:.3f}" '
                     f'data-track-index="1" data-track-kind="graphics" style="z-index:{z}">{"".join(partes)}</div>')
        z += 2
        t0 += d

    # baque seco no número novo (ruído marrom curto gerado localmente, sem trilha de terceiros)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "anoisesrc=d=0.35:c=brown:a=0.9,lowpass=f=180,afade=t=out:st=0.03:d=0.3",
                    str(destino / "assets" / "baque.wav")], check=True)

    total = round(t0, 3)
    trilha(roteiro["id"], total, destino / "assets" / "trilha.wav")
    audios.append(f'<audio id="trilha" class="clip" src="assets/trilha.wav" data-start="0" data-duration="{total}" '
                  f'data-track-index="5" data-volume="{os.environ.get("LOL_TRILHA_VOLUME", "0.16")}"></audio>')
    doc = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<script src="assets/gsap.min.js"></script>
<style>{css}</style>
</head>
<body>
<div id="root" class="v{var}" data-composition-id="main" data-start="0" data-duration="{total}" data-width="1080" data-height="1920">
{chr(10).join(corpo)}
{chr(10).join(audios)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(tl)}
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
</script>
</body>
</html>
"""
    (destino / "index.html").write_text(doc)
    (destino / "legendas.json").write_text(json.dumps(legendas, ensure_ascii=False))
    return destino, total


def hf(args):
    return subprocess.run(["npx", "--no-install", "hyperframes", *args], cwd=RAIZ, capture_output=True, text=True, timeout=1800)


def lint(projeto):
    r = hf(["lint", str(projeto), "--json"])
    try:
        j = json.loads(r.stdout)
    except json.JSONDecodeError:
        return [r.stdout[-500:]] if r.returncode else []
    achados = j.get("findings", []) if isinstance(j, dict) else []
    return [f for f in achados if f.get("severity") == "error"]


def render(projeto, saida, qualidade):
    r = hf(["render", str(projeto), "-o", str(Path(saida).resolve()), "--quality", qualidade, "--fps", "30",
            "--quiet", "--skill=hyperframes", "--workers", os.environ.get("LOL_WORKERS", "4")])
    if r.returncode != 0 or not Path(saida).exists():
        raise RuntimeError(f"render falhou: {r.stdout[-800:]} {r.stderr[-800:]}")


def compor(roteiro, pasta_audio, saida_mp4, rascunho=False, legendas=None):
    saida_mp4 = Path(saida_mp4)
    projeto, total = montar(roteiro, pasta_audio, saida_mp4.parent / "projeto", legendas)
    erros = lint(projeto)
    if erros:
        raise RuntimeError("lint com erros: " + json.dumps(erros, ensure_ascii=False)[:1500])
    if rascunho:
        render(projeto, saida_mp4.with_name(saida_mp4.stem + "_rascunho.mp4"), "draft")
    render(projeto, saida_mp4, "high")
    return projeto, total


def main():
    rot = json.loads(Path(sys.argv[1]).read_text())
    pasta = TMP / rot["id"]
    saida = Path(sys.argv[2]) if len(sys.argv) > 2 else pasta / f"{rot['id']}.mp4"
    if any(c["duracao"] is None for c in rot["cenas"]):
        print("roteiro sem duração: rode narrar.py antes")
        sys.exit(2)
    _, total = compor(rot, pasta / "audio", saida)
    print(f"ok {saida} ({total:.2f}s)")


if __name__ == "__main__":
    main()
