# POPs (um por script)

| Script | Entra | Sai | Falha conhecida → o que fazer |
| --- | --- | --- | --- |
| coletar.py | sites da Riot | `state/itens.jsonl` | todas as fontes falham → alerta "coleta voltou vazia"; conferir HTML da Riot e as fixtures |
| curar.py | itens + pautas | 1 pauta | `None` → sem pauta nova no dia (normal) |
| roteirizar.py | pauta + item | `roteiro.json` + `rodadas.json` | 3 rodadas < 80 → pauta `rejeitado`, alerta |
| critico.py | roteiro + fonte | nota 0–100 | erro do Gemini → rodada conta como reprovada |
| verificar.py | roteiro + fonte | problemas | número sem fonte → nota 0 |
| narrar.py | cenas | WAV por cena + `duracao` | fora de 25–45 s → `erro`; nome errado → `assets/pronuncia.json` |
| legendas.py | WAVs | tempo por palavra | sem whisper → tempo proporcional |
| compor.py | roteiro + WAVs | MP4 | lint com erro → `erro` |
| qa.py | MP4 | laudo | reprovado → `erro` |
| entregar.py | MP4 | Telegram | MP4 > 50 MB é barrado antes, no QA |
| publicar.py | MP4 | YouTube id | OAuth 400 → refresh token expirou; gerar de novo (ver README) |
| aprovacao.py | cliques | estado | só aceita `TELEGRAM_CHAT_ID` |
| run_pipeline.py | tudo | estado final | 3 falhas → `descartado` |
