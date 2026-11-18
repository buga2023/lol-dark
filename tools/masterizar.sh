#!/usr/bin/env bash
# Masteriza a narração e junta ao vídeo sem fade no fim (para o loop fechar).
# Uso: tools/masterizar.sh video_sem_master.mp4 saida.mp4 [trilha.wav]
set -euo pipefail
IN="$1"; OUT="$2"; TRILHA="${3:-}"

# Voz: corta grave inútil, de-esser leve, compressão suave, realce de presença.
VOZ="highpass=f=80,deesser=i=0.3,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2,equalizer=f=3500:t=q:w=1.2:g=1.5,equalizer=f=9000:t=q:w=0.8:g=2"
ALVO="loudnorm=I=-14:TP=-1.5:LRA=7"

if [ -n "$TRILHA" ]; then
  # Trilha em loop até o último quadro, baixando sozinha quando a voz entra.
  ffmpeg -v error -y -i "$IN" -stream_loop -1 -i "$TRILHA" -filter_complex \
    "[0:a]${VOZ},asplit=2[v1][v2];[1:a]volume=-18dB[m];[m][v2]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[md];[v1][md]amix=inputs=2:duration=first:normalize=0,${ALVO}[a]" \
    -map 0:v -map "[a]" -c:v libx264 -preset slow -crf 16 -maxrate 12M -bufsize 24M -pix_fmt yuv420p \
    -c:a aac -b:a 256k -ar 48000 -movflags +faststart -shortest "$OUT"
else
  ffmpeg -v error -y -i "$IN" -af "${VOZ},${ALVO}" \
    -c:v libx264 -preset slow -crf 16 -maxrate 12M -bufsize 24M -pix_fmt yuv420p \
    -c:a aac -b:a 256k -ar 48000 -movflags +faststart "$OUT"
fi
