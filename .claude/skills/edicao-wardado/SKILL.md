---
name: edicao-wardado
description: Guia de edição do Wardado Clips. Define layout, tipografia, cor, movimento, cortes, legendas e som para que todo Short tenha a mesma estética. Use sempre que for criar ou ajustar uma composição, decidir como uma cena se move, escolher transição, estilizar legenda ou adicionar som em um vídeo do canal.
---

# Edição do Wardado Clips

Esta skill decide como o vídeo se parece e se move. A `video-short-lol` cuida do processo (render, masterização, validação); a `hyperframes` cuida da sintaxe. Aqui ficam as decisões de editor.

O canal tem uma cara: azul-naval, ouro, tipografia pesada e movimento curto e seco. A meta é que alguém reconheça um vídeo do Wardado em meio segundo, sem ver o nome. Por isso algumas coisas nunca mudam e outras variam de propósito. Quando esta skill não cobrir um caso, escolha a opção mais simples e mais legível no celular.

## O que nunca muda e o que varia

Fixo em todo vídeo: paleta, as três fontes, o estilo da legenda, o logo no canto, a faixa de contexto no topo, a biblioteca de sons e a voz.

Varia entre vídeos: a variação visual (`azul-ouro`, `noite-ouro`, `ouro-cheio`), a entrada da primeira cena, os enquadramentos da arte e a ordem dos blocos dentro do palco.

Constância vem do que é fixo; o que varia impede o canal de parecer um template.

## Layout em 1080×1920

A interface do Shorts cobre o topo, a base e a lateral direita. Tudo que precisa ser lido fica entre y=288 e y=1440 e entre x=60 e x=950.

| Zona | Posição (y) | Conteúdo |
| --- | --- | --- |
| Contexto | 288 a 360 | Logo pequeno à esquerda, rótulo em mono ("PATCH 26.23") e contador de cena à direita |
| Palco | 380 a 1000 | Arte do campeão ou gameplay; é onde o movimento acontece |
| Dado | 1020 a 1240 | Título da cena e o número que importa |
| Legenda | 1260 a 1420 | Legenda da fala, sempre no mesmo lugar |

Abaixo de 1440 só entra fundo: ondas seigaiha ou o número do patch vazado, com no máximo 12% de opacidade. Nada ali pode ser necessário para entender o vídeo.

O palco ocupa a largura útil inteira. Arte pequena no meio de um quadro vazio foi o principal defeito do piloto.

## Tipografia

- **Anton**: títulos (120 a 150 px) e número de destaque (200 a 260 px). Sempre em maiúsculas.
- **JetBrains Mono**: rótulos e valores secundários (30 a 34 px, maiúsculas, espaçamento de 0,08em).
- **Archivo** peso 800: legendas (68 a 76 px).

Título tem no máximo duas linhas e nunca deixa uma palavra sozinha na última linha: reescreva o título ou reduza o corpo até 110 px. Se ainda não couber, o problema é do roteiro.

## Cor

Proporção por quadro: cerca de 70% azul, 20% papel, 10% ouro.

- Azul-naval `#0B3D6A` e azul-noite `#051C33` são fundo e caixas.
- Papel `#EDEAE4` é texto.
- Ouro `#D1A147` marca uma coisa só por vez: o número novo, a palavra falada agora ou o veredito. Se tudo é dourado, nada é.

A arte dos campeões mantém as cores originais. Aplique apenas uma moldura de 3 px em ouro e um degradê azul-noite na base para fundir com o fundo. Não use filtro, dessaturação ou duotone.

Buff e nerf: ▲ em ouro e ▼ em papel, sempre com o valor antigo riscado ao lado. Nunca dependa só da cor.

## Movimento

O estilo é curto e seco, com cara de vinheta de esporte. Nada quica, nada balança.

- Entradas: 0,25 a 0,35 s, desacelerando no fim (`power3.out`).
- Saídas: 0,15 a 0,20 s, ou corte seco.
- Proibido: `bounce`, `elastic`, rotação decorativa, tremor de câmera, zoom com desfoque.
- Arte no palco: zoom lento contínuo de 100% para 106% durante a cena, com leve deslocamento em direção ao rosto do campeão. A arte nunca fica parada.
- Fundo: as ondas seigaiha deslizam devagar o vídeo inteiro.

