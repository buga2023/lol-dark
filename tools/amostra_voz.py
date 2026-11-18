"""Gera a narração de um roteiro com o provedor pedido e salva os WAVs (usado pelo workflow amostra-voz.yml).
Uso: python tools/amostra_voz.py data/exemplos_aprovados/patch60-azir-84.json saida/ voicestudio
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from narrar import narrar  # noqa: E402

rot = json.loads(Path(sys.argv[1]).read_text())
saida = Path(sys.argv[2])
total = narrar(rot, saida, sys.argv[3] if len(sys.argv) > 3 else None)
(saida / "roteiro.json").write_text(json.dumps(rot, ensure_ascii=False, indent=1))
print(f"{rot.get('voz')}: {total:.1f}s")
