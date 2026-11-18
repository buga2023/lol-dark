---
name: video-short-lol
description: Monta e renderiza o Short vertical do canal de LoL em HyperFrames a partir de um roteiro.json verificado e dos áudios de narração. Use sempre que for criar ou alterar uma composição em compositions/ ou renderizar um vídeo do canal.
---

# Vídeo de Short de LoL

O vídeo é motion graphics próprio sobre dados e artes oficiais. O objetivo é retenção: algo muda na tela o tempo todo, e o número ou nome que importa está sempre legível em um celular.

Antes de escrever qualquer HTML de composição, leia a skill `hyperframes` (contrato de autoria) e, para áudio e legendas, a `hyperframes-media`. Esta skill define as regras do canal; aquelas definem como o framework funciona. Em conflito sobre sintaxe, vale a do HyperFrames.

## Formato técnico

- 1080×1920, 30 fps, MP4.
- Duração total = soma das durações das cenas, de 25 a 45 segundos.
- Imagem: render com `--quality high`; nunca publicar o rascunho.
- Áudio final: 48 kHz, AAC 256 kbps, volume integrado de -14 LUFS, pico de até -1,5 dBTP, sem fade no fim.

## Voz do canal

A mesma voz feminina suave narra todos os vídeos. Ela é a identidade sonora do canal: não troque de voz, de motor nem de instrução de estilo entre vídeos.

- **Motor**: Gemini 3.8 Flash TTS pela API do Gemini, em português do Brasil. Roda na nuvem e não ocupa disco. Antes de implementar, leia a documentação oficial de geração de fala da API do Gemini para pegar o identificador do modelo e os parâmetros; não adivinhe.
- **Voz**: uma só, registrada em `assets/voz/voz.json`: o nome da voz pronta escolhida pelo dono, ou a descrição da voz desenhada, mais a instrução de estilo.
- **Instrução de estilo**, enviada igual em toda geração: "Português do Brasil. Voz feminina jovem adulta, suave e próxima, como uma amiga que joga explicando no Discord. Ritmo natural, com pausas curtas e respiração. Sem tom de locutora, de propaganda ou de telejornal. Ênfase leve nos números."
- **Consentimento**: voz pronta do provedor e voz criada a partir de descrição em texto não são clone de ninguém; valem as regras de licença do provedor. Clonar a voz de uma pessoa real só com autorização dela por escrito, e nunca de streamer, dubladora ou personagem do jogo.
- **Reserva**: Kokoro (`pf_dora`) via `npx hyperframes tts`, só para rascunho. Vídeo narrado com a voz reserva não é publicado: entregue marcado como rascunho e avise o dono.
- **Geração**: um WAV por cena. Depois de gerar, transcreva o WAV e compare com o texto da cena; se alguma palavra faltar, sobrar ou mudar, gere de novo (até 3 vezes).
- **Pronúncia**: nomes de campeões e termos em inglês saem de `assets/voz/pronuncia.json`, que troca a grafia pela forma fonética antes da síntese.
- **Não use** XTTS-v2, F5-TTS, Fish Speech nem o plano gratuito da ElevenLabs: as licenças não cobrem canal monetizado.
- **Trilha**: opcional, sempre a mesma família de trilhas, entra em loop até o último quadro e abaixa sozinha quando a voz fala.

## Identidade visual: Wardado Clips

O canal é azul e dourado, na linguagem visual da Noxis (paleta, tipografia, ondas seigaiha), com logo próprio: um olho sobre uma estaca, em ouro. O nome, o @ e o logo da Noxis não aparecem em nenhum quadro. A assinatura na tela é só "Wardado Clips".

**Paleta**

- Azul-naval `#0B3D6A`: fundo principal.
- Azul-noite `#051C33`: vinheta, caixas e fundo de legenda.
- Ouro `#D1A147`: títulos, palavra-chave da legenda, números, logo.
- Papel `#EDEAE4`: texto corrido e segundo destaque.

Nenhuma outra cor entra, fora as das artes oficiais dos campeões. Buff e nerf se distinguem por seta e rótulo (▲ em ouro, ▼ em papel), nunca só pela cor.

**Tipografia**

- Anton nos títulos e números de destaque.
- JetBrains Mono em rótulos, valores de patch e créditos.
- Archivo nas legendas.

**Logo**

- Arquivos em `assets/marca/`: `logo.svg`, `wardado-avatar.png`, `wardado-banner.png`.
- No vídeo, o logo aparece pequeno em um canto durante todo o Short e nunca ocupa o primeiro quadro como vinheta.

**Variações**

1. `azul-ouro`: fundo azul-naval com ondas seigaiha, destaque em ouro. É o padrão.
2. `noite-ouro`: fundo azul-noite liso, caixas em azul-naval, destaque em ouro.
3. `ouro-cheio`: abertura com faixa dourada chapada e texto azul-noite, depois volta ao azul. No máximo 1 a cada 3 vídeos.

