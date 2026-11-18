"""Passo 4: todo número dito ou mostrado precisa existir no texto da fonte da cena."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import numeros, validar_roteiro  # noqa: E402


def verificar(roteiro, textos_fonte):
    """textos_fonte: {fonte_id: texto}. Retorna lista de problemas (vazia = aprovado)."""
    problemas = list(validar_roteiro(roteiro))
    for c in roteiro["cenas"]:
        dito = " ".join(filter(None, [c["narracao"], c["texto_tela"], c.get("antes"), c.get("depois")]))
        nums = numeros(dito)
        if not nums:
            continue
        if not c["fonte_id"]:
            problemas.append(f"cena {c['n']}: tem número ({', '.join(sorted(nums))}) e nenhuma fonte")
            continue
        texto = textos_fonte.get(c["fonte_id"])
        if texto is None:
            problemas.append(f"cena {c['n']}: texto da fonte {c['fonte_id']} ausente")
            continue
        faltam = nums - numeros(texto)
        if faltam:
            problemas.append(f"cena {c['n']}: número(s) sem fonte: {', '.join(sorted(faltam))}")
    return problemas


def main():
    rot = json.loads(Path(sys.argv[1]).read_text())
    fontes = {}
    for par in sys.argv[2:]:
        fid, arq = par.split("=", 1)
        fontes[fid] = Path(arq).read_text()
    p = verificar(rot, fontes)
    print(json.dumps({"aprovado": not p, "problemas": p}, ensure_ascii=False, indent=1))
    sys.exit(1 if p else 0)


if __name__ == "__main__":
    main()
