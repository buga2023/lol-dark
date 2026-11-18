"""Utilidades compartilhadas: caminhos, JSONL, schema e Telegram."""
import json
import os
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TMP = RAIZ / ".tmp"
ESTADO = Path(os.environ.get("LOL_ESTADO", RAIZ / ".tmp" / "state"))
SCHEMA = RAIZ / "schemas" / "roteiro.schema.json"
MIN_PALAVRAS, MAX_PALAVRAS = 60, 110  # skill roteiro-short-lol: 25 a 45 s
MAX_PALAVRAS_FRASE = 14
MAX_PALAVRAS_TELA = 6
PROIBIDAS = ["você não vai acreditar", "prepare-se", "neste vídeo", "hoje vamos falar", "fala galera",
             "e aí pessoal", "sem mais delongas", "isso muda tudo", "simplesmente insano", "bizarro", "chocante",
             "mergulhar", "desvendar", "universo de", "no mundo de league of legends", "se inscreva",
             "deixe o like", "comenta aí", "fique até o final",
             # cara de texto de IA
             "vale ressaltar", "é importante notar", "em suma", "sem dúvida", "jornada", "game changer",
             "nada menos que", "elevar o nível", "não é apenas", "mas sim", "no fim das contas", "épico"]


def ler_jsonl(p):
    p = Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def anexar_jsonl(p, regs):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        for r in regs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def gravar_jsonl(p, regs):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in regs))


def palavras(roteiro):
    return sum(len(c["narracao"].split()) for c in roteiro["cenas"])


def validar_roteiro(roteiro):
    """Lista de erros (vazia = válido): schema + regras que o schema não expressa."""
    import jsonschema
    schema = json.loads(SCHEMA.read_text())
    erros = [e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(roteiro)]
    if erros:
        return erros
    n = palavras(roteiro)
    if not MIN_PALAVRAS <= n <= MAX_PALAVRAS:
        erros.append(f"narração com {n} palavras, fora de {MIN_PALAVRAS}-{MAX_PALAVRAS}")
    for c in roteiro["cenas"]:
        baixo = c["narracao"].lower()
        for p in PROIBIDAS:
            if p in baixo:
                erros.append(f"cena {c['n']}: frase proibida '{p}'")
        for fr in re.split(r"[.!?:]+", c["narracao"]):
            if len(fr.split()) > MAX_PALAVRAS_FRASE:
                erros.append(f"cena {c['n']}: frase com {len(fr.split())} palavras (máx {MAX_PALAVRAS_FRASE})")
        if len(c["texto_tela"].replace("·", " ").split()) > MAX_PALAVRAS_TELA:
            erros.append(f"cena {c['n']}: texto_tela com mais de {MAX_PALAVRAS_TELA} palavras")
    ids = {f["id"] for f in roteiro["fontes"]}
    for c in roteiro["cenas"]:
        if c["fonte_id"] is not None and c["fonte_id"] not in ids:
            erros.append(f"cena {c['n']}: fonte_id {c['fonte_id']} inexistente")
    return erros


def ffprobe_json(arq):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(arq)],
        capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def duracao(arq):
    return float(ffprobe_json(arq)["format"]["duration"])


def telegram(metodo, dados=None, arquivos=None):
    """Chamada à Bot API. Nunca imprime a resposta crua (logs do Actions são públicos)."""
    import requests
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    r = requests.post(f"https://api.telegram.org/bot{token}/{metodo}", data=dados, files=arquivos, timeout=120)
    j = r.json()
    if not j.get("ok"):
        raise RuntimeError(f"Telegram {metodo} falhou: {j.get('error_code')} {j.get('description', '')[:80]}")
    return j["result"]


def alertar(texto):
    """Alerta no Telegram; sem token configurado, só imprime."""
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        try:
            telegram("sendMessage", {"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": f"⚠️ lol-dark: {texto}"[:4000]})
            return
        except Exception as e:  # alerta não pode derrubar a esteira
            print(f"alerta não enviado: {e}")
    print(f"ALERTA: {texto}")


NUM = re.compile(r"\d+(?:[.,]\d+)*")


def numeros(texto):
    """Números normalizados ('1.275' -> '1275', '7,5' -> '7.5')."""
    out = set()
    for m in NUM.findall(texto):
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", m):
            out.add(m.replace(".", ""))
        else:
            out.add(m.replace(",", "."))
    return out