Algo muda na tela a cada 1,5 a 2 segundos. Conta como mudança: corte, reenquadramento da arte, entrada de número ou título. Troca de palavra na legenda não conta.

## Anatomia de uma cena

Cada cena dura de 3 a 6 segundos e segue esta ordem:

1. **0,0 s**: corte seco para a nova arte, já em zoom, com o título entrando de baixo.
2. **Quando o valor antigo é falado**: ele aparece em papel, no tamanho de destaque.
3. **Quando o valor novo é falado**: o antigo encolhe e é riscado, o novo entra em ouro com um pulso de escala de 112% para 100% e um som de marcação.
4. **Na metade da cena**: reenquadramento da arte (corte para um detalhe ou salto de zoom para 115%).
5. **Últimos 0,2 s**: o título sai; a arte é cortada pela cena seguinte.

Cena com mais de 6 segundos é dividida em duas.

## Primeiro e último quadro

O primeiro quadro já tem arte, título e a primeira palavra da legenda. Não existe vinheta, logo animado nem tela de abertura: a pessoa decide ficar ou sair antes de qualquer introdução terminar.

O último quadro repete o layout do primeiro (mesma arte ou mesma montagem, mesmo lugar do título) para o loop não ter salto. A fala termina a no máximo 0,2 s do corte, sem fade.

## Transições

- Padrão: corte seco.
- Troca de bloco (por exemplo, das mudanças para o veredito): faixa dourada atravessando a tela em 0,2 s.
- No máximo dois tipos de transição por vídeo. Sem glitch, sem cubo, sem página virando.

## Legendas

- De 2 a 4 palavras por vez, centralizadas na zona de legenda, sobre caixa azul-noite a 85% de opacidade com cantos de 12 px.
- A palavra sendo falada fica em ouro; as outras do grupo ficam em papel a 100%. Nunca mostre em cinza ou transparente uma palavra que ainda não foi dita: no piloto isso ficou ilegível.
- O tempo vem da transcrição do próprio áudio, palavra por palavra.
- A legenda não repete o número de destaque em tamanho grande; o número mora na zona de dado.

## Gameplay no palco

Quando existir gameplay próprio em `assets/broll/`, ele substitui a arte parada na cena correspondente. Regras:

- Só gravação feita pelo dono do canal. Nada de transmissão de campeonato nem vídeo de outro criador.
- Recorte central em 9:16 ou enquadrado no palco com moldura dourada; nunca esticado.
- Um círculo ou seta em ouro aponta o que a fala descreve, por no máximo 1,5 s.
- O som do jogo fica mudo ou 20 dB abaixo da voz.

## Som

A voz é o centro. Todo o resto existe para dar ritmo sem competir com ela.

- Biblioteca fixa em `assets/sfx/`, com no máximo 6 sons: corte, entrada de título, marcação de número, faixa de transição, veredito e fecho. Os mesmos sons em todos os vídeos são parte da identidade.
- Efeitos ficam de 8 a 10 dB abaixo da voz e nunca cobrem uma sílaba: posicione no espaço entre palavras.
- Trilha opcional, sempre da mesma família, 18 dB abaixo da voz, baixando sozinha quando a voz fala e seguindo até o último quadro.
- O vídeo começa com som no primeiro quadro: efeito de corte e voz já entrando. Sem silêncio de abertura.

## O que denuncia vídeo genérico

Evite tudo isto, mesmo que pareça dar movimento:

- Emoji na tela.
- Legenda pulando ou girando a cada palavra.
- Barra de progresso colorida.
- Imagem gerada de campeão ou cenário.
- Arte parada por mais de 2 segundos.
- Três ou mais cores de destaque.
- Texto que ocupa a tela inteira lendo a narração.

## Checagem do editor

Antes de mandar para o `qa.py`, assista ao rascunho no tamanho de um celular e confirme:

- Sem som, dá para entender o assunto e o número principal?
- Pausando em qualquer ponto, o quadro parece do Wardado (azul, ouro, Anton, legenda no lugar)?
- Em algum momento passam 2 segundos sem mudança no palco ou no dado?
- O ouro está em um único elemento por vez?
- Algum título ficou com palavra sozinha na segunda linha?
- O último quadro emenda no primeiro, na imagem e no som?
