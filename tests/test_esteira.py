import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
FIX = RAIZ / "tests" / "fixtures"

from comum import validar_roteiro  # noqa: E402
from verificar import verificar  # noqa: E402
import coletar as col  # noqa: E402
from curar import curar  # noqa: E402
from critico import avaliar  # noqa: E402
from roteirizar import roteirizar  # noqa: E402
from qa import laudo  # noqa: E402

FONTE = (FIX / "patch_26_23.txt").read_text()
ok = lambda: json.loads((FIX / "roteiro_ok.json").read_text())  # noqa: E731


def test_roteiro_ok_passa_no_schema_e_no_verificador():
    assert validar_roteiro(ok()) == []
    assert verificar(ok(), {"f1": FONTE}) == []


def test_verificador_rejeita_numero_inventado():
    r = json.loads((FIX / "roteiro_numero_inventado.json").read_text())
    p = verificar(r, {"f1": FONTE})
    assert any("900" in x for x in p)


def test_roteiro_longo_reprovado():
    r = json.loads((FIX / "roteiro_longo.json").read_text())
    assert validar_roteiro(r)  # rejeitado (schema ou contagem de palavras)


def test_frase_proibida_reprova():
    r = ok()
    r["cenas"][5]["narracao"] = "Comenta aí qual você vai testar."
    assert any("proibida" in e for e in validar_roteiro(r))


class Resp:
    def __init__(self, t):
        self.text = t

    def raise_for_status(self):
        pass


def falso_get(url, **kw):
    if "ddragon" in url:
        raise ConnectionError("fora do ar")
    if url.endswith("/tags/patch-notes/"):
        return Resp((FIX / "html" / "indice_patch.html").read_text())
    if "patch" in url:
        return Resp((FIX / "html" / "patch_26_23.html").read_text())
    raise ConnectionError("fora do ar")


def test_coletor_nao_duplica_e_sobrevive_a_fonte_fora(tmp_path):
    arq = tmp_path / "itens.jsonl"
    n1, f1 = col.coletar(arq, get=falso_get)
    n2, _ = col.coletar(arq, get=falso_get)
    linhas = arq.read_text().splitlines()
    assert n1 and f1  # coletou do patch mesmo com as outras fontes fora
    assert len(linhas) == len({json.loads(x)["hash"] for x in linhas})
    assert all(i["hash"] not in {json.loads(x)["hash"] for x in linhas[:len(n1)]} for i in n2)


def test_curador_so_usa_o_patch_mais_recente():
    itens = [{"id": f"p{k}", "url": f"https://x/patch-26-{k}-notes/", "fonte": "patch", "coletado_em": "2026-11-17"} for k in (18, 23, 20)]
    p = curar(itens, [], datetime(2026, 11, 18, 12, tzinfo=timezone.utc), perenes=False)
    assert p["tema"] == "patch-26-23"
    assert curar(itens, [p], datetime(2026, 11, 18, 16, tzinfo=timezone.utc), perenes=False) is None


def test_curador_nao_repete_tema_em_5_dias():
    itens = [{"id": f"i{k}", "url": f"https://ddragon/champion/C{k}.json", "fonte": "lore", "coletado_em": f"2026-11-1{k}"} for k in range(5)]
    itens += [{"id": "dup", "url": "https://outro/champion/C3.json", "fonte": "lore", "coletado_em": "2026-11-19"}]
    pautas, temas = [], []
    for dia in range(5):
        p = curar(itens, pautas, datetime(2026, 11, 20 + dia, 12, tzinfo=timezone.utc), perenes=False)
        assert p is not None
        pautas.append(p)
        temas.append(p["tema"])
    assert len(temas) == len(set(temas))
    assert [p["variacao"] for p in pautas[:2]] != [pautas[0]["variacao"]] * 2


def test_critico_reprova_abaixo_de_80_e_loop_reescreve():
    notas = iter([60, 85])

    def juiz(s, u, temperatura=0):
        n = next(notas)
        from critico import RUBRICA
        return {"criterios": {k: {"nota": n * p / 100} for k, (p, _) in RUBRICA.items()}, "melhorias": ["gancho fraco"]}

    chamadas = []

    def gerar(s, u, temperatura=0.9):
        chamadas.append(u)
        return ok()

    pauta = {"id": "2026-11-17-patch-26-23", "tipo": "noticia", "formato": "patch60", "variacao": 0}
    fonte = {"url": "https://x/", "coletado_em": "2026-11-17", "texto_bruto": FONTE}
    rot, rodadas = roteirizar(pauta, fonte, [], gerar=gerar, juiz=juiz, log=lambda *_: None)
    assert [r["nota"] for r in rodadas] == [60, 85]
    assert rot["nota_critico"]["nota"] == 85
    assert "REPROVADA" in chamadas[1]


