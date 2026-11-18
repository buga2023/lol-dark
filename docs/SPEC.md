# Canal dark de LoL — Spec, infraestrutura sem custo e plano de teste

Nov 17, 2026 · @Gustavo

## Resumo

A esteira roda inteira no GitHub Actions, em repositório público, com custo zero, e entrega um Short por dia no seu Telegram para aprovação.

| Decisão | Escolha | Motivo |
| --- | --- | --- |
| Onde roda 24h | GitHub Actions com cron | Minutos gratuitos e ilimitados em repositório público |
| Texto (pauta e roteiro) | Gemini CLI em modo headless com chave de API | Em modo headless o CLI exige chave ou credencial em cache |
| Voz | `hyperframes tts` (Kokoro, local) | Roda no próprio runner, sem serviço pago |
| Vídeo | HyperFrames, render local no runner | Só precisa de Node 22 e FFmpeg |
| Aprovação | Bot do Telegram com botões | Mantém revisão humana, exigida para monetizar |
| Publicação | Manual pelo app do YouTube até a auditoria da API | Upload por projeto não auditado fica travado como privado |
| Estado | Arquivos JSONL em um branch `state` | Sem banco de dados para manter |

**Onde entra o Gemini Ultra.** A assinatura vale no login interativo do Gemini CLI. Use o Ultra na sua máquina para escrever as composições HyperFrames e para clipes pontuais no Veo. No runner, a geração diária de texto usa uma chave do AI Studio.

**Premissas assumidas.** Shorts verticais de 25 a 45 segundos, em português, 4 a 5 por semana no início, canal em seu nome como pessoa física. Troque qualquer uma e eu ajusto a spec.

## Identidade do canal

O canal se chama **Wardado Clips** e usa a linguagem visual da Noxis, sem o nome, o @ ou o logo da Noxis nos vídeos.

| Elemento | Definição |
| --- | --- |
| Paleta | Azul-naval `#0B3D6A`, azul-noite `#051C33`, ouro `#D1A147`, papel `#EDEAE4` |
| Logo | Olho sobre uma estaca, em ouro sobre azul: a visão que o ward dá |
| Fundo | Azul-naval com ondas seigaiha discretas |
| Tipografia | Anton nos títulos, JetBrains Mono em rótulos e números, Archivo nas legendas |
| Buff e nerf | Seta e rótulo: ▲ em ouro, ▼ em papel |
| Assinatura na tela | Só "Wardado Clips" |
| Arquivos | `logo.svg`, `wardado-avatar.png` (800×800), `wardado-banner.png` (2560×1440, texto dentro da área segura) |

**Por que sem a marca Noxis.** A política da Riot só libera receita de anúncios para projeto de jogador individual, e exclui projeto que envolva empresa. Usar o estilo não liga o canal à Noxis; exibir o nome, o @noxis.labs ou o gato mascote liga. O gato ficou de fora por esse motivo; a decisão de trazê-lo como mascote é sua.

O vermelho da Noxis saiu da paleta do canal. As três variações de cada formato passam a ser `azul-ouro`, `noite-ouro` e `ouro-cheio`.

## Infraestrutura sem custo

A recomendação é GitHub Actions em repositório público: não há servidor para manter e o uso de runners padrão é gratuito e sem limite de minutos.

### Serviços usados

