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


CLIPE_URL = "https://lol.dyn.riotcdn.net/x/videos/champion-abilities/{k:04d}/ability_{k:04d}_{l}1.mp4"
_CHAVES_NUM = {}


def chave_numerica(campeao_id):
    if not _CHAVES_NUM:
        v = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=30).json()[0]
        d = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{v}/data/en_US/champion.json", timeout=30).json()["data"]
        _CHAVES_NUM.update({k: int(x["key"]) for k, x in d.items()})
    return _CHAVES_NUM.get(campeao_id)


def letra_habilidade(c, idx):
    """Qual habilidade a cena fala: letra no texto de tela/rótulo/narração; 'ult' = R; 'passiva' = P."""
    tela = " ".join(filter(None, [c.get("texto_tela"), c.get("rotulo")]))
    fala = c.get("narracao") or ""
    alvo = tela + " " + fala
    m = (re.search(r"(?:^|[\s·(])([QWER])(?=\s*[–·:\-—)]|\s*$)", tela)
         or re.search(r"\b(?i:o|no|do|seu|sua|um|na|da)\s+([QWER])\b", fala))
    if m:
        return m.group(1), True
    if re.search(r"\bult", alvo, re.I):
        return "R", True
    if re.search(r"passiva", alvo, re.I):
        return "P", True
    return "QWER"[idx % 4], False  # clipe de ilustração; sem selo, para não afirmar qual habilidade é


def clipe_habilidade(campeao_id, letra, dur, destino, largura=890, altura=460, terminar_em=None):
    """Clipe oficial da habilidade (site da Riot), cortado no tempo da cena e no tamanho do quadro, sem áudio."""
    k = chave_numerica(campeao_id)
    if not k:
        return None
    cache = ARTE_CACHE / "clips" / f"{k:04d}_{letra}.mp4"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists():
        r = requests.get(CLIPE_URL.format(k=k, l=letra), timeout=120)
        if r.status_code != 200:
            return None
        cache.write_bytes(r.content)
    inicio = 0.8
    if terminar_em is not None:  # o último quadro cai em 'terminar_em' do clipe (fecho emenda no gancho)
        total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                      str(cache)], capture_output=True, text=True).stdout.strip() or 0)
        inicio = (terminar_em - dur) % total if total else 0.8
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-ss", f"{inicio:.3f}", "-i", str(cache), "-t", f"{dur:.3f}",
                    "-vf", f"scale={largura}:{altura}:force_original_aspect_ratio=increase,crop={largura}:{altura},fps=30",
                    "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(destino)],
                   check=True)
    return destino


