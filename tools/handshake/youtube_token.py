"""Gera o YT_REFRESH_TOKEN uma vez, na sua máquina (abre o navegador no consentimento do Google).

Uso: YT_CLIENT_ID=... YT_CLIENT_SECRET=... .venv/bin/python tools/handshake/youtube_token.py
Imprime o refresh token só no seu terminal; grave-o com `gh secret set YT_REFRESH_TOKEN`.
"""
import http.server
import os
import urllib.parse
import webbrowser

import requests

ESCOPO = ("https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly "
          "https://www.googleapis.com/auth/yt-analytics.readonly")
PORTA = 8765
cid, sec = os.environ["YT_CLIENT_ID"], os.environ["YT_CLIENT_SECRET"]
redir = f"http://127.0.0.1:{PORTA}/"
url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": cid, "redirect_uri": redir, "response_type": "code", "scope": ESCOPO,
    "access_type": "offline", "prompt": "consent"})
codigo = {}


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        codigo.update(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query))
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Pronto, pode fechar esta aba.".encode())

    def log_message(self, *a):
        pass


print("Abrindo o navegador. Se não abrir, acesse:\n" + url)
webbrowser.open(url)
http.server.HTTPServer(("127.0.0.1", PORTA), H).handle_request()
r = requests.post("https://oauth2.googleapis.com/token", data={
    "code": codigo["code"][0], "client_id": cid, "client_secret": sec, "redirect_uri": redir,
    "grant_type": "authorization_code"}, timeout=30).json()
print("\nYT_REFRESH_TOKEN =", r["refresh_token"])
