# Manual de produção — Wardado Clips

Para o agente que vai produzir qualquer uma das pautas de `data/pautas_evergreen.json`. Leia junto com as skills `wardado-canal` (ordem e padrão de qualidade), `roteiro-short-lol`, `edicao-wardado` e `video-short-lol`. Em conflito, vale a regra mais restritiva.

## Passo a passo (igual para toda pauta)

1. **Abra a pauta**: `id`, `serie`, `formato`, `pergunta`. Ache a série na tabela abaixo.
2. **Pesquise** com `tools/pesquisar.py <id>`: só nos domínios da coluna *Onde buscar*. Guarde URL e trecho literal. Sem trecho conferido: marque `sem_fonte` e passe para a próxima. Nunca responda de memória.
3. **Escreva o `angulo`** em uma frase antes de qualquer cena: o que isso muda para quem joga, ou por que surpreende. Sem ângulo: `sem_pauta`.
4. **Monte as cenas** na ordem da coluna *Cenas* (5 a 6 cenas, 60 a 110 palavras, frase de até 14 palavras). Use o modelo da série em `data/modelos/<serie>.json`: troque os campos entre colchetes por fatos da fonte.
5. **Gancho**: use a estrutura da coluna *Gancho* se ela não apareceu nos últimos 3 vídeos; senão, outra das 5 da skill de roteiro. A cena 1 já entrega um pedaço do fato.
6. **Texto de tela**: até 6 palavras; em cena com antes/depois, até 22 caracteres. Mostra o número ou o nome, não repete a fala.
7. **Assets**: `ddragon:champion/<Chave>` só para campeão citado na fonte; senão `ilustracao:champion/<Chave>` e nada é afirmado sobre ele. Cena 1 e última: `nenhum` (palco de gancho e fecho).
8. **Cheque sozinho** antes de mandar: `tools/verificar.py` (números), `lint_editorial` (frases proibidas, cópia de 8+ palavras), contagem de palavras.
9. **Crítico** (`tools/critico.py`): nota ≥ 80. **Nota editorial**: ≥ 4 em gancho, ângulo, clareza e fecho. Reprovou: reescreva só o ponto apontado. Duas voltas sem passar: troque de pauta.
10. **Voz**: a do `assets/voz/voz.json`. Transcreva e compare; palavra trocada, gere de novo. Nome de campeão errado: corrija em `assets/voz/pronuncia.json`.
11. **Vídeo**: `tools/compor.py` → `tools/masterizar.sh` → `tools/qa.py`, até 3 voltas, consertando na origem.
12. **Revisor independente** (`tools/revisar.py`): veredito binário. Reprovado: os pontos viram instrução da próxima tentativa.
13. **Entrega**: MP4, `roteiro.json`, `fontes.json`, `laudo.json`, `publicacao.json` (`tools/metadados.py`). Registre no vault (`tools/registrar_vault.py`).

## Receita por série