## Processo

1. Leia o `roteiro.json` e confira que todas as cenas têm `duracao` preenchida.
2. Abra a composição do `formato` em `compositions/<formato>/` e aplique a `variacao` indicada (paleta, abertura, transição).
3. Baixe os assets de cada cena para `.tmp/assets/`. Só Data Dragon e arquivos de `assets/` do repositório.
4. Gere as legendas a partir da transcrição do próprio áudio (`npx hyperframes transcribe`), para o tempo de cada palavra bater com a voz.
5. Rode `npx hyperframes lint`. Corrija todo erro antes de renderizar.
6. Renderize um rascunho com `npx hyperframes render --quality draft` e confira o checklist abaixo.
7. Renderize com `npx hyperframes render --quality high --output .tmp/<id>-bruto.mp4`.
8. Masterize com `tools/masterizar.sh .tmp/<id>-bruto.mp4 .tmp/<id>.mp4 [trilha.wav]`.
9. Valide com `python tools/qa.py .tmp/<id>.mp4 --json .tmp/<id>-laudo.json` e siga o loop de validação.

## Loop de validação

Nenhum vídeo vai para aprovação humana sem `APROVADO` no `qa.py`.

1. Rode o `qa.py`. Se aprovou e não há avisos, encerre.
2. Para cada trava reprovada, aplique o conserto que o laudo indica, na origem: composição, áudio ou roteiro. Nunca edite o MP4 para passar na trava.
3. Renderize, masterize e valide de novo.
4. No máximo 3 voltas. Se ainda reprovar, pare, marque a pauta como `erro` e envie o laudo no alerta.
5. Avisos não bloqueiam, mas cada um precisa de uma linha no laudo dizendo se foi corrigido ou por que ficou.

Consertos por trava:

- `movimento`: nas janelas listadas, adicione zoom lento na arte (4 a 6% ao longo da cena), entrada animada do número e pelo menos uma troca de enquadramento por cena. Legenda trocando de palavra não conta como movimento.
- `loop_audio`: tire o fade final; a última palavra termina a no máximo 0,2 s do corte e a trilha segue até o último quadro.
- `loop_visual`: o último quadro repete o layout do primeiro.
- `volume` e `pico`: rode a masterização de novo; se a voz veio baixa da síntese, não compense com ganho acima de 6 dB, gere de novo.
- `duracao`: devolva ao roteiro; não acelere a voz.
- `ocupacao` (aviso): aumente arte, número e legenda até ocupar a área segura inteira.

## Regras visuais

- **Primeiro quadro**: já mostra o assunto (arte do campeão ou o número) e o `texto_tela` da cena 1. Nada de vinheta, logo ou tela de título antes.
- **Ritmo**: algum elemento muda a cada 2 segundos no máximo: corte, entrada de texto, zoom, troca de número. Nunca mais de 2 segundos de tela parada ou de silêncio.
- **Área segura**: nenhum texto nos 15% do topo, nos 25% de baixo ou nos 12% da direita, onde a interface do Shorts cobre o vídeo. Ajuste estes valores se o teste no celular mostrar corte.
- **Legendas**: queimadas no vídeo, grandes, alto contraste, de 2 a 4 palavras por vez, sincronizadas com a fala. A palavra-chave da frase ganha a cor de destaque da variação.
- **Números**: todo número falado aparece na tela no momento em que é dito, com antes e depois quando for mudança de patch.
- **Tipografia**: no máximo 2 famílias por vídeo. Corpo mínimo de 64 px para legenda e 96 px para número de destaque.
- **Fecho**: o último quadro combina visualmente com o primeiro, para o loop não ter salto.

## Variação obrigatória

Cada formato tem pelo menos 3 variações. Nunca use a mesma combinação de formato e variação do vídeo anterior. Varie também a entrada da cena 1 (zoom, corte seco, texto digitado).

## O que não entra

- Logos e marcas da Riot.
- Trechos de transmissão de campeonato ou de vídeo de outro criador.
- Imagem gerada por IA de campeões ou de pessoas.
- Avatar ou apresentador sintético.
- Texto na tela que não esteja no `roteiro.json`.

## Checklist do rascunho

- O primeiro quadro, sozinho, diz do que é o vídeo?
- Todas as legendas cabem na área segura e batem com a voz?
- Algum trecho com mais de 2 segundos sem mudança?
- Os números na tela são os mesmos do roteiro?
- A voz pronuncia certo os nomes de campeões? Se não, corrija a grafia fonética em `assets/voz/pronuncia.json` e gere o áudio de novo.
- A variação é diferente da do vídeo anterior?
