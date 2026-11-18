# Achados

- Kokoro pt-br funciona com `pm_alex` (voz masculina) e `pf_dora`. Exige Python ≤ 3.12 (`kokoro-onnx`); na máquina, `.venv` com 3.12 via uv.
- `hyperframes transcribe -m small -l pt` dá tempo por palavra bom o bastante para legenda karaokê; o texto exibido vem do roteiro.
- Notas de patch pt-br: índice em `/pt-br/news/tags/patch-notes/`, página `league-of-legends-patch-26-NN-notes`. Números no formato `350/550/750` e `1.275`.
- Data Dragon: splash em `cdn/img/champion/splash/<Chave>_0.jpg`; chave do K'Sante é `KSante`.
- Render de 39 s em 1080×1920 high: ~55 s com 4 workers nesta máquina.
- Replays de transmissão do LoL Esports: risco de claim. Jogadas de pro entram reconstruídas com arte e dados.
