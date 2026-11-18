"""Metas de qualidade da narração e do vídeo final. Cada meta é um número com limite; abaixo do limite, refaz.

Narração (por tomada de voz):
  ritmo            média de 2,2 a 3,3 palavras/s; cada cena entre 1,6 e 4,0
  inteligibilidade >= 0,85 das palavras do roteiro reconhecidas pelo whisper (pronúncia clara)
  naturalidade     >= 8/10 do juiz de áudio (Gemini ouvindo a narração inteira)
Vídeo (MP4 final):
  nota             >= 80/100 do juiz de vídeo (Gemini assistindo o MP4): gancho, legibilidade, ritmo, acabamento, autenticidade
"""
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from comum import duracao  # noqa: E402

METAS = {"ritmo_min": 2.2, "ritmo_max": 3.3, "cena_min": 1.6, "cena_max": 4.0, "inteligibilidade": 0.85, "naturalidade": 8, "video": 80}
MODELO_JUIZ = os.environ.get("LOL_GEMINI_JUIZ", "gemini-2.5-flash")
API = "https://generativelanguage.googleapis.com"


def _gerar(partes, temperatura=0):
    r = requests.post(f"{API}/v1beta/models/{MODELO_JUIZ}:generateContent",
                      headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, timeout=300,
                      json={"contents": [{"parts": partes}],
                            "generationConfig": {"temperature": temperatura, "responseMimeType": "application/json"}})
    if r.status_code != 200:
        raise RuntimeError(f"juiz Gemini HTTP {r.status_code}")
    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])


def avaliar_narracao(roteiro, pasta_audio, inteligibilidade):
    pasta_audio = Path(pasta_audio)
    falhas, medidas = [], {}
    ritmos, pal, seg = [], 0, 0.0
    for c in roteiro["cenas"]:
        d = duracao(pasta_audio / f"cena{c['n']}.wav")
        n = len(c["narracao"].split())
        pal, seg = pal + n, seg + d
        ritmos.append(round(n / max(d, 0.1), 2))
    medio = round(pal / max(seg, 0.1), 2)
    medidas["ritmo"], medidas["ritmo_medio"] = ritmos, medio
    if not METAS["ritmo_min"] <= medio <= METAS["ritmo_max"]:
        falhas.append(f"ritmo médio {medio} fora de {METAS['ritmo_min']}-{METAS['ritmo_max']} palavras/s")
    if any(not METAS["cena_min"] <= r <= METAS["cena_max"] for r in ritmos):
        falhas.append(f"cena com ritmo fora de {METAS['cena_min']}-{METAS['cena_max']} palavras/s: {ritmos}")
    medidas["inteligibilidade"] = inteligibilidade
    if inteligibilidade is not None and inteligibilidade < METAS["inteligibilidade"]:
        falhas.append(f"inteligibilidade {inteligibilidade} < {METAS['inteligibilidade']}")
    if os.environ.get("GEMINI_API_KEY"):
        wav = pasta_audio / "narracao.wav"
        if not wav.exists():
            wav = pasta_audio / "cena1.wav"
        j = _gerar([{"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(wav.read_bytes()).decode()}},
                    {"text": "Você é diretor de dublagem brasileiro. Ouça esta narração de um Short de League of Legends. "
                             "Dê de 0 a 10: 'naturalidade' (soa como pessoa real falando, não robô nem locutor de IA), "
                             "'pronuncia' (nomes e números claros), 'clima' (suave e descontraída). Seja rigoroso. "
                             "Responda só JSON: {\"naturalidade\": n, \"pronuncia\": n, \"clima\": n, \"problemas\": [\"...\"]}"}])
        medidas["juiz_audio"] = j
        if float(j.get("naturalidade", 0)) < METAS["naturalidade"]:
            falhas.append(f"naturalidade {j.get('naturalidade')}/10 < {METAS['naturalidade']}: {j.get('problemas', [])[:2]}")
    return {"aprovado": not falhas, "falhas": falhas, "medidas": medidas}


def _subir_arquivo(mp4):
    tam = Path(mp4).stat().st_size
    ini = requests.post(f"{API}/upload/v1beta/files", headers={
        "x-goog-api-key": os.environ["GEMINI_API_KEY"], "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start", "X-Goog-Upload-Header-Content-Length": str(tam),
        "X-Goog-Upload-Header-Content-Type": "video/mp4", "Content-Type": "application/json"},
        json={"file": {"display_name": Path(mp4).name}}, timeout=60)
    url = ini.headers["X-Goog-Upload-URL"]
    with open(mp4, "rb") as f:
        up = requests.post(url, headers={"X-Goog-Upload-Command": "upload, finalize", "X-Goog-Upload-Offset": "0"},
                           data=f, timeout=600).json()["file"]
    for _ in range(60):
        if up.get("state") == "ACTIVE":
            return up
        time.sleep(3)
        up = requests.get(f"{API}/v1beta/{up['name']}", headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, timeout=30).json()
    raise RuntimeError("Gemini não processou o vídeo a tempo")


CRITERIOS_VIDEO = {
    "gancho": (25, "Nos 2 primeiros segundos a tela e a fala já entregam o assunto e dão vontade de continuar?"),
    "legibilidade": (20, "Legenda, números e títulos legíveis num celular, sem corte nem sobreposição?"),
    "ritmo": (20, "Algo muda na tela a cada 2 s, sem trecho parado ou silêncio?"),
    "acabamento": (15, "Voz, trilha e efeitos bem mixados; voz na frente, trilha discreta; nada estoura?"),
    "autenticidade": (20, "Parece conteúdo autoral de um canal com identidade, e não 'AI slop' genérico?"),
}


def avaliar_video(mp4):
    if not os.environ.get("GEMINI_API_KEY"):
        return {"aprovado": True, "nota": None, "falhas": [], "obs": "sem GEMINI_API_KEY: juiz de vídeo não rodou"}
    arq = _subir_arquivo(mp4)
    rub = "\n".join(f"- {k} (0 a {p}): {q}" for k, (p, q) in CRITERIOS_VIDEO.items())
    j = _gerar([{"file_data": {"mime_type": "video/mp4", "file_uri": arq["uri"]}},
                {"text": "Você é editor-chefe de um canal de Shorts. Assista e avalie com rigor (nota alta é rara).\n" + rub +
                         "\nResponda só JSON: {\"criterios\": {\"<nome>\": {\"nota\": n, \"motivo\": \"...\"}}, \"melhorias\": [\"...\"]}"}])
    nota = round(sum(max(0, min(p, float(j.get("criterios", {}).get(k, {}).get("nota", 0))))
                     for k, (p, _) in CRITERIOS_VIDEO.items()))
    falhas = [] if nota >= METAS["video"] else [f"nota do vídeo {nota} < {METAS['video']}: {j.get('melhorias', [])[:3]}"]
    return {"aprovado": not falhas, "nota": nota, "falhas": falhas, "criterios": j.get("criterios", {}),
            "melhorias": j.get("melhorias", [])}


if __name__ == "__main__":
    print(json.dumps(avaliar_video(sys.argv[1]), ensure_ascii=False, indent=1))