def alternar_palco(tl, sid, t0, d, fecho=False):
    """Segmentos de ~1,8 s: pares mostram o gameplay, ímpares cortam para um detalhe da arte (115-135%).
    Dentro de cada segmento a imagem faz o zoom lento de 100% para 106% (edicao-wardado)."""
    detalhes = [(1.15, 0, -6), (1.35, -8, -10), (1.25, 8, -4)]
    if t0 > 0:
        tl.append(f'tl.set("#{sid}-vw",{{opacity:0}},0);')
    if not fecho:
        tl.append(f'tl.set("#{sid}-vw",{{opacity:0}},{t0 + d:.3f});')
    limite = max(0.0, d - 1.2) if fecho else d
    k, tt = 0, 0.0
    while tt < limite - 0.05:
        fim = min(limite, tt + 1.8)
        ir = "" if k == 0 else ",immediateRender:false"
        if k % 2 == 0:
            tl.append(f'tl.set("#{sid}-vw",{{opacity:1}},{t0 + tt:.3f});')
        else:
            esc, xp, yp = detalhes[(k // 2) % len(detalhes)]
            tl.append(f'tl.set("#{sid}-vw",{{opacity:0}},{t0 + tt:.3f});')
            tl.append(f'tl.fromTo("#{sid}-art",{{scale:{esc},xPercent:{xp},yPercent:{yp}}},'
                      f'{{scale:{esc * 1.06:.3f},xPercent:{xp},yPercent:{yp - 2},duration:{fim - tt:.2f},ease:"none"{ir}}},{t0 + tt:.3f});')
        k, tt = k + 1, fim
    if fecho:  # loop: os últimos 1,2 s mostram o gameplay, como o primeiro quadro
        tl.append(f'tl.set("#{sid}-vw",{{opacity:1}},{t0 + max(0.0, d - 1.2):.3f});')


def caixa_video(sid, t0, d, z, solo=False, hab=None):
    """Clipe na camada do root: caixa sem tempo próprio (só posiciona e anima) com o <video> temporizado dentro."""
    cls = "vidbox solo" if solo else "vidbox"
    return (f'<div class="{cls}" id="{sid}-vw" style="z-index:{z}"><div class="mov" id="{sid}-img">'
            f'<video id="{sid}-vid" class="clip" src="assets/clip_{sid}.mp4" data-start="{t0:.3f}" data-duration="{d:.3f}" '
            f'data-track-index="6" muted playsinline></video></div>'
            + (f'<span class="hab">{e(hab)}</span>' if hab else "") + '</div>')


def campeao(asset):
    return asset.split("/", 1)[1] if asset.startswith("ddragon:champion/") else None


def direcao_de(antes, depois):
    num = lambda x: float(re.sub(r"[^\d.,]", "", x).replace(",", ".") or 0)  # noqa: E731
    return "buff" if num(depois) >= num(antes) else "nerf"


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
        tl.append(f'tl.fromTo("#{sid}-selo",{{opacity:0,y:20}},{{opacity:1,y:0,duration:.3,ease:"power3.out"}},{t0 + .5:.3f});')
    # abertura varia por variação; o quadro 0 já mostra a manchete (skill: primeiro quadro diz o assunto)
    if variacao == 0:
        tl.append(f'tl.fromTo("#{sid}-man",{{scale:1.07,transformOrigin:"left top"}},{{scale:1,duration:.5,ease:"expo.out"}},{t0:.3f});')
    elif variacao == 1:
        tl.append(f'tl.fromTo("#{sid}-man",{{x:-14}},{{x:0,duration:.12,ease:"steps(3)"}},{t0:.3f});')
    else:
        tl.append(f'tl.fromTo("#{sid}-man",{{clipPath:"inset(0 18% 0 0)"}},{{clipPath:"inset(0 0% 0 0)",duration:.45,ease:"steps(6)"}},{t0:.3f});')
    k, tt = 0, 0.0
    while tt < d - 0.2:
        fim = min(d, tt + 1.8)
        for i in range(len(campeoes)):
            esc = 1.15 + 0.35 * ((i + k) % 2)
            tl.append(f'tl.fromTo("#{sid}-t{i}",{{yPercent:{-8 + 6 * ((i + k) % 3)},scale:{esc}}},'
                      f'{{yPercent:{-4 + 6 * ((i + k) % 3)},scale:{esc * 1.05:.3f},duration:{fim - tt:.2f},ease:"none"'
                      f'{",immediateRender:false" if k else ""}}},{t0 + tt:.3f});')
        k, tt = k + 1, fim
    return partes


# efeitos (Pixabay Content License, uso comercial livre): arquivo, segundo do pico, volume
# Biblioteca fixa do canal (edicao-wardado: até 6 sons, os mesmos em todo vídeo = identidade).
# Pixabay Content License (uso comercial livre). arquivo, segundo do pico, volume (~8-10 dB abaixo da voz)
SFX = {"corte": ("whoosh-short.mp3", 0.162, 0.30), "numero": ("pop.mp3", 0.119, 0.28),
       "faixa": ("whoosh.mp3", 0.162, 0.32), "veredito": ("impact-bass-1.mp3", 0.073, 0.34),
       "titulo": ("click-soft.mp3", 0.072, 0.22)}
QUADRO = 1 / 30


def efeito(audios, nome, t_imagem, idx, media_start=None, dur=None):
    """Põe o pico do efeito 1 quadro depois da imagem (luz chega antes do som)."""
    arq, pico, vol = SFX[nome]
    ms = media_start or 0.0
    ini = max(0.0, t_imagem + QUADRO - (pico - ms))
    dur = dur or 0.7
    audios.append(f'<audio id="sfx{idx}" class="clip" src="assets/sfx/{arq}" data-start="{ini:.3f}" data-duration="{dur:.3f}" '
                  f'{f"data-media-start=\"{ms:.3f}\" " if ms else ""}data-track-index="3" data-volume="{vol}"></audio>')


def faixa_dourada(tl, sid_entrada, t_corte):
    """Troca de bloco: faixa ouro atravessa a tela em 0,2 s revelando a cena seguinte."""
    tl.append(f'tl.fromTo("#{sid_entrada}-flood",{{xPercent:0,opacity:1}},{{xPercent:101,opacity:1,duration:.2,ease:"power3.in"}},{t_corte:.3f});')


def titulo_por_palavra(texto, sid, t, tl, extra_style=""):
    """Título entra palavra por palavra (desfoque 6px -> 0 em 0,13 s, 0,067 s de intervalo) e fica parado."""
    palavras = texto.split()
    spans = "".join(f'<span class="tw" id="{sid}-mw{i}">{e(p)}</span> ' for i, p in enumerate(palavras))
    for i in range(len(palavras)):
        tl.append(f'tl.fromTo("#{sid}-mw{i}",{{opacity:0,y:40}},{{opacity:1,y:0,duration:.3,ease:"power3.out"}},{t + i * .06:.3f});')
    return spans


def trilha(seed, dur, destino):
    """Trilha baixa sob a voz. Usa assets/musica/*.mp3|wav (escolha estável por vídeo) ou sintetiza um pad suave."""
    pasta = RAIZ / "assets" / "musica"
    faixas = sorted([*pasta.glob("*.mp3"), *pasta.glob("*.wav")]) if pasta.exists() else []
    if faixas:
        f = faixas[sum(map(ord, seed)) % len(faixas)]
        filtro = "afade=t=in:d=0.3"  # sem fade no fim: o loop do Short fecha
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", str(f), "-t", f"{dur:.2f}", "-af", filtro,
                        "-ar", "44100", "-ac", "2", str(destino)], check=True)
        return
    # pad em lá menor com 9ª: senos lentos com tremolo, filtro passa-baixa e fades
    notas = [110.0, 164.81, 220.0, 261.63, 329.63, 493.88]
    soma = "+".join(f"{0.16 if i < 2 else 0.1}*sin(2*PI*{f}*t)*(0.75+0.25*sin(2*PI*{0.07 + 0.03 * i}*t))"
                    for i, f in enumerate(notas))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"aevalsrc={soma}:s=44100:d={dur:.2f}",
                    "-af", "lowpass=f=1400,aecho=0.8:0.7:120|240:0.25|0.15,afade=t=in:d=0.3,volume=2.5",
                    "-ac", "2", str(destino)], check=True)


