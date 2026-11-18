"""Legendas palavra a palavra: transcreve a narração (whisper local) e alinha ao texto do roteiro.

O texto exibido é sempre o do roteiro (nunca o que o ASR ouviu); a transcrição só dá o tempo.
Se a transcrição falhar, cai para tempo proporcional ao tamanho das palavras.
"""
import difflib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import RAIZ, duracao  # noqa: E402


def norm(w):
    w = unicodedata.normalize("NFD", w.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(ch for ch in w if unicodedata.category(ch) != "Mn"))


def proporcional(palavras, dur):
    total = sum(len(p) + 1 for p in palavras)
    t, out = 0.0, []
    for p in palavras:
        d = dur * (len(p) + 1) / total
        out.append({"w": p, "s": round(t, 3), "e": round(t + d, 3)})
        t += d
    return out


def alinhar(palavras, asr):
    """palavras: texto do roteiro; asr: [{text,start,end}]. Interpola o que não casar."""
    a, b = [norm(p) for p in palavras], [norm(x["text"]) for x in asr]
    tempos = [None] * len(palavras)
    for bloco in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(bloco.size):
            x = asr[bloco.b + k]
            tempos[bloco.a + k] = (x["start"], x["end"])
    # preenche buracos interpolando entre vizinhos conhecidos
    i = 0
    fim_asr = asr[-1]["end"] if asr else 0.0
    while i < len(tempos):
        if tempos[i] is None:
            j = i
            while j < len(tempos) and tempos[j] is None:
                j += 1
            ini = tempos[i - 1][1] if i > 0 else 0.0
            fim = tempos[j][0] if j < len(tempos) else max(fim_asr, ini + 0.3 * (j - i))
            passo = (fim - ini) / (j - i)
            for k in range(i, j):
                tempos[k] = (ini + passo * (k - i), ini + passo * (k - i + 1))
            i = j
        else:
            i += 1
    return [{"w": p, "s": round(s, 3), "e": round(e, 3)} for p, (s, e) in zip(palavras, tempos)]


def transcrever(wav, pasta):
    r = subprocess.run(["npx", "--no-install", "hyperframes", "transcribe", str(wav), "-m", "small", "-l", "pt",
                        "--json", "-d", str(pasta)], cwd=RAIZ, capture_output=True, text=True, timeout=1200)
    j = json.loads(r.stdout.strip().splitlines()[-1])
    if not j.get("ok"):
        raise RuntimeError(j)
    return json.loads(Path(j["transcriptPath"]).read_text())


def legendar(roteiro, pasta_audio):
    """Devolve {n_cena: [{w,s,e}]} com tempo relativo ao início da cena."""
    pasta_audio = Path(pasta_audio)
    cenas = roteiro["cenas"]
    wavs = [pasta_audio / f"cena{c['n']}.wav" for c in cenas]
    offs, t = [], 0.0
    for c in cenas:
        offs.append(t)
        t += c["duracao"]
    out = {}
    try:
        # uma transcrição só: concatena os WAVs com o mesmo espaçamento do vídeo
        lista = pasta_audio / "concat.txt"
        partes = []
        for w, c in zip(wavs, cenas):
            pad = pasta_audio / f"pad{c['n']}.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(w), "-af", f"apad=whole_dur={c['duracao']}",
                            "-ar", "24000", "-ac", "1", str(pad)], check=True)
            partes.append(f"file '{pad.name}'")
        lista.write_text("\n".join(partes))
        tudo = pasta_audio / "narracao.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), str(tudo)], check=True)
        asr = transcrever(tudo, pasta_audio)
        for c, o in zip(cenas, offs):
            trecho = [x for x in asr if o - 0.15 <= x["start"] < o + c["duracao"] - 0.05]
            trecho = [dict(x, start=max(0, x["start"] - o), end=max(0, x["end"] - o)) for x in trecho]
            out[c["n"]] = alinhar(c["narracao"].split(), trecho)
        fonte = "whisper"
    except Exception as e:  # sem ASR, legenda proporcional
        print(f"transcrição falhou, usando tempo proporcional: {e}")
        for c, w in zip(cenas, wavs):
            out[c["n"]] = proporcional(c["narracao"].split(), duracao(w))
        fonte = "proporcional"
    return out, fonte


if __name__ == "__main__":
    rot = json.loads(Path(sys.argv[1]).read_text())
    leg, fonte = legendar(rot, sys.argv[2])
    print(fonte)
    print(json.dumps(leg, ensure_ascii=False)[:1500])
