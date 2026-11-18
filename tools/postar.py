"""Posta o vídeo pronto mais antigo do estoque (rodado pelo postar.yml às 09h, 13h e 19h de Salvador).

O workflow baixa o artefato antes (gh run download) para .tmp/postar/<id>/. Aqui: publica no YouTube,
manda MP4 + descrição no Telegram (para TikTok e Instagram até as APIs aprovarem) e grava o estado.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import ESTADO, TMP, alertar, gravar_jsonl, ler_jsonl  # noqa: E402


def proximo(pautas):
    prontos = sorted((p for p in pautas if p["estado"] == "pronto"), key=lambda p: p.get("pronto_em", ""))
    return prontos[0] if prontos else None


def main():
    pautas = ler_jsonl(ESTADO / "pautas.jsonl")
    if "--qual" in sys.argv:  # o workflow pergunta qual artefato baixar
        p = proximo(pautas)
        print(json.dumps({"id": p["id"], "run_id": p.get("run_id"), "artefato": p.get("artefato")} if p else {}))
        return
    p = proximo(pautas)
    if not p:
        alertar("estoque vazio no horário de postar: nenhum vídeo pronto passou nas travas")
        print("estoque vazio")
        return
    pasta = TMP / "postar" / p["id"]
    mp4 = next(pasta.rglob("*.mp4"), None)
    rot_arq = next(pasta.rglob("roteiro.json"), None)
    if not mp4 or not rot_arq:
        p["estado"], p["ultimo_erro"] = "erro", "artefato do estoque não encontrado (expirou?)"
        gravar_jsonl(ESTADO / "pautas.jsonl", pautas)
        alertar(f"{p['id']}: artefato não encontrado; pauta volta para a fila")
        sys.exit(1)
    rot = json.loads(rot_arq.read_text())
    from entregar import entregar
    from publicar import publicar
    extra = ""
    try:
        vid, priv = publicar(rot, mp4)
        p["youtube_id"], p["estado"] = vid, ("publicado" if priv == "public" else "publicado_privado")
        extra = f"YouTube: https://youtu.be/{vid} ({priv})"
        if priv != "public":
            extra += "\nAPI do YouTube ainda não auditada: o vídeo ficou privado; poste pelo app."
    except Exception as e:
        p["estado"], p["ultimo_erro"] = "postar_manual", f"YouTube: {str(e)[:200]}"
        extra = f"Upload automático falhou ({str(e)[:120]}). Poste este MP4 pelo app."
    gravar_jsonl(ESTADO / "pautas.jsonl", pautas)
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        entregar(rot, mp4, botoes=False, extra=extra + "\nTikTok e Instagram: poste este MP4 com a descrição abaixo.")
    print(f"postado: {p['id']} -> {p['estado']} {extra}")


if __name__ == "__main__":
    main()
