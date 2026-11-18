"""Título, descrição, legendas e hashtags por plataforma (skill wardado-canal + pesquisa de 17/11/2026).

YouTube: título até 60 caracteres com campeão ou patch; descrição = fato + fontes + aviso da Riot; 5 a 8 tags;
         3 hashtags no fim (as 3 primeiras aparecem acima do título; mais de 60 fazem o YouTube ignorar todas).
TikTok:  legenda curta (gancho reescrito + pergunta) e 3 a 5 hashtags.
Instagram: legenda um pouco mais longa (o que você aprende) e 5 hashtags; arquivo sem marca d'água de outro app.
"""
import re
import unicodedata

AVISO_RIOT = ("Wardado Clips was created under Riot Games' \"Legal Jibber Jabber\" policy using assets owned by Riot "
              "Games. Riot Games does not endorse or sponsor this project.")


def _tag(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", t)


def campeoes(roteiro):
    return list(dict.fromkeys(c["asset"].split("/")[-1] for c in roteiro["cenas"] if c["asset"].startswith("ddragon:")))


def titulo_curto(t, limite=60):
    t = t.strip()
    if len(t) <= limite:
        return t
    return t[:limite - 1].rsplit(" ", 1)[0].rstrip(",:;-–") + "…"


def gerar(roteiro, fontes, tema=None):
    chs = campeoes(roteiro)
    tema = tema or (chs[0] if chs else "lol")
    hashtags = ["#leagueoflegends", "#lol"] + [f"#{_tag(x)}" for x in chs[:2]] + [f"#{_tag(tema)}"]
    hashtags = list(dict.fromkeys(h for h in hashtags if len(h) > 2))[:5]
    yt_tags = list(dict.fromkeys(["league of legends", "lol"] + [c.lower() for c in chs] +
                                 [str(tema).lower(), "curiosidades lol", "wardado clips"]))[:8]
    titulo = titulo_curto(roteiro["titulo"])
    fato = (roteiro.get("angulo") or "").strip()
    linhas_fontes = "\n".join(f"- {f['url']}" for f in fontes)
    gancho = roteiro["cenas"][0]["narracao"].strip()
    pergunta = "E você, concorda?" if roteiro.get("tipo") == "noticia" else "Você sabia dessa?"
    return {
        "youtube": {"titulo": titulo,
                    "descricao": f"{fato}\n\nFontes:\n{linhas_fontes}\n\n{' '.join(hashtags[:3])}\n\n{AVISO_RIOT}",
                    "tags": yt_tags},
        "tiktok": {"legenda": f"{gancho} {pergunta} {' '.join(hashtags)}"[:2200]},
        "instagram": {"legenda": f"{titulo}\n\n{fato}\n\n{pergunta}\n\nFontes na bio do YouTube @wardadoclips.\n\n"
                                 f"{' '.join(hashtags)}"[:2200]},
        # compatibilidade com publicacao.json da skill wardado-canal
        "titulo": titulo, "descricao": f"{fato}\n\nFontes:\n{linhas_fontes}\n\n{AVISO_RIOT}", "tags": yt_tags,
    }
