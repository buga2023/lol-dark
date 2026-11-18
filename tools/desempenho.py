"""Acompanha o desempenho dos vídeos publicados e realimenta a esteira (workflow desempenho.yml, diário).

1. YouTube Data API (videos.list statistics): views, likes, comentários.
2. YouTube Analytics API (reports): views, averageViewPercentage (retenção), averageViewDuration,
   subscribersGained por vídeo. Precisa do escopo yt-analytics.readonly no refresh token.
3. Grava state/desempenho.jsonl (uma linha por vídeo por dia) e data/aprendizado.json (média de retenção por
   formato e por tipo de gancho) — o curador usa isso para dar mais espaço ao que retém mais.
4. Às segundas, manda um resumo da semana no Telegram.
TikTok e Instagram não têm API de leitura configurada: os números de lá ficam fora até existir app aprovado.
"""
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from comum import ESTADO, RAIZ, anexar_jsonl, ler_jsonl  # noqa: E402

APRENDIZADO = RAIZ / "data" / "aprendizado.json"


def token():
    from publicar import token as t
    return t()


def estatisticas(ids, tk):
    out = {}
    for i in range(0, len(ids), 50):
        r = requests.get("https://www.googleapis.com/youtube/v3/videos",
                         params={"part": "statistics", "id": ",".join(ids[i:i + 50])},
                         headers={"Authorization": f"Bearer {tk}"}, timeout=30).json()
        for it in r.get("items", []):
            s = it["statistics"]
            out[it["id"]] = {"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                             "comentarios": int(s.get("commentCount", 0))}
    return out


def analytics(ids, tk, inicio):
    """Retenção por vídeo. Se o token não tiver o escopo de Analytics, devolve {} sem derrubar o resto."""
    r = requests.get("https://youtubeanalytics.googleapis.com/v2/reports", headers={"Authorization": f"Bearer {tk}"},
                     params={"ids": "channel==MINE", "startDate": inicio, "endDate": date.today().isoformat(),
                             "metrics": "views,averageViewPercentage,averageViewDuration,subscribersGained",
                             "dimensions": "video", "filters": "video==" + ",".join(ids[:200])}, timeout=30)
    if r.status_code != 200:
        print(f"Analytics indisponível (HTTP {r.status_code}); só estatísticas públicas")
        return {}
    cols = [c["name"] for c in r.json().get("columnHeaders", [])]
    return {row[0]: dict(zip(cols[1:], row[1:])) for row in r.json().get("rows", [])}


def aprender(linhas):
    """Média de retenção por formato e por gancho (últimos 30 vídeos com dado)."""
    ult = {}
    for l in linhas:
        ult[l["youtube_id"]] = l
    agrup = {"formato": {}, "gancho_tipo": {}}
    for l in list(ult.values())[-30:]:
        ret = l.get("averageViewPercentage")
        if ret is None:
            continue
        for k in agrup:
            agrup[k].setdefault(l.get(k) or "?", []).append(float(ret))
    resumo = {k: {g: round(sum(v) / len(v), 1) for g, v in d.items()} for k, d in agrup.items()}
    APRENDIZADO.parent.mkdir(exist_ok=True)
    APRENDIZADO.write_text(json.dumps({"atualizado": date.today().isoformat(), "retencao_media": resumo},
                                      ensure_ascii=False, indent=1))
    return resumo


def main():
    pautas = [p for p in ler_jsonl(ESTADO / "pautas.jsonl") if p.get("youtube_id")]
    if not pautas:
        print("nenhum vídeo publicado ainda")
        return
    tk = token()
    ids = [p["youtube_id"] for p in pautas]
    est = estatisticas(ids, tk)
    ana = analytics(ids, tk, (date.today() - timedelta(days=90)).isoformat())
    hoje = date.today().isoformat()
    linhas = [{"dia": hoje, "youtube_id": p["youtube_id"], "pauta": p["id"], "formato": p.get("formato"),
               "gancho_tipo": p.get("gancho_tipo"), **est.get(p["youtube_id"], {}), **ana.get(p["youtube_id"], {})}
              for p in pautas]
    anexar_jsonl(ESTADO / "desempenho.jsonl", linhas)
    resumo = aprender(ler_jsonl(ESTADO / "desempenho.jsonl"))
    print(json.dumps(resumo, ensure_ascii=False))
    if date.today().weekday() == 0 and os.environ.get("TELEGRAM_BOT_TOKEN"):
        from comum import telegram
        top = sorted(linhas, key=lambda l: l.get("views", 0), reverse=True)[:3]
        texto = ("📊 Wardado — semana\n" + "\n".join(f"{l['pauta']}: {l.get('views', 0)} views, retenção "
                                                    f"{l.get('averageViewPercentage', '?')}%" for l in top)
                 + f"\n\nRetenção média por formato: {resumo['formato']}\nPor gancho: {resumo['gancho_tipo']}")
        telegram("sendMessage", {"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": texto[:4000]})


if __name__ == "__main__":
    main()
