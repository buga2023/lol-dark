#!/usr/bin/env bash
# Ciclo contínuo (timer wardado-ciclo): 1 vídeo por volta, formatos em rodízio, revisão independente e registro no vault.
# Não publica: o vídeo vai para entregas/ciclo-<data>/ e para o estoque de revisão. Para: systemctl --user disable --now wardado-ciclo.timer
cd "$(dirname "$0")/.."
LIVRE=$(df --output=avail -m . | tail -1)
[ "$LIVRE" -lt 800 ] && { echo "disco com ${LIVRE} MB livres: pulo esta volta"; exit 0; }
pgrep -f "[l]oop_exemplos|exemplos.py" >/dev/null && { echo "outra produção rodando: pulo"; exit 0; }
N=$(cat entregas/.rodizio 2>/dev/null || echo 0); L=$(echo A B C | cut -d' ' -f$((N % 3 + 1))); echo $((N + 1)) > entregas/.rodizio
rm -f "entregas/pontos-$L.json.usado"; [ -f "entregas/pontos-$L.json" ] && cp "entregas/pontos-$L.json" "entregas/pontos-$L.json.usado"
LOL_VOICESTUDIO_URL=http://127.0.0.1:3900 LOL_LLM=claude LOL_LLM_ESCRITOR=agy LOL_AGY_MODELO=gemini-3.8-flash-high LOL_WORKERS=3 \
  .venv/bin/python -u tools/exemplos.py "$L" --destino="ciclo-$(date +%Y%m%d-%H%M)-$L"
find .tmp -maxdepth 1 -name "20*" -mtime +2 -exec rm -rf {} +   # disco: intermediários com mais de 2 dias