def test_critico_zera_com_numero_inventado():
    r = json.loads((FIX / "roteiro_numero_inventado.json").read_text())
    av = avaliar(r, {"f1": FONTE}, juiz=lambda *a, **k: pytest.fail("juiz não deveria ser chamado"))
    assert av["nota"] == 0 and not av["aprovado"]


@pytest.fixture(scope="module")
def mp4s(tmp_path_factory):
    d = tmp_path_factory.mktemp("mp4")
    sem_audio, preto = d / "sem_audio.mp4", d / "preto.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=1080x1920:r=30:d=30",
                    "-pix_fmt", "yuv420p", str(sem_audio)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=1080x1920:r=30:d=28",
                    "-f", "lavfi", "-i", "color=black:s=1080x1920:r=30:d=2", "-f", "lavfi", "-i", "sine=f=300:d=30",
                    "-filter_complex", "[0][1]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2", "-pix_fmt", "yuv420p",
                    "-shortest", str(preto)], check=True)
    return sem_audio, preto


def test_qa_reprova_sem_audio(mp4s):
    r = laudo(mp4s[0])
    assert not r["aprovado"] and not r["checks"]["tem_audio"]


def test_qa_reprova_tela_preta(mp4s):
    r = laudo(mp4s[1])
    assert not r["aprovado"] and not r["checks"]["tela_preta"]


def test_lint_editorial_barra_copia_e_gancho_repetido():
    from lint_editorial import lint
    r = ok()
    r["cenas"][1]["narracao"] = "Ezreal teve desempenho abaixo do esperado na maioria dos ranques, mesmo estando bem forte."
    r["gancho_tipo"] = "contradicao"
    p = lint(r, {"f1": FONTE}, [{"gancho_tipo": "contradicao"}])
    assert any("copiado" in x for x in p) and any("gancho_tipo" in x for x in p)
    assert lint(ok(), {"f1": FONTE}, []) == []


def test_pesquisa_so_aceita_trecho_que_existe_na_pagina():
    from pesquisar import pesquisar
    pagina = Resp("<html><body><p>O Urf foi um campeão anunciado no Dia da Mentira de 2010.</p></body></html>")
    ev = {"id": "ev-002", "pergunta": "De onde veio o Urf?"}
    bom = lambda s, u: {"fontes": [{"url": "https://www.leagueoflegends.com/x", "trechos": ["anunciado no Dia da Mentira de 2010"]}]}  # noqa: E731
    inventado = lambda s, u: {"fontes": [{"url": "https://www.leagueoflegends.com/x", "trechos": ["criado por um estagiário em 2005"]}]}  # noqa: E731
    fora = lambda s, u: {"fontes": [{"url": "https://blogqualquer.com/x", "trechos": ["anunciado no Dia da Mentira de 2010"]}]}  # noqa: E731
    assert pesquisar(ev, bom, get=lambda *a, **k: pagina)["fonte"] == "evergreen"
    assert pesquisar(ev, inventado, get=lambda *a, **k: pagina) is None
    assert pesquisar(ev, fora, get=lambda *a, **k: pagina) is None


def test_curador_rodizia_series_perenes_e_patch_vem_primeiro():
    agora = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    patch = [{"id": "p", "url": "https://x/patch-26-23-notes/", "fonte": "patch", "coletado_em": "2026-11-17"}]
    assert curar(patch, [], agora)["tema"] == "patch-26-23"
    pautas = []
    for h in range(3):
        p = curar([], pautas, datetime(2026, 11, 18, 12 + h, tzinfo=timezone.utc))
        pautas.append(p)
    assert pautas[0]["item_id"] == "ev-001"
    assert len({p["serie"] for p in pautas[1:]}) == 2 and pautas[1]["serie"] != pautas[0]["serie"]


def test_metadados_por_plataforma():
    from metadados import AVISO_RIOT, gerar
    m = gerar(ok(), [{"url": "https://www.leagueoflegends.com/x"}], "patch 26.23")
    assert len(m["youtube"]["titulo"]) <= 60 and AVISO_RIOT in m["youtube"]["descricao"]
    assert 5 <= len(m["youtube"]["tags"]) <= 8 and {"league of legends", "lol"} <= set(m["youtube"]["tags"])
    assert 3 <= m["tiktok"]["legenda"].count("#") <= 5 and "https://www.leagueoflegends.com/x" in m["youtube"]["descricao"]