| Serviço | Papel | Limite gratuito | Cuidado |
| --- | --- | --- | --- |
| [GitHub Actions](https://docs.github.com/billing/managing-billing-for-your-products/managing-billing-for-github-actions) | Agendador e máquina de execução | Ilimitado em repo público com runner padrão | O código fica visível; segredos só em GitHub Secrets |
| Chave do Gemini (AI Studio) | Curadoria e roteiro | Camada gratuita, limite a medir no T1 | Cerca de 10 chamadas por dia bastam |
| [HyperFrames](https://github.com/heygen-com/hyperframes) | Voz (Kokoro) e render do MP4 | Apache-2.0, sem taxa por render | Voz em português exige `espeak-ng` no runner |
| Telegram Bot API | Preview, aprovação e alertas | Gratuito | Arquivo enviado por bot tem teto de tamanho; manter o MP4 abaixo de 50 MB |
| [YouTube Data API](https://developers.google.com/youtube/v3/docs/videos/insert) | Upload | 100 uploads por dia | Projeto não auditado sobe tudo como privado |
| Data Dragon | Artes e dados de campeões | Aberto, sem chave | Citar a Riot na descrição |

### Agendamentos

| Workflow | Frequência | Duração esperada |
| --- | --- | --- |
| `coletar.yml` | A cada 2 horas | 1 a 2 minutos |
| `esteira.yml` | Diário, 09:00 de Salvador (12:00 UTC) | 10 a 20 minutos |
| `aprovacao.yml` | A cada 30 minutos | Menos de 1 minuto |

O cron do GitHub pode atrasar alguns minutos em horário de pico, o que não afeta um canal de um vídeo por dia.

### Alternativas descartadas

| Opção | Por que não é a principal |
| --- | --- |
| [Oracle Cloud Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm) | A cota ARM caiu para 2 OCPU e 12 GB em 2026, falta capacidade em várias regiões e instâncias ociosas são recolhidas. Nossa esteira fica parada a maior parte do dia. |
| Seu PC com systemd timer | Custo zero e permite usar o login do Ultra no Gemini CLI, mas depende da máquina ligada. Fica como plano B. |
| Render na nuvem da HeyGen ou em Lambda | São pagos. |

## Spec de implementação

São 11 scripts Python atômicos em `tools/`, cada um com um POP em `architecture/`, executados nesta ordem pelo orquestrador.

| # | Script | Entrada → saída | Regras | Pronto quando |
| --- | --- | --- | --- | --- |
| 1 | `coletar.py` | Fontes → `itens.jsonl` | Fontes: notas de patch, notícias oficiais, LoL Esports, Data Dragon. Deduplica por hash da URL. Fonte fora do ar não derruba a execução. | Roda duas vezes seguidas e não duplica itens |
| 2 | `curar.py` | Itens novos → 1 pauta | Não repete campeão ou tema dos últimos 14 dias. Alterna os formatos. Dia de patch tem prioridade. | Escolhe pauta válida em 5 dias de dados simulados |
| 3 | `roteirizar.py` | Pauta e texto das fontes → `roteiro.json` | Saída validada por JSON Schema, até 2 novas tentativas. De 60 a 110 palavras. Gancho na primeira cena. Comentário próprio, sem copiar a fonte. | 10 roteiros seguidos passam no schema |
| 4 | `verificar.py` | Roteiro → aprovado ou rejeitado | Toda afirmação aponta para um `fonte_id`. Todo número do roteiro existe no texto da fonte, checado em Python. | Rejeita o roteiro de teste com número inventado |
| 5 | `narrar.py` | Cenas → um WAV por cena | Usa `hyperframes tts`. Duração da cena = áudio medido por ffprobe mais 0,3 s. | Total entre 25 e 45 s |
| 6 | `compor.py` | Roteiro, áudios e artes → MP4 | Preenche o HTML do formato com os dados. Roda `hyperframes lint` e depois `render --quality high`. | Lint sem erros e MP4 gerado |
| 7 | `qa.py` | MP4 → laudo | 1080×1920, 30 fps, faixa de áudio presente, duração igual à soma das cenas ± 0,5 s, nenhum trecho preto acima de 0,5 s, arquivo abaixo de 50 MB. | Reprova o vídeo de teste sem áudio |
| 8 | `entregar.py` | MP4 e metadados → Telegram | Envia vídeo, título, descrição, tags e fontes, com botões Aprovar, Refazer e Descartar. | Mensagem chega com os 3 botões |
| 9 | `aprovacao.py` | Cliques → novo estado | Lê `getUpdates`. Refazer devolve ao passo 3 com o seu comentário. Só aceita o seu chat ID. | Cada botão muda o estado certo |
| 10 | `publicar.py` | Aprovado → YouTube | `videos.insert` com descrição, fontes e aviso da Riot. Antes da auditoria, sobe como privado e marca `publicado_manual` quando você postar pelo app. | Vídeo aparece no canal |
| 11 | `run_pipeline.py` | Orquestra 2 a 8 | Flags `--dry-run`, `--ate <etapa>` e `--pauta <id>`. No máximo 3 tentativas por pauta. Falha gera alerta no Telegram. | Roda de ponta a ponta com um comando |

### Composições de vídeo

As composições são escritas uma vez, na sua máquina, com o Gemini CLI e as skills do HyperFrames, e ficam em `compositions/`. Na execução diária o modelo só gera o `roteiro.json`; o HTML é preenchido por código, o que mantém o render determinístico.

- `patch60`: buffs e nerfs com números animados.
- `voce-sabia`: uma curiosidade de lore ou de bastidor.
- `top5`: ranking com dados.
- `noticia`: novidade do dia.

Cada formato precisa de pelo menos 3 variações de cor, abertura e transição, sorteadas por vídeo, para o canal não ter cara de template único.

## Dados e estados

O `roteiro.json` é o payload central: tudo antes dele existe para produzi-lo e tudo depois só o consome.

```json
{
  "id": "2026-11-18-patch",
  "tipo": "noticia",
  "formato": "patch60",
  "variacao": 2,
  "titulo": "3 mudanças do patch que mexem na sua ranqueada",
  "fontes": [
    {"id": "f1", "url": "https://...", "coletado_em": "2026-11-18T09:00:00Z"}
  ],
  "cenas": [
    {
      "n": 1,
      "narracao": "texto falado da cena",
      "texto_tela": "texto curto na tela",
      "asset": "ddragon:champion/Ahri",
      "fonte_id": "f1",
      "duracao": null
    }
  ],
  "descricao": "texto + fontes + aviso da Riot",
  "tags": ["leagueoflegends", "lol"]
}
```

`duracao` nasce vazia e é preenchida pelo `narrar.py`. Cada linha de `itens.jsonl` guarda `id`, `url`, `fonte`, `titulo`, `texto_bruto`, `coletado_em` e `hash`.

### Estados da pauta

1. `pauta`: escolhida pelo curador.
2. `roteirizado`: roteiro válido no schema.
3. `verificado`: todas as afirmações com fonte.
4. `narrado`: áudios e durações prontos.
5. `renderizado`: MP4 gerado.
6. `qa_ok`: laudo aprovado.
7. `aguardando_ok`: preview enviado ao Telegram.
8. `aprovado`: você clicou em Aprovar.
9. `publicado`: no ar, com o ID do vídeo gravado.

Estados laterais: `rejeitado` (verificador), `erro` (com contador de tentativas) e `descartado` (seu clique). Uma pauta em `erro` volta ao último estado bom na execução seguinte, até 3 vezes.

## Repositório, workflows e segredos

O repositório segue a estrutura do V.L.A.E.G., com duas pastas a mais: `compositions/` e `.github/workflows/`.

```
lol-dark/
├── gemini.md              # schemas e regras (a Lei)
├── task_plan.md
├── findings.md
├── progress.md
├── .env.example
├── architecture/          # um POP por script
├── tools/                 # os 11 scripts + handshakes
│   └── handshake/
├── compositions/          # patch60, voce-sabia, top5, noticia
├── schemas/               # roteiro.schema.json
├── tests/
│   └── fixtures/          # HTML salvo, roteiros bons e ruins, MP4 defeituosos
├── .tmp/                  # intermediários, fora do git
└── .github/workflows/
    ├── coletar.yml
    ├── esteira.yml
    ├── aprovacao.yml
    └── testes.yml         # roda em todo push
```

O estado (`itens.jsonl`, `pautas.jsonl`) fica no branch `state`, que cada workflow baixa no início e atualiza no fim. Os MP4 ficam como artefatos do Actions e no Telegram, nunca no git.

### Segredos no GitHub Secrets

| Segredo | Uso |
| --- | --- |
| `GEMINI_API_KEY` | Gemini CLI em modo headless |
| `TELEGRAM_BOT_TOKEN` | Envio de preview e alertas |
| `TELEGRAM_CHAT_ID` | Único chat autorizado a aprovar |
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | Upload no canal |

### Dependências do runner

O `esteira.yml` instala Node 22, FFmpeg, `espeak-ng`, Python 3.12 e o Gemini CLI, e roda `npx hyperframes doctor` antes de qualquer render. O Chrome usado no render é baixado pelo próprio HyperFrames.

## Plano de teste da esteira

São 9 etapas em ordem, e cada uma só começa com a anterior aprovada. O primeiro vídeo aparece no T4 e a esteira rodando sozinha na nuvem aparece no T5.

| Etapa | O que prova | Como rodar | Passa quando |
| --- | --- | --- | --- |
| T0 Ambiente | A máquina renderiza | `npx hyperframes doctor` | Node 22+, FFmpeg e Chrome OK |
| T1 Conexões | Cada serviço externo responde | `python tools/handshake/todos.py` | Data Dragon e página de patch respondem 200; Gemini devolve texto; TTS gera WAV em português; Telegram entrega mensagem; YouTube lista o seu canal |
| T2 Unidade | Cada script isolado, com fixtures | `pytest tests/` | Coletor não duplica; curador não repete tema; roteiro passa no schema; verificador rejeita número inventado |
| T3 Render | Um roteiro fixo vira vídeo correto | `python tools/compor.py tests/fixtures/roteiro_ok.json` e depois `qa.py` | 1080×1920, 30 fps, com áudio, duração certa, sem tela preta |
| T4 Ponta a ponta local | A esteira inteira, sem publicar | `python tools/run_pipeline.py --dry-run` | MP4 e metadados em `.tmp/` em menos de 20 minutos |
| T5 Ponta a ponta na nuvem | O mesmo no GitHub Actions | Disparo manual do `esteira.yml` | Artefato MP4 gerado e preview recebido no Telegram |
| T6 Aprovação e upload | Botões e publicação | Clicar em Aprovar, Refazer e Descartar em 3 pautas | Estados mudam certo; o vídeo aprovado sobe como privado no canal |
| T7 Falhas | A esteira não quebra em silêncio | Simular fonte com 404, JSON inválido do Gemini, falha de TTS e render travado | Pauta fica em `erro`, alerta chega no Telegram e a execução seguinte tenta de novo |
| T8 Sete dias | Roda sozinha de verdade | Cron ligado por 7 dias | Pelo menos 6 vídeos entregues, nenhum tema repetido, nenhuma afirmação sem fonte |

### Fixtures necessárias

- 3 páginas de patch salvas em HTML, para o coletor.
- `roteiro_ok.json`, `roteiro_numero_inventado.json` e `roteiro_longo.json`.
- Um MP4 sem áudio e um com 2 segundos de tela preta, para o QA.

### O que você confere a olho no T4 e no T5

- [ ] A narração soa natural em português e pronuncia nomes de campeões.
- [ ] O texto na tela não corta nem sai da área segura do Short.
- [ ] O gancho aparece nos 2 primeiros segundos.
- [ ] As fontes na descrição batem com o que foi dito.

No Fedora, abra os MP4 com VLC ou mpv: o render sai em H.264 e o player padrão pode mostrar tela preta mesmo com o arquivo correto.

## Boas práticas de postagem

A pesquisa muda duas premissas da spec: os vídeos ficam mais curtos (25 a 45 segundos) e o canal começa com 4 a 5 Shorts por semana, não um por dia.

| Prática | Regra na esteira | Onde é aplicada |
| --- | --- | --- |
| Gancho nos primeiros 1 a 3 segundos | A cena 1 já entrega parte do fato; nada de vinheta ou saudação | Skill de roteiro e skill de vídeo |
| Duração curta retém mais | 25 a 45 s; vídeos abaixo de 30 s costumam passar de 100% de retenção por causa do loop, e os de 60 s precisam de 80 a 90% | `narrar.py` e `qa.py` |
| Sem tempo morto | Nenhum trecho acima de 2 s sem fala, movimento ou troca de texto | Skill de vídeo e `qa.py` |
| Legenda queimada | Grande, alto contraste, frase a frase, palavra-chave em cor de destaque | Skill de vídeo |
| Fecho em loop | A última cena responde ao gancho e emenda no início | Skill de roteiro |
| Consistência acima de volume | 4 a 5 por semana no início; subir para diário só com retenção estável | Cron do `esteira.yml` |
| Horário por teste | Testar 3 horários por 2 semanas e cortar o pior pelo YouTube Studio | Cron e revisão semanal |
| Título e descrição | Título com o nome do campeão ou do patch; descrição com fontes | `entregar.py` |

### Revisão semanal

Toda semana, olhe no YouTube Studio três números por vídeo: quantos assistiram em vez de deslizar, retenção média e inscritos ganhos. O formato e o tipo de gancho com melhor retenção ganham mais espaço na semana seguinte; o pior sai da rotação.

Fontes: [JoinBrands](https://joinbrands.com/blog/youtube-shorts-best-practices/), [Toptal](https://www.toptal.com/creator/post/youtube-shorts-length), [PostEverywhere](https://posteverywhere.ai/blog/youtube-shorts-strategy), [SocialPilot](https://www.socialpilot.co/youtube-marketing/how-to-get-more-views-on-youtube-shorts), [Miraflow](https://miraflow.ai/blog/how-to-get-more-views-youtube-shorts-2026), [Schedulala](https://schedulala.com/blog/youtube-shorts-engagement-get-more-views). São guias de mercado, não documentação oficial do YouTube; os números servem como ponto de partida para os seus testes.

## Regras anti-slop

Um vídeo só sai se passar por três barreiras: um lint editorial automático, o verificador de fatos e a sua aprovação. Em dia sem pauta boa, a esteira não publica nada.

| Regra | Como é checada | Quem barra |
| --- | --- | --- |
| Ângulo próprio | O roteiro tem o campo `angulo`: o que o fato muda para quem joga | Skill de roteiro; sem ângulo, devolve `sem_pauta` |
| Sem frase feita de IA | Lista de frases proibidas, comparada por código | `lint_editorial.py` |
| Fato com fonte | Cada cena tem `fonte_id`; cada número existe no texto da fonte | `verificar.py` |
| Sem repetição | Tema, estrutura de gancho e variação visual diferentes dos últimos vídeos | `curar.py` e `lint_editorial.py` |
| Visual próprio | Só motion graphics do canal e artes oficiais; nada de imagem gerada de campeões nem avatar sintético | Skill de vídeo |
| Conteúdo não copiado | Nenhuma frase igual à fonte acima de 8 palavras seguidas; nada de clipes de outros canais | `lint_editorial.py` |
| Pronúncia certa | Dicionário `assets/pronuncia.json` para nomes de campeões | `narrar.py` e sua revisão |
| Teto de volume | No máximo 1 vídeo por dia, mesmo com várias pautas | `run_pipeline.py` |
| Revisão humana | Você assiste e aprova cada vídeo | Telegram |

**Freio automático.** Se você rejeitar mais de 30% dos vídeos em uma semana, a esteira pausa e avisa. O conserto é na skill de roteiro ou na composição, não em gerar mais.

**Mudanças na spec.** Entram um 12º script, `lint_editorial.py`, entre o roteirista e o verificador, e dois campos no roteiro: `angulo` e `gancho_tipo`.

## Skills no harness do agente

O agente é o Gemini CLI rodando dentro do repositório, e ele descobre sozinho as skills que ficam em `.gemini/skills/`. São duas skills próprias do canal, já escritas, mais as oficiais do HyperFrames.

| Skill | Origem | O que faz |
| --- | --- | --- |
| `roteiro-short-lol` | Própria, entregue junto com este documento | Processo de roteiro, 5 estruturas de gancho, frases proibidas, checagem final e a saída `sem_pauta` |
| `video-short-lol` | Própria, entregue junto com este documento | Formato técnico, ritmo, área segura, legendas, variação obrigatória e checklist do rascunho |
| `hyperframes` | [HeyGen](https://github.com/heygen-com/hyperframes) | Contrato de autoria das composições HTML |
| `hyperframes-cli` | HeyGen | `init`, `lint`, `render`, `doctor` |
| `hyperframes-media` | HeyGen | Voz, transcrição, legendas e trilha |
| `hyperframes-creative` | HeyGen | Direção de arte, paletas, tipografia, ritmo |
| `faceless-explainer` | HeyGen | Fluxo pronto de vídeo sem rosto a partir de texto; serve de referência para as composições |

### Instalação

```bash
# dentro do repositório
npx skills add heygen-com/hyperframes --all
mkdir -p .gemini/skills
# copie as pastas roteiro-short-lol/ e video-short-lol/ para .gemini/skills/
gemini skills list
```

### Como a esteira usa as skills

- **Na sua máquina, com o Ultra.** Você abre o Gemini CLI no repositório e pede uma composição nova; o agente carrega `video-short-lol` e as skills do HyperFrames sozinho.
- **No runner, sem interação.** O `roteirizar.py` lê o `SKILL.md` de `roteiro-short-lol` e injeta o texto direto no prompt. Assim a regra é a mesma nos dois lugares e não depende de o agente decidir ativar a skill.
- **Loop de reparo.** Toda rejeição sua com comentário vira uma linha nova na skill correspondente, pelo mesmo commit que corrige o POP.

A validar no T1: se a sua versão do Gemini CLI já traz skills ativas por padrão ou se é preciso habilitar nas configurações, e quais vozes em português o `npx hyperframes tts --list` mostra.

Fontes: [Gemini CLI: Agent Skills](https://geminicli.com/docs/cli/skills/), [Gemini CLI: criando skills](https://geminicli.com/docs/cli/creating-skills/), [hyperframes-media](https://mcpservers.org/agent-skills/heygen-com/hyperframes-media), [faceless-explainer](https://mcpservers.org/ru/agent-skills/heygen-com/faceless-explainer).

## Canais de referência

Não achei um canal dark de Shorts de LoL em português com números confiáveis, o que indica espaço aberto. Os canais abaixo são sem rosto ou quase, têm audiência comprovada e cada um ensina uma peça do formato.

| Canal | Formato | Tamanho | O que copiar |
| --- | --- | --- | --- |
| [Necrit](https://agatasmurf.com/league-of-legends-youtube-channels/) | Lore de Runeterra narrada | 1,1 mi+ inscritos, 2 a 3 vídeos por semana | Curiosidade de lore contada como história, com opinião |
| [Vandiril](https://agatasmurf.com/league-of-legends-youtube-channels/) | Testes de bugs e interações | 1,1 mi+ inscritos, 3 a 5 vídeos por semana | Pergunta no título e resposta mostrada na tela |
| [SkinSpotlights](https://agatasmurf.com/league-of-legends-youtube-channels/) | Prévia de skins, sem narração | 1,3 mi+ inscritos | Rapidez: publica junto com cada ciclo de novidades |
| [Remus](https://analytics.wizdeo.com/en/channels/651489-Remus) | Notícias, reworks e mudanças de balanceamento | Parceiro oficial da Riot | Cobertura de patch com avatar no lugar do rosto |
| [Exil](https://vidiq.com/youtube-stats/channel/UCvzoHz_9Vym9HUJ3lNRfCcw) | Documentários longos sobre a história do jogo | 389 mil inscritos com 115 vídeos | Pautas perenes de bastidor, boas para o formato `voce-sabia` |
| [LeagueVoices](https://vidiq.com/youtube-stats/channel/UCdkonRjBLzr1Adf7Jhu1bWQ) | Falas dos campeões, sem narração | 114 mil inscritos, 97 mi de views | Falas escondidas rendem pauta e busca |
| [Zack D. Films](https://taletok.io/blog/best-faceless-youtube-channels/) | Shorts animados de curiosidades (fora de LoL) | 29 mi de inscritos | Estrutura do Short: fato estranho, explicação visual, fecho seco |

### O que copiar e o que não copiar

Copie estrutura: tipo de gancho, ritmo de corte, jeito de mostrar número, frequência e padrão de título. Não copie roteiro, narração nem imagem de nenhum deles: a regra da Riot e a política do YouTube tratam conteúdo reaproveitado como motivo para derrubar ou desmonetizar.

### Tarefa antes do T3

- [ ] Buscar no YouTube, em português, "curiosidades lol shorts" e "patch lol shorts" e anotar 3 canais brasileiros com Shorts acima de 100 mil views.
- [ ] Para cada um e para os 7 da tabela, registrar em `findings.md`: os 5 Shorts mais vistos, a primeira frase de cada e a duração.
- [ ] Usar esses 50 ganchos reais para ajustar as 5 estruturas da skill de roteiro.

Os números de inscritos vêm de páginas de terceiros com datas diferentes (2024 a 2026); confirme no próprio YouTube antes de usar como meta.

## Revisão do piloto e loop de qualidade

O piloto do patch 26.23 reprovou em 3 de 9 travas do novo `qa.py`: volume baixo, fim de áudio que apaga e quebra o loop, e vídeo parado em 14 de 19 janelas de 2 segundos.

| Medida | Piloto | Alvo | Resultado |
| --- | --- | --- | --- |
| Formato | 1080×1920, 30 fps | 1080×1920, 30 fps | Passa |
| Duração | 39,3 s | 25 a 45 s | Passa |
| Volume | -19,7 LUFS | -14 LUFS | Reprova |
| Pico | -2,9 dBTP | até -1 dBTP | Passa |
| Fim do áudio | 11,4 dB abaixo da média | até 6 dB | Reprova |
| Movimento | 14 de 19 janelas paradas | até 25% | Reprova |
| Primeiro e último quadro | 0,80 de semelhança | 0,75 ou mais | Passa |
| Bitrate de vídeo | 4,3 Mbps | 6 Mbps ou mais | Aviso |

**O que está bom.** O roteiro fecha em "e tudo isso porque" e emenda no título, o número antes e depois aparece junto com a fala, e o layout é limpo.

**O que corrigir na composição.**

- Cada cena fica cerca de 6 segundos com a arte imóvel; só a legenda muda. Adicionar zoom lento na arte, entrada animada do número e uma troca de enquadramento por cena.
- A parte de baixo da tela só tem o "26.23" vazado. Subir o tamanho da arte, do número e da legenda.
- As palavras ainda não ditas da legenda aparecem em cinza claro sobre fundo creme e quase não se leem.
- O título quebra deixando "PRO" sozinho na segunda linha.
- O piloto usa papel e vermelho; a identidade definida é azul e dourado.

O bitrate baixo é consequência do vídeo parado, não de codificação ruim: reencodar o mesmo piloto com qualidade máxima deu 2,2 Mbps. Por isso ele é aviso, e a trava real é a de movimento.

### Loop de validação

1. Renderizar em alta qualidade.
2. Masterizar com `tools/masterizar.sh`.
3. Validar com `tools/qa.py`, que devolve um laudo com o conserto de cada falha.
4. Aplicar os consertos na origem (composição, áudio ou roteiro) e repetir, no máximo 3 voltas.
5. Só vídeo aprovado segue para o seu Telegram; depois de 3 voltas reprovado, a pauta vira `erro` e o laudo vai no alerta.

A masterização já foi testada no piloto: o volume foi de -19,7 para -14,0 LUFS com pico de -1,5 dBTP.

## Voz do canal

A recomendação é o Chatterbox Multilingual com uma voz feminina fixa, clonada de uma gravação autorizada de 10 a 30 segundos, usada igual em todos os vídeos.

| Opção | Licença dos pesos | Português do Brasil | Voz própria | Uso no canal |
| --- | --- | --- | --- | --- |
| [Chatterbox Multilingual](https://www.resemble.ai/learn/models/chatterbox-multilingual) | MIT, uso comercial liberado | Sim, com versão dedicada | Sim, a partir de 10 s de referência | Principal |
| [Kokoro](https://www.bentoml.com/blog/exploring-the-world-of-open-source-text-to-speech-models) | Apache 2.0 | Sim, vozes prontas | Não | Reserva; roda em CPU |
| XTTS-v2, F5-TTS, Fish Speech | [Não comercial](https://localaimaster.com/blog/best-local-tts-models) | Sim | Sim | Não usar em canal monetizado |

**Por que voz própria.** Voz pronta de modelo é a mesma de milhares de canais e soa como slop. Uma voz clonada de uma pessoa real que autorizou vira a marca sonora do canal e não existe em nenhum outro.

**Constância.** A gravação de referência e os parâmetros ficam versionados em `assets/voz/`. Cada cena é sintetizada, transcrita e comparada com o roteiro; palavra trocada gera nova tentativa. Um dicionário de pronúncia cuida dos nomes de campeões.

**A decidir.** De quem é a voz de referência: precisa ser de alguém que autorize por escrito, e nunca de streamer, dubladora ou personagem do jogo.

**A validar no T1.** Uma página de [comparativo de licenças](https://www.cartesia.ai/learn/open-source-tts) diz que o Chatterbox deixou de ser mantido em agosto de 2026, enquanto o repositório lista uma versão V3 com pacote para português do Brasil; confirme o estado atual. Meça também quanto tempo ele leva em CPU no runner do GitHub: é um modelo de 500 milhões de parâmetros e pode exigir gerar o áudio na sua máquina.

## Banco de pautas

O arquivo `data/pautas_evergreen.json` traz 62 pautas em 10 séries, cada uma escrita como pergunta. O curador só transforma uma pergunta em vídeo se o coletor achar fonte oficial que a responda.

| Série | Formato | Ritmo | Pautas | Exemplo |
| --- | --- | --- | --- | --- |
| Você sabia | `voce-sabia` | Perene | 15 | Que campeões foram anunciados e nunca lançados? |
| Fala escondida | `voce-sabia` | Perene | 6 | Que falas só tocam ao encontrar um rival do lore? |
| De onde vem | `voce-sabia` | Perene | 7 | De onde vem a palavra "gank"? |
| O jogo não te conta | `top5` | Perene, revisar por temporada | 7 | Como a recompensa por abate cresce e quando zera? |
| Itens e coisas removidas | `voce-sabia` | Perene | 5 | Que itens lendários foram removidos e por quê? |
| Recordes | `voce-sabia` | Perene | 5 | Qual foi a partida profissional mais longa? |
| Número do patch | `patch60` | A cada patch | 4 | Qual nerf parece pequeno mas mata um combo? |
| Ganhou e perdeu | `patch60` | A cada patch | 3 | Quem ganhou e quem perdeu o patch em cada rota? |
| Dados da semana | `top5` | Semanal | 4 | Que escolha quase ninguém joga mas vence acima da média? |
| Notícia | `noticia` | Sob demanda | 6 | Que campeão novo foi revelado e o que se sabe do kit? |

**Grade semanal sugerida para 5 vídeos.** Dois de patch ou notícia, dois perenes de séries diferentes e um de dados. Em semana sem patch, entram três perenes.

**Reposição.** Quando restarem menos de 15 pautas abertas, o curador propõe 20 novas a partir do que o coletor trouxe e você aprova a lista de uma vez, no Telegram.

## Modo autônomo: o que falta para rodar sem você

Dá para chegar a zero toque no dia a dia, mas não a zero toque desde o primeiro dia: seis tarefas só você pode fazer, uma vez, e uma delas depende de aprovação do YouTube.

### Só você pode fazer, uma vez

- [ ] Criar o canal, o repositório público e o bot do Telegram.
- [ ] Criar o projeto no Google Cloud, ativar a YouTube Data API e autorizar o canal (gera o refresh token).
- [ ] Pedir a auditoria da API do YouTube. Sem ela, todo upload automático fica privado e não pode ser aberto depois.
- [ ] Gerar a chave do Gemini no AI Studio e gravar os 6 segredos no GitHub.
- [ ] Gravar ou conseguir a voz de referência, com autorização por escrito.
- [ ] Aprovar as composições dos 4 formatos e os 5 primeiros vídeos, para calibrar as travas.

### O agente faz sozinho, em ordem

1. Coletar as fontes a cada 2 horas e gravar em `itens.jsonl`.
2. Escolher a pauta do dia: patch ou notícia se houver, senão a próxima perene da grade.
3. Escrever o roteiro com a skill `roteiro-short-lol`.
4. Passar no `lint_editorial.py` e no `verificar.py`. Reprovou duas vezes, troca de pauta.
5. Gerar a voz, transcrever e conferir com o roteiro.
6. Montar e renderizar com a skill `video-short-lol`.
7. Masterizar e rodar o `qa.py`, até 3 voltas.
8. Publicar pela API com título, descrição, fontes e aviso da Riot.
9. Registrar o resultado e mandar um resumo no Telegram.
10. Uma vez por semana, ler os números do canal e ajustar a grade.

### Quatro travas substituem a sua aprovação

| Trava | O que barra |
| --- | --- |
| `verificar.py` | Número ou fato sem fonte |
| `lint_editorial.py` | Frase feita, repetição de tema ou de gancho, cópia da fonte |
| `qa.py` | Vídeo parado, áudio baixo, loop quebrado |
| Juiz editorial | Um segundo modelo dá nota de 1 a 5 ao roteiro contra a skill; abaixo de 4 não publica |

Se qualquer trava reprovar, o dia fica sem vídeo e você recebe o laudo. Publicar nada é o comportamento certo.

### O que você ainda faz

Dez minutos por semana: assistir aos vídeos publicados, apagar o que não gostar e responder ao resumo com o que mudar. Cada correção vira uma linha nova na skill.

**Risco que fica.** Sem revisão humana antes de publicar, um erro chega ao público antes de você ver, e a política de conteúdo inautêntico do YouTube pesa justamente contra canal sem direção humana. A recomendação é manter a aprovação no Telegram nos primeiros 20 vídeos e só então ligar o modo autônomo.

## Plano de produção com o Claude

O Claude opera o canal com quatro skills, e o caminho até a publicação automática tem cinco fases, cada uma com um portão que só abre com evidência.

| Skill | Papel |
| --- | --- |
| `wardado-canal` | Manual de operação: a esteira, o padrão de qualidade, publicação e quando parar |
| `roteiro-short-lol` | Como escrever o roteiro |
| `edicao-wardado` | Como o vídeo se parece e se move |
| `video-short-lol` | Como montar, renderizar, masterizar e validar |

| Fase | O que acontece | Portão para a próxima |
| --- | --- | --- |
| 1. Exemplos | O Claude gera 3 vídeos, um por formato, sem publicar | Os 3 passam no `qa.py` e na revisão de quadros e roteiro |
| 2. Calibração | Correções viram regras nas skills; mais 2 vídeos | 2 vídeos seguidos aprovados sem correção sua |
| 3. Canal no ar | Você posta à mão os 5 primeiros; auditoria da API pedida | Voz definitiva gravada e auditoria aprovada |
| 4. Modo aprovação | Esteira agendada, 4 a 5 por semana, você aprova no Telegram | 20 vídeos publicados, menos de 2 rejeições nos últimos 10 |
| 5. Modo autônomo | Publicação direta, revisão semanal sua | Volta à fase 4 se a rejeição semanal passar de 30% |

O prompt da fase 1 está na conversa. Os vídeos de exemplo usam a voz reserva enquanto a voz definitiva não existe.

## Arquitetura revisada: Claude orquestra, Antigravity executa

A esteira passa a rodar na sua máquina, com o Orca coordenando o Claude Code e o Antigravity CLI, e isso substitui o Gemini CLI e o GitHub Actions da primeira versão desta spec.

**Correção da spec original.** O [Gemini CLI foi encerrado para assinantes Pro e Ultra em 18 de junho de 2026](https://dev.to/arindam_1729/antigravity-cli-a-hands-on-guide-to-googles-terminal-coding-agent-5bc7) e substituído pelo Antigravity CLI (`agy`). Onde este documento diz "Gemini CLI", leia `agy`; a pasta `.gemini/skills` precisa ser trocada pela pasta de skills que o Antigravity lê.

| Papel | Agente | O que faz |
| --- | --- | --- |
| Orquestrador e fiscal | Claude Code | Pauta, fontes, verificação, nota editorial, `qa.py`, decisão de publicar |
| Executor de geração | Antigravity (`agy`) com o Ultra | Rascunho de roteiro, composições HyperFrames, imagens de fundo |
| Coordenação | [Orca](https://github.com/stablyai/orca) | Um worktree por agente, acompanhamento das tarefas, CLI próprio |

**O que isso resolve.** O [modo headless do `agy` usa o login em cache](https://antigravity.google/docs/cli/headless/), então a cota do Ultra vale sem chave de API. E o vídeo passa a ser gerado por um modelo e fiscalizado por outro, o que pega mais erro do que um modelo revisando a si mesmo.

**O que isso custa.** O Orca é um aplicativo local, então a esteira só roda com a sua máquina ligada. Em CI sem login o `agy` sai com erro de autenticação, o que tira o GitHub Actions do caminho principal.

| A validar | Por quê |
| --- | --- |
| Permissões no modo headless | Um [teste independente](https://www.testmuai.com/blog/google-antigravity-review/) viu o `agy -p` negar em silêncio o que não estava pré-aprovado e reportar sucesso sem saída |
| Agentes remotos do Antigravity | A [documentação](https://antigravity.google/docs/features/) descreve sessões em ambiente gerenciado pelo Google para assinantes Pro e Ultra, que seguem rodando com a máquina desligada; pode ser o caminho para rodar 24h |
| Geração de imagem e vídeo pelo `agy` | Há uma ferramenta de imagem embutida; não confirmei se o Veo é acessível pelo CLI ou só pelo Flow |
| Limite semanal do Ultra | Não medi quantos vídeos por semana a cota aguenta |

## Riscos, pendências e ordem de execução

O maior risco é de plataforma, não técnico: a auditoria da API do YouTube e a política de conteúdo inautêntico decidem se o canal publica sozinho e se monetiza.

| Risco ou pendência | Efeito | Tratamento |
| --- | --- | --- |
| Projeto da API do YouTube não auditado | Upload fica travado como privado e não pode ser aberto depois | Pedir a auditoria na primeira semana; até lá, postar pelo app a partir do Telegram |
| Política de conteúdo inautêntico | Canal com cara de produção em massa perde monetização | Aprovação humana, 4 formatos com variações, comentário próprio, 1 vídeo por dia |
| Regras da Riot | Canal de empresa ou com logo da Riot fica fora da permissão | Canal em pessoa física, sem logos, com o aviso padrão na descrição |
| Limite da chave gratuita do Gemini | Roteiro não é gerado no dia | Medir no T1; plano B é rodar a esteira no seu PC com o login do Ultra |
| Voz Kokoro em português | Narração pode soar artificial | Avaliar no T1; plano B é o TTS do Gemini |
| Token do YouTube expirando | Upload para de funcionar após alguns dias | Confirmar no T1 se o app OAuth em modo de teste expira o token; se sim, publicar o app |
| Workflows agendados pausados | O GitHub pode pausar cron de repo sem atividade | Os commits diários no branch `state` mantêm o repo ativo; confirmar no T8 |
| Mudança no HTML do site da Riot | Coletor para de achar patches | Teste de fixture no T2 e alerta quando a coleta volta vazia |

### Ordem de execução

1. Criar o repositório, os 4 arquivos de memória e o schema do roteiro.
2. Criar bot do Telegram, chave do Gemini e credenciais OAuth do YouTube; pedir a auditoria da API.
3. Escrever os handshakes e passar no T0 e no T1.
4. Escrever a composição `patch60` e passar no T3.
5. Implementar os scripts 1 a 7 e passar no T2 e no T4.
6. Subir os workflows e passar no T5 e no T6.
7. Passar no T7, ligar o cron e rodar o T8.
8. Adicionar os outros 3 formatos.

### Fontes

- [GitHub: cobrança do Actions](https://docs.github.com/billing/managing-billing-for-your-products/managing-billing-for-github-actions)
- [Oracle: recursos Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm)
- [InfoQ: corte da cota Ampere A1](https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/)
- [YouTube Data API: videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert)
- [Gemini CLI: autenticação](https://geminicli.com/docs/get-started/authentication)
- [HyperFrames no Linux](https://computingforgeeks.com/install-hyperframes-linux/)
- [Riot: Legal Jibber Jabber](https://www.riotgames.com/en/legal)
- [TechCrunch: política de conteúdo inautêntico do YouTube](https://techcrunch.com/2026/07/20/youtube-clarifies-policies-around-ai-slop-and-upsetting-videos/)
