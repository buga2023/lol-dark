"""Agenda, resultados e estatísticas do competitivo pela API pública da Leaguepedia (Cargo), sem chave.

Licença dos dados: CC BY-SA 3.0 — toda descrição de vídeo que usar isto credita "Dados: Leaguepedia (lol.fandom.com)".
Uso educado: 1 consulta por tabela por execução, com User-Agent próprio.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).parent))

API = "https://lol.fandom.com/api.php"
LIGAS = ("CBLOL", "LCK", "LPL", "LEC", "LTA", "LCP", "MSI", "World Championship", "Worlds", "First Stand")
CREDITO = "Dados: Leaguepedia (lol.fandom.com), CC BY-SA 3.0"


def cargo(tables, fields, where, order_by, limit=100, join_on=None):
    q = {"action": "cargoquery", "format": "json", "tables": tables, "fields": fields, "where": where,
         "order_by": order_by, "limit": limit}
    if join_on:
        q["join_on"] = join_on
    r = subprocess.run(["curl", "-s", "--max-time", "40", "-A", "WardadoClips-fontes/1.0", f"{API}?{urlencode(q)}"],
                       capture_output=True, text=True, timeout=60)
    return [x["title"] for x in json.loads(r.stdout).get("cargoquery", [])]


def principal(pagina):
    return any(l.lower() in pagina.lower() for l in LIGAS) and "academy" not in pagina.lower()


def agenda(agora=None, dias=7):
    agora = agora or datetime.now(timezone.utc)
    ini, fim = agora.strftime("%Y-%m-%d %H:%M:%S"), (agora + timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    linhas = cargo("MatchSchedule", "DateTime_UTC,Team1,Team2,OverviewPage,BestOf",
                   f"DateTime_UTC >= '{ini}' AND DateTime_UTC <= '{fim}'", "DateTime_UTC", 200)
    return [l for l in linhas if principal(l["OverviewPage"]) and l["Team1"] and l["Team2"]]


def resultados(agora=None, dias=7):
    agora = agora or datetime.now(timezone.utc)
    ini, fim = (agora - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S"), agora.strftime("%Y-%m-%d %H:%M:%S")
    linhas = cargo("MatchSchedule", "DateTime_UTC,Team1,Team2,OverviewPage,Winner,Team1Score,Team2Score",
                   f"DateTime_UTC >= '{ini}' AND DateTime_UTC <= '{fim}' AND Winner IS NOT NULL", "DateTime_UTC DESC", 200)
    return [l for l in linhas if principal(l["OverviewPage"])]


def itens(agora=None):
    """Dois itens para o curador (fonte 'esports'): a semana que vem e a semana que passou. Horário em Brasília."""
    agora = agora or datetime.now(timezone.utc)
    sem = agora.strftime("%G-W%V")
    out = []
    for tipo, linhas in (("agenda", agenda(agora)), ("resultados", resultados(agora))):
        if not linhas:
            continue
        txt = [f"## {'Agenda' if tipo == 'agenda' else 'Resultados'} do competitivo, semana {sem} ({CREDITO})"]
        for l in linhas[:60]:
            brt = datetime.strptime(l["DateTime UTC"], "%Y-%m-%d %H:%M:%S") - timedelta(hours=3)
            base = f"- {brt:%d/%m %H:%M} (Brasília) · {l['OverviewPage']} · {l['Team1']} x {l['Team2']}"
            if tipo == "agenda":
                base += f" · melhor de {l.get('BestOf') or '?'}"
            else:
                venc = l["Team1"] if l.get("Winner") == "1" else l["Team2"]
                base += f" · placar {l.get('Team1Score')} a {l.get('Team2Score')} · vencedor: {venc}"
            txt.append(base)
        url = f"https://lol.fandom.com/wiki/{linhas[0]['OverviewPage'].replace(' ', '_')}#{tipo}-{sem}"
        h = hashlib.sha256(url.encode()).hexdigest()[:16]
        out.append({"id": h, "url": url, "fonte": "esports", "titulo": f"{tipo} {sem}", "texto_bruto": "\n".join(txt),
                    "coletado_em": agora.isoformat(timespec="seconds"), "hash": h, "credito": CREDITO})
    return out


if __name__ == "__main__":
    for it in itens():
        print(it["titulo"], len(it["texto_bruto"].splitlines()) - 1, "jogos")
        print("\n".join(it["texto_bruto"].splitlines()[:6]))
