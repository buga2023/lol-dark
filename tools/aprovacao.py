"""Passo 9: lê cliques do Telegram (getUpdates) e muda o estado da pauta. Só aceita o TELEGRAM_CHAT_ID."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import ESTADO, gravar_jsonl, ler_jsonl, telegram  # noqa: E402

ACOES = {"ok": "aprovado", "refazer": "refazer", "descartar": "descartado"}


def processar(updates, pautas, chat_id):
    mudou, comentario = [], {}
    for u in updates:
        msg = u.get("message")
        if msg and str(msg["chat"]["id"]) == chat_id and msg.get("reply_to_message"):
            comentario[msg["reply_to_message"]["message_id"]] = msg.get("text", "")
        cb = u.get("callback_query")
        if not cb or str(cb["message"]["chat"]["id"]) != chat_id:
            continue
        acao, _, pid = cb["data"].partition(":")
        for p in pautas:
            if p["id"] == pid and acao in ACOES and p["estado"] in ("aguardando_ok", "publicado_privado"):
                p["estado"] = ACOES[acao]
                if acao == "refazer":
                    p["comentario"] = comentario.get(cb["message"]["message_id"], "")
                    p["estado"] = "pauta"
                mudou.append((pid, p["estado"], cb["id"]))
    return mudou


def main():
    chat = os.environ["TELEGRAM_CHAT_ID"]
    arq_off = ESTADO / "telegram_offset.txt"
    off = int(arq_off.read_text()) if arq_off.exists() else 0
    ups = telegram("getUpdates", {"offset": off, "timeout": 0, "allowed_updates": json.dumps(["callback_query", "message"])})
    pautas = ler_jsonl(ESTADO / "pautas.jsonl")
    for pid, est, cbid in processar(ups, pautas, chat):
        telegram("answerCallbackQuery", {"callback_query_id": cbid, "text": f"{pid}: {est}"})
        print(pid, est)
    gravar_jsonl(ESTADO / "pautas.jsonl", pautas)
    if ups:
        arq_off.write_text(str(ups[-1]["update_id"] + 1))


if __name__ == "__main__":
    main()
