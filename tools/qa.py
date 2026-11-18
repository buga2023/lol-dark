"""Passo 7: laudo técnico do MP4. Reprova sem áudio, fora de 1080x1920/30fps, duração errada, tela preta >0,5 s ou >50 MB."""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import ffprobe_json  # noqa: E402

MAX_MB = 50


def laudo(mp4, duracao_esperada=None, min_s=25, max_s=45):
    info = ffprobe_json(mp4)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    mb = Path(mp4).stat().st_size / 1e6
    fps = eval(v["r_frame_rate"]) if v else 0  # "30/1"
    preto = subprocess.run(["ffmpeg", "-v", "info", "-i", str(mp4), "-vf", "blackdetect=d=0.5:pix_th=0.10", "-an", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    trechos = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", preto)
    mudo = None
    if a:
        vol = subprocess.run(["ffmpeg", "-v", "info", "-i", str(mp4), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        m = re.search(r"mean_volume: (-?[\d.]+) dB", vol)
        mudo = m is None or float(m.group(1)) < -50
    checks = {
        "resolucao_1080x1920": bool(v) and (v["width"], v["height"]) == (1080, 1920),
        "fps_30": abs(fps - 30) < 0.01,
        "audio_presente": bool(a) and not mudo,
        f"duracao_{min_s}_{max_s}s": min_s <= dur <= max_s,
        "duracao_bate_cenas": duracao_esperada is None or abs(dur - duracao_esperada) <= 0.5,
        "sem_tela_preta": not trechos,
        f"abaixo_{MAX_MB}MB": mb < MAX_MB,
    }
    return {"aprovado": all(checks.values()), "checks": checks, "duracao": round(dur, 2), "mb": round(mb, 1),
            "trechos_pretos": trechos}


if __name__ == "__main__":
    esp = float(sys.argv[2]) if len(sys.argv) > 2 else None
    r = laudo(sys.argv[1], esp)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    sys.exit(0 if r["aprovado"] else 1)