| Série | Onde buscar | Gancho | Cenas | Palco | Armadilha |
| --- | --- | --- | --- | --- | --- |
| `voce-sabia` | Universo de LoL, blog de dev da Riot, wiki oficial | pergunta com aposta ou detalhe escondido | 1 gancho com metade da resposta · 2 o fato com data ou nome · 3 o porquê · 4 o que sobrou disso no jogo hoje · 5 fecho que devolve a pergunta | arte do campeão ou da região citada; sem campeão na fonte, `ilustracao:` | contar de memória; lista de 5 curiosidades soltas em vez de uma história |
| `fala-escondida` | wiki oficial (página de áudio do campeão), Universo | detalhe escondido | 1 a situação exata em que a fala toca · 2 a fala (texto literal da fonte) · 3 por que ela existe (relação no lore) · 4 como ouvir na sua partida · 5 fecho | clipe da habilidade ou arte dos dois campeões envolvidos | inventar a fala ou traduzir livremente: use a grafia da fonte e diga o idioma |
| `de-onde-vem` | wiki oficial (página do termo), blog da Riot; se a origem for de outro jogo, a fonte precisa dizer | pergunta com aposta | 1 o termo em uso · 2 de onde veio (jogo, ano, pessoa) · 3 como mudou de sentido · 4 o nome oficial hoje, se houver · 5 fecho | `ilustracao:` de um campeão que representa a ação (ex.: caçador para gank) | etimologia popular sem fonte: se a fonte não afirmar, devolva sem_pauta |
| `o-jogo-nao-te-conta` | wiki oficial (mecânica), notas de patch que mudaram a regra | consequência primeiro | 1 o erro que todo mundo comete · 2 a regra com o número · 3 exemplo em lane · 4 a exceção · 5 o que fazer diferente amanhã | gameplay da situação; número grande na zona de dado | regra de temporada antiga: confira a data da página e diga a versão |
| `itens-e-coisas-removidas` | notas de patch da remoção, blog de dev, wiki oficial (histórico) | contradição (era amado e saiu) | 1 o que era · 2 o que fazia (número) · 3 por que a Riot tirou (motivo declarado) · 4 o que herdou o efeito · 5 fecho | arte de quem usava o item; valor antigo riscado | dizer 'a Riot tirou porque era forte' sem a frase da Riot |
| `recordes` | lolesports.com, Leaguepedia (lol.fandom.com), páginas oficiais de campeonato | número na cara | 1 o recorde com o número · 2 quem, quando, torneio · 3 o contexto (por que foi possível) · 4 quem chegou perto · 5 fecho | arte do campeão jogado; nomes de jogador só em texto | usar trecho de transmissão; recorde desatualizado: diga 'até <data da fonte>' |
| `numero-do-patch` | nota oficial do patch mais recente | número na cara | 1 o número novo e o veredito · 2 antes → depois · 3 a consequência em lane · 4 quem se beneficia mais · 5 fecho em loop | clipe da habilidade citada; antes riscado, depois em ouro | mais de 3 mudanças; número sem consequência |
| `ganhou-perdeu` | nota oficial do patch mais recente | contradição | 1 veredito: quem ganhou · 2 a mudança que prova · 3 quem perdeu · 4 a mudança que prova · 5 opinião marcada como opinião | um campeão por cena, ▲ e ▼ | virar lista de 6 campeões; opinião vendida como fato |
| `dados-da-semana` | fonte de dados com permissão (hoje não há: exige chave da Riot) | número na cara | 1 o dado surpreendente · 2 o ranking (3 itens) · 3 o porquê provável, marcado como hipótese · 4 o que testar · 5 fecho | um item do ranking por cena | sem fonte de dados autorizada esta série fica PARADA: devolva sem_pauta |
| `noticia` | site oficial (leagueoflegends.com/pt-br/news), vídeo de dev da Riot | consequência primeiro | 1 o que muda e para quem · 2 o fato com data · 3 o detalhe que passou batido · 4 o que ainda não se sabe · 5 fecho | arte oficial do anúncio ou do campeão | especular data ou kit; notícia com mais de 48 h vira 'você sabia' |
| `jogada-de-pro` | lolesports.com, Leaguepedia, VOD oficial só como referência de tempo (nunca o trecho) | número na cara ou contradição | 1 o resultado da jogada · 2 o contexto (série, placar, ouro) · 3 o detalhe técnico que a tornou possível (habilidade, tempo de recarga) · 4 o que você copia disso · 5 fecho | clipe oficial das habilidades usadas + arte; mapa esquemático se couber | usar clipe da transmissão ou de streamer; narrar lance que a fonte não descreve |
| `agenda-competitiva` | lolesports.com (agenda e tabela), cblol.gg | consequência primeiro | 1 o jogo que vale a semana e por quê · 2 dia e hora de Brasília · 3 o que está em jogo na tabela · 4 um confronto de campeões para olhar · 5 fecho | escudo não; nomes dos times em texto, arte de campeões-assinatura | agenda vencida: só publica se o jogo ainda não aconteceu na hora da postagem |
| `build-do-patch` | nota do patch + wiki oficial do item | número na cara | 1 o item que mudou e o veredito · 2 antes → depois · 3 em quem a build muda · 4 o que sai da build · 5 fecho | arte do campeão + número do item | recomendar build sem a mudança na fonte; taxa de vitória sem dado |
| `lore` | Universo de LoL (universe.leagueoflegends.com), bio do Data Dragon | detalhe escondido ou pergunta | 1 a cena mais forte da história · 2 quem era antes · 3 o que aconteceu · 4 como isso aparece no kit ou nas falas · 5 fecho | arte do campeão com reenquadramentos; clipe da habilidade ligada ao lore | resumir a bio inteira; teoria de fã como fato |