def montar(roteiro, pasta_audio, destino, legendas=None):
    destino = Path(destino)
    if destino.exists():
        shutil.rmtree(destino)
    (destino / "assets").mkdir(parents=True)
    shutil.copy(COMP / "vendor" / "gsap.min.js", destino / "assets" / "gsap.min.js")
    shutil.copytree(COMP / "fonts", destino / "assets" / "fonts")
    css = (COMP / "wardado.css").read_text() + (COMP / roteiro["formato"] / "formato.css").read_text()
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
    serie = {"patch60": "patch", "voce-sabia": "você sabia", "top5": "top 5", "noticia": "notícia"}.get(roteiro["formato"], "")
    cabecalho = rot1 or serie
    marca = rot1.split()[-1] if rot1 else ""
    corpo, audios, tl, videos = [], [], [], []
    t0, z = 0.0, 1
    primeiro_numero = False
    for c in cenas:
        n, d = c["n"], c["duracao"]
        sid = f"c{n}"
        n_videos = len(videos)
        shutil.copy(Path(pasta_audio) / f"cena{n}.wav", destino / "assets" / f"cena{n}.wav")
        audios.append(f'<audio id="voz{n}" class="clip" src="assets/cena{n}.wav" data-start="{t0:.3f}" '
                      f'data-duration="{d:.3f}" data-track-index="2" data-volume="1"></audio>')
        tl.append(f'tl.fromTo("#{sid}-fundo",{{backgroundPosition:"0px 0px, {t0 * 8:.0f}px 0px, {30 + t0 * 8:.0f}px 15px, 0 0"}},'
                  f'{{backgroundPosition:"0px 0px, {(t0 + d) * 8:.0f}px 0px, {30 + (t0 + d) * 8:.0f}px 15px, 0 0",duration:{d:.2f},ease:"none"}},{t0:.3f});')
        partes = [f'<div class="fundo" id="{sid}-fundo"></div>', f'<div class="marca" data-layout-ignore>{e(marca)}</div>',
                  f'<div class="cab"><span class="logo">{LOGO}<span>wardado clips</span></span><span>{e(cabecalho)}</span>'
                  f'<b>{n:02d}/{len(cenas):02d}</b></div>']
        ch = campeao(c["asset"])
        arte_bg = ch or (campeoes[(n - 1) % len(campeoes)] if campeoes else None)
        if arte_bg:
            partes.insert(1, f'<div class="bgart"><img id="{sid}-bg" src="assets/{arte_bg}.jpg" alt=""></div>')
            planos_bg = [(1.15, 0, 0), (1.9, -14, 8), (1.45, 12, -6), (2.2, 4, 12)]
            k, tt = 0, 0.0
            while tt < d - 0.2:
                esc, xp, yp = planos_bg[(k + n + 1) % len(planos_bg)]
                fim = min(d, tt + 1.8)
                tl.append(f'tl.fromTo("#{sid}-bg",{{scale:{esc},xPercent:{xp},yPercent:{yp}}},'
                          f'{{scale:{esc * 1.08:.3f},xPercent:{xp - 4},yPercent:{yp},duration:{fim - tt:.2f},ease:"none"'
                          f'{",immediateRender:false" if k else ""}}},{t0 + tt:.3f});')
                k, tt = k + 1, fim
        if not ch and campeoes:  # gancho e fecho: palco cheio com o campeão principal (sem as tiras recortadas)
            # um campeão só: arte grande no lugar de uma tira única
            ch_solo = campeoes[0]
            vid = None
            if os.environ.get("LOL_GAMEPLAY", "1") == "1":
                try:  # gancho e fecho usam o mesmo clipe: o loop emenda
                    vid = clipe_habilidade(ch_solo, letra_habilidade(cenas[1] if len(cenas) > 1 else c, 1)[0], d,
                                           destino / "assets" / f"clip_{sid}.mp4", largura=1080, altura=700,
                                           terminar_em=0.8 if n == len(cenas) else None)
                except Exception as ex:
                    print(f"clipe {ch_solo} indisponível: {ex}")
            if vid:
                partes.append(f'<div class="foto solo"><img id="{sid}-art" src="assets/{ch_solo}.jpg" alt=""></div>')
                alternar_palco(tl, sid, t0, d, fecho=(n == len(cenas)))
                videos.append(caixa_video(sid, t0, d, z + 1, solo=True))
            else:
                partes.append(f'<div class="foto solo"><img id="{sid}-img" src="assets/{ch_solo}.jpg" alt=""></div>')
            partes.append(f'<h1 id="{sid}-man" class="manchete grande">{e(c["texto_tela"])}</h1>')
            planos = [(1.0, 0, 0), (1.12, -4, -3), (1.0, 2, 2), (1.15, 3, -4)]
            k, tt = 0, 0.0
            while tt < d - 0.2:
                esc, xp, yp = planos[(k + n) % len(planos)]
                fim = min(d, tt + 1.8)
                tl.append(f'tl.fromTo("#{sid}-img",{{scale:{esc},xPercent:{xp},yPercent:{yp}}},'
                          f'{{scale:{esc * 1.06:.3f},xPercent:{xp + 3},yPercent:{yp},duration:{fim - tt:.2f},ease:"none"'
                          f'{",immediateRender:false" if k else ""}}},{t0 + tt:.3f});')
                k, tt = k + 1, fim
        elif not ch:
            # gancho e fecho usam o mesmo quadro de tiras: o loop emenda sem salto
            partes += cena_tiras(sid, c, campeoes, t0, d, var, tl)
        else:
            letra, citada = letra_habilidade(c, n)
            vid = None
            if os.environ.get("LOL_GAMEPLAY", "1") == "1":
                try:
                    vid = clipe_habilidade(ch, letra, d, destino / "assets" / f"clip_{sid}.mp4", largura=1080, altura=640)
                except Exception as ex:  # sem clipe: fica a splash art
                    print(f"clipe {ch} {letra} indisponível: {ex}")
            if vid:
                partes.append(f'<div class="foto"><img id="{sid}-art" src="assets/{ch}.jpg" alt=""></div>')
                alternar_palco(tl, sid, t0, d)
                videos.append(caixa_video(sid, t0, d, z + 1, hab=(letra if letra != "P" else "PASSIVA") if citada else None))
            else:
                partes.append(f'<div class="foto"><img id="{sid}-img" src="assets/{ch}.jpg" alt=""></div>')
            planos = [(1.0, 0, 0), (1.12, -4, -3), (1.0, 2, 2), (1.15, 3, -4)]  # aberto e salto de zoom (até 115%)
            k, tt = 0, 0.0
            while tt < d - 0.2:
                esc, xp, yp = planos[(k + n) % len(planos)]
                fim = min(d, tt + 1.8)
                tl.append(f'tl.fromTo("#{sid}-img",{{scale:{esc},xPercent:{xp},yPercent:{yp}}},'
                          f'{{scale:{esc * 1.06:.3f},xPercent:{xp + 3},yPercent:{yp},duration:{fim - tt:.2f},ease:"none"'
                          f'{",immediateRender:false" if k else ""}}},{t0 + tt:.3f});')
                k, tt = k + 1, fim
            estilo = ""
            if c.get("antes") and c.get("depois"):
                # cena de número: título numa linha só (encolhe se longo) para nunca cobrir o antes/depois
                tam = max(64, min(118, int(890 / (0.47 * max(1, len(c["texto_tela"]))))))
                estilo = f' style="font-size:{tam}px;white-space:nowrap"'
            partes.append(f'<h1 id="{sid}-man" class="manchete"{estilo}>{titulo_por_palavra(c["texto_tela"], sid, t0 + .12, tl)}</h1>')
            if c.get("antes") and c.get("depois"):
                direcao = c.get("direcao") or direcao_de(c["antes"], c["depois"])
                marca_dir = '<span class="dir buff">▲ BUFF</span>' if direcao == "buff" else '<span class="dir nerf">▼ NERF</span>'
                partes.append(f'<div class="numeros"><span class="antes" id="{sid}-antes">{e(c["antes"])}'
                              f'<i class="risco" id="{sid}-risco"></i></span><span class="seta" id="{sid}-seta">→</span>'
                              f'<span class="depois" id="{sid}-dep">{e(c["depois"])}</span>'
                              f'<span id="{sid}-dir">{marca_dir}</span></div>')
                tl.append(f'tl.fromTo("#{sid}-dir",{{opacity:0,y:20}},{{opacity:1,y:0,duration:.2}},{t0 + .35:.3f});')
                # o número novo entra quando é falado (skill: número aparece no momento em que é dito)
                tb = t0 + 0.6
                for w in legendas.get(n, []):
                    if c["depois"].rstrip("%") in w["w"]:
                        tb = t0 + max(0.4, w["s"])
                        break
                ta = t0 + 0.25
                for w in legendas.get(n, []):
                    if c["antes"].rstrip("%") in w["w"]:
                        ta = t0 + max(0.1, w["s"])
                        break
                ta = min(ta, tb - 0.35)
                tl.append(f'tl.fromTo("#{sid}-antes",{{opacity:0,y:20}},{{opacity:1,y:0,duration:.3,ease:"power3.out"}},{ta:.3f});')
                tl.append(f'tl.fromTo("#{sid}-antes",{{scale:1}},{{scale:.82,transformOrigin:"left bottom",duration:.2,ease:"power3.out",immediateRender:false}},{tb - .2:.3f});')
                tl.append(f'tl.fromTo("#{sid}-risco",{{scaleX:0}},{{scaleX:1,duration:.2,ease:"power3.in"}},{tb - .3:.3f});')
                tl.append(f'tl.fromTo("#{sid}-seta",{{opacity:0,x:-20}},{{opacity:1,x:0,duration:.12}},{tb - .12:.3f});')
                tl.append(f'tl.fromTo("#{sid}-dep",{{scale:1.12,opacity:0}},{{scale:1,opacity:1,duration:.3,ease:"power3.out"}},{tb:.3f});')
                a_num = re.sub(r"[^\d.,]", "", c["antes"]).replace(",", ".")
                d_num = re.sub(r"[^\d.,]", "", c["depois"]).replace(",", ".")
                if a_num and d_num:
                    suf = "%" if c["depois"].strip().endswith("%") else ""
                    casas = len(d_num.split(".")[1]) if "." in d_num else 0
                    # contador: o texto é função do tempo da timeline (render determinístico)
                    tl.append(f'(()=>{{const el=document.querySelector("#{sid}-dep"),o={{v:{a_num}}};'
                              f'tl.fromTo(o,{{v:{a_num}}},{{v:{d_num},duration:.45,ease:"power2.out",'
                              f'onUpdate:()=>{{el.textContent=o.v.toFixed({casas}).replace(".",",")+"{suf}";}}}},{tb:.3f});}})();')
                efeito(audios, "numero", tb - .05, f"p{n}")
            if c.get("rotulo"):
                partes.append(f'<div class="rotulo" id="{sid}-rot">{e(c["rotulo"])}</div>')
                tl.append(f'tl.fromTo("#{sid}-rot",{{clipPath:"inset(0 100% 0 0)"}},{{clipPath:"inset(0 0% 0 0)",duration:.3,ease:"power2.out"}},{t0 + .45:.3f});')
        # legendas karaokê: grupo aparece no início da 1ª palavra; cada palavra acende quando é dita
        legs = []
        grupos = grupos_legenda(legendas.get(n, []))
        for gi, g in enumerate(grupos):
            gs = 0.0 if (gi == 0 and n == 1) else g[0]["s"]
            ge = grupos[gi + 1][0]["s"] if gi + 1 < len(grupos) else d - 0.05
            spans = []
            for wi, w in enumerate(g):
                wid = f"{sid}-g{gi}w{wi}"
                cls = ""
                spans.append(f'<span id="{wid}"{cls}>{e(w["w"])}</span>')
                ws = t0 + max(w["s"], gs)
                we = t0 + (g[wi + 1]["s"] if wi + 1 < len(g) else ge)
                tl.append(f'tl.set("#{wid}",{{color:"var(--ouro)"}},{ws:.3f});')
                tl.append(f'tl.set("#{wid}",{{color:"var(--creme)"}},{max(ws + .05, we):.3f});')
            legs.append(f'<div id="{sid}-g{gi}" class="leg clip" data-start="{t0 + gs:.3f}" '
                        f'data-duration="{max(0.1, ge - gs):.3f}" data-track-index="4"><span class="legbox">{"".join(spans)}</span></div>')
        partes.append(f'<div class="legendas">{"".join(legs)}</div>')
        classe = "cena clip comvideo" if len(videos) > n_videos else "cena clip"
        corpo.append(f'<div id="{sid}" class="{classe}" data-start="{t0:.3f}" data-duration="{d:.3f}" '
                     f'data-track-index="1" data-track-kind="graphics" style="z-index:{z}">{partes[0]}'
                     f'<div class="quadro" id="{sid}-q">{"".join(partes[1:])}</div>'
                     f'<div class="flood" id="{sid}-flood" data-layout-ignore></div></div>')
        if n > 1:  # cena 1 já nasce pronta no quadro 0; emendas são corte seco
            if n == len(cenas):  # troca de bloco: o veredito/fecho entra pela faixa dourada
                faixa_dourada(tl, sid, t0)
                efeito(audios, "faixa", t0, f"f{n}")
                efeito(audios, "veredito", t0 + .2, f"v{n}")
            else:
                efeito(audios, "corte", t0, f"w{n}")
        z += 2
        t0 += d

    shutil.copytree(RAIZ / "assets" / "sfx", destino / "assets" / "sfx")

    total = round(t0, 3)
    trilha(roteiro["id"], total, destino / "trilha.wav")  # mixada depois, no masterizar.sh
    doc = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<script src="assets/gsap.min.js"></script>
<style>{css}</style>
</head>
<body>
<div id="root" class="v{var}" data-motion-blur="on" data-composition-id="main" data-start="0" data-duration="{total}" data-width="1080" data-height="1920">
{chr(10).join(corpo)}
{chr(10).join(videos)}
<div id="marcadagua" class="clip" data-start="0" data-duration="{total}" data-track-index="7" style="z-index:900">{LOGO}<span>wardado clips</span></div>
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
    cru = saida_mp4.with_name(saida_mp4.stem + "_cru.mp4")
    render(projeto, cru, "high")
    r = subprocess.run(["bash", str(RAIZ / "tools" / "masterizar.sh"), str(cru), str(saida_mp4), str(projeto / "trilha.wav")],
                       capture_output=True, text=True, timeout=900)
    if r.returncode != 0 or not saida_mp4.exists():
        raise RuntimeError(f"masterização falhou: {r.stderr[-400:]}")
    cru.unlink(missing_ok=True)
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
