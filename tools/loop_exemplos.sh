#!/usr/bin/env bash
# Refaz o exemplo até sair (APROVADO ou REPROVADO com laudo), no máximo 4 tentativas. Uso: tools/loop_exemplos.sh A
L="$1"; cd "$(dirname "$0")/.."
for t in 1 2 3 4; do
  # para quando o vídeo passou no qa.py E o revisor independente aprovou
  [ -f "entregas/exemplo-$L/resumo.json" ] && grep -q '"resultado": "APROVADO"' "entregas/exemplo-$L/resumo.json" \
    && ! grep -q 'REPROVADO_REVISOR' "entregas/exemplo-$L/resumo.json" && break
  [ -d "entregas/exemplo-$L" ] && mv "entregas/exemplo-$L" "entregas/tentativa-$L-$(date +%H%M%S)"
  echo "[$L] tentativa $t"
  LOL_VOICESTUDIO_URL=http://127.0.0.1:3900 LOL_LLM=claude LOL_LLM_ESCRITOR=agy LOL_AGY_MODELO=gemini-3.8-flash-high LOL_WORKERS=3 \
    .venv/bin/python -u tools/exemplos.py "$L"
done
# entrega final: copia para Downloads o melhor resultado desta letra
mkdir -p ~/Downloads/wardado-exemplos/exemplo-$L
[ -d "entregas/exemplo-$L" ] && cp -r entregas/exemplo-$L/. ~/Downloads/wardado-exemplos/exemplo-$L/