## Fontes de dados gratuitas (sem chave)

- **Leaguepedia Cargo API** (`tools/esports.py`): agenda, resultados e estatísticas de todas as ligas. Crédito obrigatório na descrição (CC BY-SA 3.0).
- **Data Dragon** e **Community Dragon**: campeões, itens, runas, artes.
- **Clipes de habilidade** do site oficial.
- Taxa de vitória e builds da fila ranqueada **não têm fonte gratuita autorizada**: exigem chave da Riot (developer.riotgames.com). A série `dados-da-semana` fica parada até lá.

## Formato-assinatura: O Ward Viu

Ideia original do canal (proposta de 18/11/2026, a validar com o dono): todo vídeo é contado como **o que um ward revelou**. O nome do canal vira mecânica.

- **Abertura (0 a 0,8 s)**: o palco começa na névoa de guerra (escuro, azul-noite); o som de sentinela cai e a névoa abre em círculo sobre o fato. O título já está na tela.
- **Selo de veredito**: cada vídeo termina com um de três selos fixos: `WARDADO` (confirmado pela fonte), `SEM VISÃO` (a fonte não diz; fica a hipótese marcada) ou `VARRIDO` (a Riot removeu ou reverteu).
- **Série recorrente "A Riot voltou atrás?"**: a cada patch, o canal reabre uma mudança de patches anteriores e confere na nota nova se a Riot manteve, aumentou ou reverteu. É verificável só com fonte oficial e dá motivo para voltar ao canal.
- **Pergunta final fixa**: "Você tinha visão disso?" Convida comentário sem pedir like.
- **O que não muda**: fonte em todo fato, 25 a 45 s, paleta e voz do canal.

## As 74 pautas

