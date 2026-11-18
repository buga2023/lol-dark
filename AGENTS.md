# lol-dark

Esteira da Wardado Clips: 3 Shorts de League of Legends por dia (YouTube, Instagram, TikTok) a partir das notas oficiais da Riot.
Contexto e decisões: nota `memory/projects/lol-dark.md` no vault Second-Brain.

- A Lei está em `gemini.md`; leia antes de mudar qualquer script.
- Rodar local: `uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -r requirements.txt && npm ci`,
  depois `.venv/bin/python tools/run_pipeline.py --dry-run` (precisa de `GEMINI_API_KEY`) ou
  `--roteiro tests/fixtures/roteiro_ok.json --dry-run` (sem chave).
- Pronto = `pytest tests/` verde **e** o MP4 da amostra passa no `tools/qa.py`.
- Roteiro: skill `.claude/skills/roteiro-short-lol`. Vídeo: skill `.claude/skills/video-short-lol`.
- Nunca imprima resposta crua de API: o repositório e os logs do Actions são públicos.
