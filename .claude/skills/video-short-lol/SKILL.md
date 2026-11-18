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
- Áudio: um WAV por cena, gerado por `npx hyperframes tts`, mais trilha de fundo opcional com volume bem abaixo da voz.

## Processo

1. Leia o `roteiro.json` e confira que todas as cenas têm `duracao` preenchida.
2. Abra a composição do `formato` em `compositions/<formato>/` e aplique a `variacao` indicada (paleta, abertura, transição).
3. Baixe os assets de cada cena para `.tmp/assets/`. Só Data Dragon e arquivos de `assets/` do repositório.
4. Gere as legendas a partir da transcrição do próprio áudio (`npx hyperframes transcribe`), para o tempo de cada palavra bater com a voz.
5. Rode `npx hyperframes lint`. Corrija todo erro antes de renderizar.
6. Renderize um rascunho com `npx hyperframes render --quality draft` e confira o checklist abaixo.
7. Renderize o final com `npx hyperframes render --quality high --output .tmp/<id>.mp4`.

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
- A voz pronuncia certo os nomes de campeões? Se não, corrija a grafia fonética em `assets/pronuncia.json` e gere o áudio de novo.
- A variação é diferente da do vídeo anterior?
