"""Passo 5: um WAV por cena via hyperframes tts; duração = áudio + 0,3 s."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import RAIZ, duracao  # noqa: E402

VOZ = os.environ.get("LOL_VOZ", "pf_dora")  # Kokoro, só reserva
VELOCIDADE = os.environ.get("LOL_VELOCIDADE", "1.08")
FOLGA = 0.3
# Pronúncia: o espeak lê nomes de campeão em português; corrigimos os que soam errado.
PRONUNCIA = json.loads((RAIZ / "assets" / "voz" / "pronuncia.json").read_text())


# Tratamento para tirar a "secura" de TTS: corta grave inútil, calor leve no grave-médio, sala bem pequena
# (reflexões curtas e baixas) e compressão suave. A masterização faz de-esser, presença e loudness depois.
TRATAMENTO = ("highpass=f=75,equalizer=f=220:t=q:w=1.0:g=1.8,equalizer=f=4200:t=q:w=2:g=-1.2,"
              "aecho=0.92:0.55:17|29|41:0.10|0.07|0.04,acompressor=threshold=-22dB:ratio=2:attack=12:release=160:makeup=1.5")


def pausa(narracao):
    """Respiro no fim da cena conforme a pontuação, em vez de um silêncio fixo."""
    fim = narracao.strip()[-1:]
    return {"?": 0.42, "!": 0.36, ".": 0.30, ",": 0.18, ":": 0.22}.get(fim, 0.26)


def tratar_voz(wav):
    tmp = Path(wav).with_suffix(".bruto.wav")
    Path(wav).replace(tmp)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", TRATAMENTO, "-ar", "24000", "-ac", "1", str(wav)],
                   check=True)
    tmp.unlink()


def falar(texto):
    for k, v in PRONUNCIA.items():
        texto = texto.replace(k, v)
    texto = re.sub(r"(\d)\.(\d{3})", r"\1\2", texto)  # 1.275 -> 1275
    return texto


VM_URL = "https://developer.voicemaker.in/voice/api"
VM_VOZ = os.environ.get("LOL_VM_VOZ", "")          # VoiceId do VoiceMaker (pt-BR); listar com: narrar.py --vozes
VM_MOTOR = os.environ.get("LOL_VM_MOTOR", "neural")


def voicemaker_vozes():
    import requests
    r = requests.post("https://developer.voicemaker.in/voice/list", json={"language": "pt-BR"},
                      headers={"Authorization": f"Bearer {os.environ['VOICEMAKER_API_KEY']}"}, timeout=30)
    j = r.json()
    if not j.get("success"):
        raise RuntimeError(f"VoiceMaker /voice/list recusou (HTTP {r.status_code})")
    return j["data"]["voices_list"]


def voicemaker(texto, wav):
    """Gera o MP3 no VoiceMaker e converte para WAV 24 kHz mono (mesmo formato do Kokoro)."""
    import requests
    corpo = {"Engine": VM_MOTOR, "VoiceId": VM_VOZ, "LanguageCode": "pt-BR", "Text": texto, "OutputFormat": "mp3",
             "SampleRate": "48000", "Effect": "default", "MasterSpeed": os.environ.get("LOL_VM_VELOCIDADE", "8"),
             "MasterVolume": "0", "MasterPitch": "0"}
    r = requests.post(VM_URL, json=corpo, headers={"Authorization": f"Bearer {os.environ['VOICEMAKER_API_KEY']}"}, timeout=120)
    j = r.json()
    if not j.get("success"):
        raise RuntimeError(f"VoiceMaker recusou (HTTP {r.status_code}): {str(j.get('message', ''))[:120]}")
    mp3 = Path(wav).with_suffix(".mp3")
    mp3.write_bytes(requests.get(j["path"], timeout=120).content)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-ar", "24000", "-ac", "1", str(wav)], check=True)


VOZ_CANAL = json.loads((RAIZ / "assets" / "voz" / "voz.json").read_text())
GEMINI_TTS_MODELO = os.environ.get("LOL_GEMINI_TTS", "gemini-3.8-flash-tts")  # docs oficiais, 18/11/2026


def _achar_audio(no):
    """Procura o primeiro campo base64 de áudio na resposta (o formato exato da Interactions API não foi testado)."""
    if isinstance(no, dict):
        for k in ("data", "audio", "inline_data", "inlineData"):
            v = no.get(k)
            if isinstance(v, str) and len(v) > 1000:
                return v
        for v in no.values():
            r = _achar_audio(v)
            if r:
                return r
    if isinstance(no, list):
        for v in no:
            r = _achar_audio(v)
            if r:
                return r
    return None


def gemini_tts(texto, wav):
    """Voz do canal (skill video-short-lol): Gemini 3.8 Flash TTS, Interactions API, voz e estilo do voz.json.
    Saída documentada: WAV 24 kHz mono 16 bits."""
    import base64
    import requests
    voz = os.environ.get("LOL_GEMINI_VOZ") or VOZ_CANAL.get("voz")
    if not voz or voz.startswith("A DEFINIR"):
        raise RuntimeError("voz do canal ainda não definida em assets/voz/voz.json")
    corpo = {"model": GEMINI_TTS_MODELO,
             "input": [{"type": "user_input", "content": [{"type": "text", "text": texto,
                                                            "annotations": [{"type": "speech_metadata",
                                                                             "style": VOZ_CANAL["estilo"]}]}]}],
             "response_format": {"type": "audio"},
             "generation_config": {"speech_config": [{"voice": voz}]}}
    r = requests.post("https://generativelanguage.googleapis.com/v1beta/interactions", json=corpo,
                      headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini TTS HTTP {r.status_code}")
    dados = _achar_audio(r.json())
    if not dados:
        raise RuntimeError("Gemini TTS: resposta sem áudio reconhecível")
    bruto = base64.b64decode(dados)
    tmp = Path(wav).with_suffix(".g.wav" if bruto[:4] == b"RIFF" else ".pcm")
    tmp.write_bytes(bruto)
    entrada = ["-i", str(tmp)] if bruto[:4] == b"RIFF" else ["-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(tmp)]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entrada, "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse", "-ar", "24000", "-ac", "1", str(wav)],
                   check=True)


VS_URL = os.environ.get("LOL_VOICESTUDIO_URL", "")  # ex.: http://127.0.0.1:3900 (container no runner)
VS_VOZ = os.environ.get("LOL_VS_VOZ") or json.loads((RAIZ / "assets" / "voz" / "voz.json").read_text()).get("voz", "female, young adult, moderate pitch")  # tags de design do OmniVoice


def voicestudio(texto, wav):
    """VoiceStudio (OmniVoice) local, API compatível com OpenAI; voz desenhada por tags, sem chave."""
    import requests
    corpo = {"model": os.environ.get("LOL_VS_MODELO", "omnivoice"), "input": texto, "voice": "default",
             "instruct": VS_VOZ, "language": "pt", "response_format": "wav",
             "speed": float(os.environ.get("LOL_VS_VELOCIDADE", "1.0"))}
    r = requests.post(f"{VS_URL}/v1/audio/speech", json=corpo, timeout=900)
    if r.status_code != 200:
        raise RuntimeError(f"VoiceStudio HTTP {r.status_code}: {r.text[:160]}")
    bruto = Path(wav).with_suffix(".vs.wav")
    bruto.write_bytes(r.content)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(bruto), "-ar", "24000", "-ac", "1", str(wav)], check=True)


def provedores():
    """Ordem de preferência; o laço de qualidade passa para o próximo se a voz não bater a meta."""
    p = []
    if os.environ.get("VOICEMAKER_API_KEY") and VM_VOZ:
        p.append("voicemaker")
    if VS_URL:
        p.append("voicestudio")
    if os.environ.get("GEMINI_API_KEY"):
        p.append("gemini")
    p.append("kokoro")
    if os.environ.get("LOL_VOZ_PROVEDOR") in p:  # forçar um provedor
        p.remove(os.environ["LOL_VOZ_PROVEDOR"])
        p.insert(0, os.environ["LOL_VOZ_PROVEDOR"])
    return p


def usar_voicemaker():
    return bool(os.environ.get("VOICEMAKER_API_KEY") and VM_VOZ)


def narrar(roteiro, pasta, provedor=None):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HYPERFRAMES_PYTHON=os.environ.get("HYPERFRAMES_PYTHON", str(RAIZ / ".venv/bin/python")))
    provedor = provedor or provedores()[0]
    ultima = roteiro["cenas"][-1]["n"]
    roteiro["voz"] = provedor
    for c in roteiro["cenas"]:
        wav = pasta / f"cena{c['n']}.wav"
        texto = c["narracao"].replace("%", " por cento")
        if provedor in ("voicemaker", "voicestudio", "gemini"):
            {"voicemaker": voicemaker, "voicestudio": voicestudio, "gemini": gemini_tts}[provedor](falar(c["narracao"]), wav)
            tratar_voz(wav)
            c["duracao"] = round(duracao(wav) + (0.08 if c["n"] == ultima else pausa(c["narracao"])), 3)
            continue
        r = subprocess.run(["npx", "--no-install", "hyperframes", "tts", falar(c["narracao"]), "-v", VOZ,
                            "-l", "pt-br", "-s", VELOCIDADE, "-o", str(wav), "--json"],
                           cwd=RAIZ, env=env, capture_output=True, text=True, timeout=600)
        if r.returncode != 0 or not wav.exists():
            raise RuntimeError(f"TTS falhou na cena {c['n']}: {r.stdout[-300:]} {r.stderr[-300:]}")
        tratar_voz(wav)
        c["duracao"] = round(duracao(wav) + (0.08 if c["n"] == ultima else pausa(c["narracao"])), 3)  # loop: sem respiro no fim
    total = sum(c["duracao"] for c in roteiro["cenas"])
    return total


def main():
    if sys.argv[1] == "--vozes":
        for v in voicemaker_vozes():
            print(v.get("VoiceId"), v.get("VoiceGender"), v.get("Engine"), v.get("VoiceWebname"))
        return
    arq = Path(sys.argv[1])
    rot = json.loads(arq.read_text())
    total = narrar(rot, sys.argv[2] if len(sys.argv) > 2 else RAIZ / ".tmp" / rot["id"] / "audio")
    arq.write_text(json.dumps(rot, ensure_ascii=False, indent=1))
    print(f"total {total:.2f}s")
    if not 30 <= total <= 58:
        print("FORA de 30-58 s")
        sys.exit(1)


if __name__ == "__main__":
    main()
