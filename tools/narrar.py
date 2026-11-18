"""Passo 5: um WAV por cena via hyperframes tts; duração = áudio + 0,3 s."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import RAIZ, duracao  # noqa: E402

VOZ = os.environ.get("LOL_VOZ", "pm_alex")
VELOCIDADE = os.environ.get("LOL_VELOCIDADE", "1.08")
FOLGA = 0.3
# Pronúncia: o espeak lê nomes de campeão em português; corrigimos os que soam errado.
PRONUNCIA = json.loads((RAIZ / "assets" / "pronuncia.json").read_text())


def falar(texto):
    for k, v in PRONUNCIA.items():
        texto = texto.replace(k, v)
    texto = re.sub(r"(\d)\.(\d{3})", r"\1\2", texto)  # 1.275 -> 1275
    return texto


def narrar(roteiro, pasta):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HYPERFRAMES_PYTHON=os.environ.get("HYPERFRAMES_PYTHON", str(RAIZ / ".venv/bin/python")))
    for c in roteiro["cenas"]:
        wav = pasta / f"cena{c['n']}.wav"
        r = subprocess.run(["npx", "--no-install", "hyperframes", "tts", falar(c["narracao"]), "-v", VOZ,
                            "-l", "pt-br", "-s", VELOCIDADE, "-o", str(wav), "--json"],
                           cwd=RAIZ, env=env, capture_output=True, text=True, timeout=600)
        if r.returncode != 0 or not wav.exists():
            raise RuntimeError(f"TTS falhou na cena {c['n']}: {r.stdout[-300:]} {r.stderr[-300:]}")
        c["duracao"] = round(duracao(wav) + FOLGA, 3)
    total = sum(c["duracao"] for c in roteiro["cenas"])
    return total


def main():
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
