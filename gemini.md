# A Lei — lol-dark

Regras que nenhum script pode violar. Mudou aqui, muda o código e os testes.

## Payload
`schemas/roteiro.schema.json`. Tudo antes do roteiro existe para produzi-lo; tudo depois só o consome.
Estado de cada pauta: `pauta → roteirizado → verificado → narrado → renderizado → qa_ok → (aguardando_ok → aprovado) → publicado`.
Laterais: `rejeitado` (nenhuma rodada chegou a 80), `erro` (volta até 3 vezes), `descartado`, `publicado_privado`.

## Portões
1. **Determinístico** (`comum.validar_roteiro` + `verificar.py`): schema, 60–110 palavras, frase ≤ 14 palavras,
   texto de tela ≤ 6 palavras, frases proibidas, todo número dito ou mostrado existe no texto da fonte. Falhou = nota 0.
2. **Crítico** (`critico.py`): rubrica de 7 critérios, soma 100. Só segue com **nota ≥ 80**. Abaixo, o roteirista
   reescreve com o feedback, até 3 rodadas. Nenhuma passou: sem vídeo no dia (não publicar é melhor que publicar fraco).
3. **QA do MP4** (`qa.py`): 1080×1920, 30 fps, áudio audível, 25–45 s, duração = soma das cenas ± 0,5 s,
   nenhum preto > 0,5 s, < 50 MB.

## Escrita e vídeo
Skills do repositório: `.claude/skills/roteiro-short-lol` (prompt do roteirista, lido pelo `roteirizar.py`)
e `.claude/skills/video-short-lol` (regras visuais aplicadas pelo `compor.py`).
Proibido: logo da Riot, trecho de transmissão ou de outro criador, imagem de campeão gerada por IA, avatar sintético.

## Correções da spec original (2026-11-17)
1. Escrita concorrente no branch `state`: os 3 workflows usam `concurrency: state`, e o push faz rebase com até 4 tentativas.
2. Token do YouTube: app OAuth em modo de teste expira o refresh token em 7 dias. Publicar o app OAuth (status "Em produção")
   ao criar as credenciais.
3. Upload duplicado: até a auditoria, o upload sai privado e o mesmo MP4 vai para o Telegram para postar pelo app.
   Depois da auditoria, `LOL_YT_PRIVACIDADE=public`.
4. Cron pausado: o GitHub pausa cron de repo público após 60 dias sem commit no branch padrão. O `esteira.yml` faz
   um commit vazio de keepalive se o último commit tiver mais de 45 dias.
5. Logs públicos: nenhum script imprime resposta crua do Telegram ou do Gemini.
