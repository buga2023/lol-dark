# Contas e chaves (feito uma vez, pelo dono do canal)

Cada passo termina num `gh secret set`. O valor é digitado no seu terminal e nunca vai para o chat nem para o git.

## 1. Telegram (2 min)
1. No Telegram, fale com **@BotFather** → `/newbot` → nome e usuário do bot. Ele devolve o token.
2. `gh secret set TELEGRAM_BOT_TOKEN -R buga2023/lol-dark` e cole o token.
3. Mande qualquer mensagem para o seu bot e rode:
   `curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | grep -o '"chat":{"id":[0-9-]*'`
4. `gh secret set TELEGRAM_CHAT_ID -R buga2023/lol-dark` com esse número.

## 2. Gemini (1 min)
1. https://aistudio.google.com/apikey → **Create API key**.
2. `gh secret set GEMINI_API_KEY -R buga2023/lol-dark`.

## 3. YouTube (10 min)
1. Crie o canal (pessoa física, sem logo da Riot) em youtube.com com a conta Google que vai ser a dona.
2. https://console.cloud.google.com → novo projeto `lol-dark` → **APIs e serviços** → ative **YouTube Data API v3**.
3. **Tela de consentimento OAuth**: tipo Externo, adicione o seu e-mail como usuário de teste e depois clique
   em **Publicar app** (em modo de teste o refresh token expira em 7 dias).
4. **Credenciais** → Criar ID do cliente OAuth → tipo **App para computador**. Copie ID e segredo.
5. Na sua máquina:
   ```bash
   cd ~/Projects/lol-dark
   YT_CLIENT_ID=... YT_CLIENT_SECRET=... .venv/bin/python tools/handshake/youtube_token.py
   ```
   Escolha a conta do canal no navegador (o Google avisa "app não verificado": Avançado → continuar).
6. `gh secret set YT_CLIENT_ID`, `gh secret set YT_CLIENT_SECRET`, `gh secret set YT_REFRESH_TOKEN` (todos com `-R buga2023/lol-dark`).
7. Peça a auditoria: formulário "YouTube API Services - Audit and Quota Extension". Até ela sair, todo upload por API
   fica privado; depois: `gh variable set LOL_YT_PRIVACIDADE -b public -R buga2023/lol-dark`.

## 4. Instagram e TikTok
Crie as contas pelo app. A postagem automática nas duas exige app aprovado na Meta e no TikTok (revisão de dias a
semanas). Até lá, o vídeo e a descrição chegam no Telegram todo dia, prontos para postar pelo app.

## 5. Ligar
```bash
.venv/bin/python tools/handshake/todos.py         # T1, com as variáveis exportadas
gh workflow run esteira.yml -R buga2023/lol-dark -f dry_run=true   # T5 sem publicar
gh workflow run esteira.yml -R buga2023/lol-dark                   # primeiro vídeo de verdade
```
