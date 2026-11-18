"""Passo 10: upload no YouTube (videos.insert, upload resumable) com refresh token OAuth.

Projeto de API não auditado: o YouTube trava o vídeo como privado. Até a auditoria, LOL_YT_PRIVACIDADE=private
e o vídeo também vai para o Telegram para postar pelo app; depois da auditoria, public.
"""
import json
import os
import sys
from pathlib import Path

import requests

AVISO = ("Este conteúdo não é endossado pela Riot Games. League of Legends e Riot Games são marcas "
         "comerciais ou registradas da Riot Games, Inc.")


def token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"OAuth do YouTube falhou ({r.status_code}): token expirado ou revogado")
    return r.json()["access_token"]


def publicar(rot, mp4):
    from metadados import gerar
    yt = gerar(rot, rot.get("fontes", []))["youtube"]
    meta = {"snippet": {"title": yt["titulo"], "description": yt["descricao"][:4900], "tags": yt["tags"],
                        "categoryId": "20", "defaultLanguage": "pt-BR", "defaultAudioLanguage": "pt-BR"},
            "status": {"privacyStatus": os.environ.get("LOL_YT_PRIVACIDADE", "private"),
                       "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}}
    tk = token()
    tam = Path(mp4).stat().st_size
    ini = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                        headers={"Authorization": f"Bearer {tk}", "Content-Type": "application/json",
                                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(tam)},
                        data=json.dumps(meta), timeout=60)
    if ini.status_code != 200:
        raise RuntimeError(f"YouTube recusou o upload ({ini.status_code}): {ini.text[:200]}")
    with open(mp4, "rb") as f:
        up = requests.put(ini.headers["Location"], headers={"Authorization": f"Bearer {tk}", "Content-Type": "video/mp4"},
                          data=f, timeout=900)
    if up.status_code not in (200, 201):
        raise RuntimeError(f"upload falhou ({up.status_code})")
    j = up.json()
    return j["id"], j["status"]["privacyStatus"]


if __name__ == "__main__":
    r = json.loads(Path(sys.argv[1]).read_text())
    print(publicar(r, sys.argv[2]))
