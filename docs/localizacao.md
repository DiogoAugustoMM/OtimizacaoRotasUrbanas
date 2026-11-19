# Seleção de origem e destino no meio das ruas

## O problema

A interface associava o clique ao vértice mais próximo. Como os vértices do grafo
base representam principalmente cruzamentos, extremidades e limites das vias,
um clique no meio de uma rua longa podia selecionar um local distante ou até um
vértice de outra rua próxima.

## O que foi implementado

O módulo `mapas/localizacao.py` procura o segmento de rua mais próximo do clique,
projeta o ponto sobre ele e prepara vértices temporários para essa consulta.

```text
Grafo base:
A -------------------------------- B

Grafo da consulta:
A -------- P ------------ Q ------- B
           origem         destino
```

A busca considera todos os segmentos da geometria, inclusive os que desenham
curvas. O grafo base e o JSON permanecem preservados. A preparação acontece
quando os cliques mudam; controles de visualização não repetem a divisão.

## As três funções

| Função | Responsabilidade |
|---|---|
| `criar_indice_segmentos` | Preparar os segmentos e suas coordenadas em uma projeção plana local, sem duplicar ida e volta |
| `localizar_ponto_na_via` | Encontrar o segmento mais próximo e a posição do clique projetada sobre ele |
| `inserir_pontos_temporarios` | Preparar o grafo da consulta com os pontos selecionados e as arestas divididas |

O índice é um dicionário com uma lista de segmentos. Não é um índice espacial
com árvore ou grade: a procura ainda percorre a lista inteira. Ele evita refazer
a projeção das coordenadas e procurar duas vezes na geometria de mão dupla.

## Lógica da localização

1. Convertemos latitude e longitude para coordenadas aproximadas em metros em
   um plano local, usando a latitude média do grafo como referência.
2. Para cada segmento entre dois pontos consecutivos, calculamos a projeção do
   clique sobre sua linha e limitamos o resultado ao intervalo do segmento.
3. Escolhemos a projeção com menor distância ao clique.
4. Guardamos os IDs do segmento, a fração de seu comprimento e as coordenadas
   projetadas. A fração é expressa na ordem crescente dos IDs do segmento;
   ela não representa um sentido permitido de circulação.

A aproximação foi escolhida para mapas urbanos. As distâncias das arestas
continuam usando Haversine; não são calculadas por diferenças de graus.

## Lógica da divisão

1. Reutilizamos um ponto OSM se o clique projetado coincidir com ele. Se for um
   ponto intermediário da geometria, ele passa a ser vértice na consulta.
2. Criamos IDs negativos para pontos novos, evitando colisões com IDs existentes.
3. Tratamos origem e destino juntos e ordenamos as inserções ao longo do segmento.
4. Copiamos os dicionários principais do grafo, substituímos somente as arestas
   afetadas e atualizamos suas listas de adjacência.
5. Recalculamos as distâncias dos pedaços e preservamos seus pontos intermediários
   e as referências às vias usadas pelo cálculo de tempo.

Em mão única, `A → B` vira `A → P → B`. Não é criada conexão inversa.
Em mão dupla, os dois sentidos são divididos. Isso evita que um ponto possa
acessar só uma direção de uma rua de mão dupla.

Inserir os dois pontos juntos também resolve o caso em que origem e destino
estão na mesma aresta, permitindo calcular diretamente o trecho `P → Q`.

Não unimos segmentos distintos pela proximidade das coordenadas: ruas que
cruzam um viaduto continuam separadas quando não compartilham os mesmos IDs.

## Integração com o trabalho dos colegas

| Arquivo | Alteração |
|---|---|
| `mapas/localizacao.py` | Novo módulo com a localização e a preparação do grafo |
| `app.py` | Usa os novos pontos, mantém a preparação na sessão e chama os cálculos existentes |
| `visualizacao/mapa.py` | Agrupa a camada de ruas e remove a duplicação visual de ida e volta |
| `grafos/grafo.py` | Estrutura preservada |
| `grafos/dijkstra.py` | Algoritmo preservado |
| `resultados.py` | Comparação preservada |

O contrato continua sendo um objeto `Grafo`, um dicionário de `pontos` e o
dicionário de `vias`. As rotas por distância e tempo usam o mesmo grafo preparado,
então seus IDs de aresta continuam comparáveis.

Também corrigimos a limpeza de seleção ao trocar o mapa, invalidamos o cache ao
substituir um arquivo e evitamos recalcular as duas rotas ao alternar controles.

## Melhoria no desenho das ruas

Antes, a camada de diagnóstico criava uma PolyLine do Folium por aresta,
inclusive duas linhas sobrepostas para ruas de mão dupla. Agora os percursos
são agrupados em uma geometria MultiLineString do GeoJSON, preparada com o mapa
base e sem repetir os percursos inversos. O mapa utiliza o renderizador Canvas.

Isso reduz o número de objetos e o HTML enviado. Não elimina o custo de enviar
todas as coordenadas de um mapa muito grande ou de baixar os mapas de fundo.

## Texto sugerido para apresentar

> Implementei a seleção de locais ao longo das ruas, em vez de limitar o usuário
> aos cruzamentos. Para cada clique, encontro o segmento viário mais próximo e
> projeto o ponto sobre ele. Depois preparo uma cópia do grafo para a consulta,
> adicionando origem e destino como vértices temporários e dividindo as arestas
> afetadas. Preservo os sentidos de circulação, as curvas, as distâncias e os
> atributos usados para estimar tempo. Assim, o Dijkstra e a comparação de rotas
> continuam trabalhando com a mesma estrutura que já esperavam.

## Limitações que devem ser explicadas

- A origem e o destino são os pontos ajustados sobre as vias; o deslocamento do
  clique até a via é informado separadamente e não entra na rota de carro.
- Escolher o trecho mais próximo não identifica endereço nem acesso de garagem.
  Pistas paralelas ou vias sobrepostas podem exigir outro clique do usuário.
- A projeção é uma aproximação urbana e a busca ainda é linear.
- As restrições de trânsito já documentadas para o perfil de carros permanecem.
- IDs temporários e suas arestas pertencem somente à consulta, não ao mapa original.
