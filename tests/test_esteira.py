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


def test_curador_nao_repete_tema_em_5_dias():
    itens = [{"id": f"i{k}", "url": f"https://x/patch-26-{k}-notes/", "fonte": "patch", "coletado_em": f"2026-11-1{k}"} for k in range(5)]
    itens += [{"id": "dup", "url": "https://x/outro/patch-26-3-notes/", "fonte": "patch", "coletado_em": "2026-11-19"}]
    pautas, temas = [], []
    for dia in range(5):
        p = curar(itens, pautas, datetime(2026, 11, 20 + dia, 12, tzinfo=timezone.utc))
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
    assert not r["aprovado"] and not r["checks"]["audio_presente"]


def test_qa_reprova_tela_preta(mp4s):
    r = laudo(mp4s[1])
    assert not r["aprovado"] and not r["checks"]["sem_tela_preta"]
