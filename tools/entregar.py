"""Passo 8: MP4 + metadados -> Telegram (preview, aviso de publicação ou pedido de aprovação)."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import telegram  # noqa: E402


def legenda(rot, extra=""):
    nota = (rot.get("nota_critico") or {}).get("nota")
    fontes = "\n".join(f["url"] for f in rot["fontes"])
    t = f"{rot['titulo']}\n\nnota do crítico: {nota}\n{extra}\n\nfontes:\n{fontes}\n\n#" + " #".join(rot["tags"][:8])
    return t[:1000]


def entregar(rot, mp4, botoes=True, extra=""):
    chat = os.environ["TELEGRAM_CHAT_ID"]
    teclado = {"inline_keyboard": [[{"text": "✅ Aprovar", "callback_data": f"ok:{rot['id']}"},
                                    {"text": "🔁 Refazer", "callback_data": f"refazer:{rot['id']}"},
                                    {"text": "🗑 Descartar", "callback_data": f"descartar:{rot['id']}"}]]}
    dados = {"chat_id": chat, "caption": legenda(rot, extra), "supports_streaming": "true"}
    if botoes:
        dados["reply_markup"] = json.dumps(teclado)
    with open(mp4, "rb") as f:
        msg = telegram("sendVideo", dados, {"video": (Path(mp4).name, f, "video/mp4")})
    # legendas prontas para colar no TikTok e no Instagram (com hashtags), em mensagens separadas
    from metadados import gerar
    m = gerar(rot, rot.get("fontes", []))
    telegram("sendMessage", {"chat_id": chat, "text": "TikTok:\n\n" + m["tiktok"]["legenda"][:3900]})
    telegram("sendMessage", {"chat_id": chat, "text": "Instagram:\n\n" + m["instagram"]["legenda"][:3900]})
    return msg["message_id"]


if __name__ == "__main__":
    r = json.loads(Path(sys.argv[1]).read_text())
    print(entregar(r, sys.argv[2]))