| Id | Série | Formato | Pergunta |
| --- | --- | --- | --- |
| ev-001 | `voce-sabia` | voce-sabia | Quais campeões têm o nome tirado do apelido de fundadores ou funcionários da Riot? |
| ev-002 | `voce-sabia` | voce-sabia | De onde veio o Urf, o peixe-boi, e por que ele virou modo de jogo? |
| ev-003 | `voce-sabia` | voce-sabia | Que campeões foram anunciados ou vazados e nunca lançados? |
| ev-004 | `voce-sabia` | voce-sabia | O que era o Instituto da Guerra e por que a Riot apagou essa parte do lore? |
| ev-005 | `voce-sabia` | voce-sabia | Qual skin foi criada junto com um fã por meio de uma ação beneficente? |
| ev-006 | `voce-sabia` | voce-sabia | Que mapas já existiram e foram removidos do jogo? |
| ev-007 | `voce-sabia` | voce-sabia | Qual foi o primeiro campeão lançado depois do lançamento oficial do jogo? |
| ev-008 | `voce-sabia` | voce-sabia | Quais campeões têm parentesco ou relação direta no lore que pouca gente conhece? |
| ev-009 | `voce-sabia` | voce-sabia | O que mudou entre a história de um campeão em Arcane e a versão do jogo? |
| ev-010 | `voce-sabia` | voce-sabia | Qual campeão ficou mais tempo sem receber skin? |
| ev-011 | `voce-sabia` | voce-sabia | Como nasceu o meme do 'Mordekaiser es número uno'? |
| ev-012 | `voce-sabia` | voce-sabia | Quem dubla em português campeões famosos, e que outros personagens essa pessoa faz? |
| ev-013 | `voce-sabia` | voce-sabia | Qual é a origem da rivalidade entre Demacia e Noxus no lore atual? |
| ev-014 | `voce-sabia` | voce-sabia | Que campeão teve a história totalmente reescrita em um rework? |
| ev-015 | `voce-sabia` | voce-sabia | Qual é o significado dos nomes das regiões de Runeterra? |
| ev-016 | `fala-escondida` | voce-sabia | Que falas especiais um campeão tem ao encontrar um rival do lore? |
| ev-017 | `fala-escondida` | voce-sabia | Quais campeões têm fala escondida ao comprar um item específico? |
| ev-018 | `fala-escondida` | voce-sabia | Que provocações mudam quando o alvo é um campeão específico? |
| ev-019 | `fala-escondida` | voce-sabia | Quais skins trocam todas as falas do campeão? |
| ev-020 | `fala-escondida` | voce-sabia | Que campeão tem piada interna com outro jogo da Riot? |
| ev-021 | `fala-escondida` | voce-sabia | Quais falas de morte ou de reviver quase ninguém ouviu? |
| ev-022 | `de-onde-vem` | voce-sabia | De onde vem a palavra 'gank'? |
| ev-023 | `de-onde-vem` | voce-sabia | Por que chamamos de 'kitar' o ato de bater e andar? |
| ev-024 | `de-onde-vem` | voce-sabia | De onde vem 'smurf' para conta secundária? |
| ev-025 | `de-onde-vem` | voce-sabia | Por que o atirador é chamado de 'ADC' e o que mudou no nome oficial? |
| ev-026 | `de-onde-vem` | voce-sabia | De onde vem 'feedar' e 'inting'? |
| ev-027 | `de-onde-vem` | voce-sabia | O que significa 'peel' e por que usamos esse termo? |
| ev-028 | `de-onde-vem` | voce-sabia | Por que a selva tem 'buff azul' e 'buff vermelho' no vocabulário mesmo com nomes oficiais diferentes? |
| ev-029 | `o-jogo-nao-te-conta` | top5 | Como funciona a agressividade das tropas quando você ataca um campeão? |
| ev-030 | `o-jogo-nao-te-conta` | top5 | Quanto tempo dura cada tipo de sentinela e quantas você pode ter no mapa? |
| ev-031 | `o-jogo-nao-te-conta` | top5 | Como a recompensa por abate cresce e quando ela zera? |
| ev-032 | `o-jogo-nao-te-conta` | top5 | O que define qual jogador recebe o ouro da placa da torre? |
| ev-033 | `o-jogo-nao-te-conta` | top5 | Como funciona a experiência compartilhada na rota? |
| ev-034 | `o-jogo-nao-te-conta` | top5 | Que atributos escondidos mudam entre campeões corpo a corpo e à distância? |
| ev-035 | `o-jogo-nao-te-conta` | top5 | Quais itens têm passiva que não acumula com outro item? |
| ev-036 | `itens-e-coisas-removidas` | voce-sabia | Que itens lendários foram removidos e por quê? |
| ev-037 | `itens-e-coisas-removidas` | voce-sabia | Que feitiços de invocador já existiram e sumiram? |
| ev-038 | `itens-e-coisas-removidas` | voce-sabia | Como eram as runas e talentos antes do sistema atual? |
| ev-039 | `itens-e-coisas-removidas` | voce-sabia | Que habilidade antiga de um campeão foi removida por ser forte demais? |
| ev-040 | `itens-e-coisas-removidas` | voce-sabia | Que modos de jogo rotativos nunca mais voltaram? |
| ev-041 | `numero-do-patch` | patch60 | Qual mudança numérica do patch mais altera uma troca de nível 1 a 3? |
| ev-042 | `numero-do-patch` | patch60 | Qual campeão ganhou mais poder no patch, em uma frase e um número? |
| ev-043 | `numero-do-patch` | patch60 | Qual nerf do patch parece pequeno mas mata um combo? |
| ev-044 | `numero-do-patch` | patch60 | Que item mudou e quais três campeões sentem mais? |
| ev-045 | `ganhou-perdeu` | patch60 | Quem ganhou e quem perdeu o patch em cada rota? |
| ev-046 | `ganhou-perdeu` | patch60 | Qual mudança do patch mira o competitivo e sobra para a ranqueada? |
| ev-047 | `ganhou-perdeu` | patch60 | Qual campeão esquecido volta a ser jogável neste patch? |
| ev-048 | `dados-da-semana` | top5 | Quais são os 3 campeões com maior taxa de vitória por rota nesta semana? |
| ev-049 | `dados-da-semana` | top5 | Qual é o campeão mais banido e ele merece? |
| ev-050 | `dados-da-semana` | top5 | Que escolha quase ninguém joga mas vence acima da média? |
| ev-051 | `dados-da-semana` | top5 | Qual campeão mais caiu de popularidade depois do patch? |
| ev-052 | `noticia` | noticia | Que skins foram anunciadas e qual é o destaque? |
| ev-053 | `noticia` | noticia | O que a Riot anunciou no último vídeo de desenvolvedores? |
| ev-054 | `noticia` | noticia | Que campeão novo ou atualização visual foi revelado, e o que já se sabe do kit? |
| ev-055 | `noticia` | noticia | Que mudança de sistema (ranqueada, passe, loja) entra e quando? |
| ev-056 | `noticia` | noticia | Qual foi o resultado e o número mais marcante da rodada do campeonato brasileiro? |
| ev-057 | `noticia` | noticia | O que esperar do próximo patch segundo a prévia oficial? |
| ev-058 | `recordes` | voce-sabia | Qual foi a partida profissional mais longa da história? |
| ev-059 | `recordes` | voce-sabia | Qual jogador tem mais títulos mundiais e com quais campeões? |
| ev-060 | `recordes` | voce-sabia | Que campeão nunca foi escolhido em um Mundial? |
| ev-061 | `recordes` | voce-sabia | Qual foi a maior virada de ouro em uma final? |
| ev-062 | `recordes` | voce-sabia | Que time brasileiro foi mais longe em torneio internacional? |
| ev-063 | `jogada-de-pro` | voce-sabia | Qual foi a jogada mais lembrada de uma final de Mundial e o que a tornou possível? |
| ev-064 | `jogada-de-pro` | voce-sabia | Que roubo de Barão decidiu uma série de playoffs? |
| ev-065 | `jogada-de-pro` | voce-sabia | Qual pentakill em Mundial entrou para a história e com qual campeão? |
| ev-066 | `jogada-de-pro` | voce-sabia | Que jogada de um time brasileiro em torneio internacional ficou famosa? |
| ev-067 | `agenda-competitiva` | noticia | Quais séries das ligas principais valem assistir nesta semana e por quê? |
| ev-068 | `agenda-competitiva` | noticia | Quando começa o próximo torneio internacional e quem já está classificado? |
| ev-069 | `agenda-competitiva` | noticia | Como está a tabela do campeonato brasileiro e quem pode cair ou subir? |
| ev-070 | `build-do-patch` | patch60 | Que item mudou neste patch e em qual campeão a build muda por causa disso? |
| ev-071 | `build-do-patch` | patch60 | Que runa ficou melhor ou pior neste patch e quem deve trocar? |
| ev-072 | `lore` | voce-sabia | Qual é a história de origem de um campeão popular que pouca gente leu? |
| ev-073 | `lore` | voce-sabia | O que aconteceu com Shurima e quem são os Ascendentes? |
| ev-074 | `lore` | voce-sabia | Quem são os Vigias e o que é o Vazio em Runeterra? |
