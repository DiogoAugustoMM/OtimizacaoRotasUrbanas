# Otimização de rotas urbanas com base em mapas

Projeto acadêmico de Grafos em Python. O objetivo é obter dados geográficos
do OpenStreetMap pela Overpass API e utilizar uma implementação própria de
grafos para estudar rotas urbanas.

Esta versão contém a conversão de um JSON local da Overpass em um grafo próprio
direcionado para carros, com distâncias em metros, e uma interface Streamlit para
escolher origem e destino no mapa. Ainda não realiza consultas à API nem calcula
rotas: a rota aparece na tela quando `grafos/dijkstra.py` for implementado.

O escopo definido é de rotas para carros particulares. O conversor aplica um
perfil básico de acesso e sentidos de circulação, com limitações descritas abaixo.

## Tecnologias

- Python 3.10 ou superior.
- Streamlit: interface da aplicação.
- Folium e streamlit-folium: mapa interativo, seleção de pontos e desenho da rota.
- Requests: futuras requisições à Overpass API.
- Pytest: testes das implementações do grupo.

Não utilizar NetworkX nem outras bibliotecas prontas para criar ou processar
grafos. As estruturas e os algoritmos serão implementados pelo grupo.

## Estrutura

```text
.
├── app.py                  # Interface do Streamlit
├── requirements.txt        # Dependências
├── .gitignore              # Exclusões do controle de versão
├── .streamlit/
│   └── config.toml         # Tema do Streamlit
├── README.md
├── mapas/
│   ├── __init__.py
│   ├── overpass.py         # Reservado para acesso à Overpass API
│   ├── regras_carros.py    # Filtro de acesso e interpretação dos sentidos
│   └── conversor.py        # Leitura do JSON e montagem do grafo
├── grafos/
│   ├── __init__.py
│   ├── grafo.py            # Classe Grafo, com pesos e arestas paralelas
│   └── dijkstra.py         # Reservado para o algoritmo de Dijkstra
├── visualizacao/
│   ├── __init__.py
│   └── mapa.py             # Mapa Folium, seleção de pontos e desenho da rota
├── testes/
│   ├── __init__.py
│   ├── test_grafo.py       # Testes da estrutura e integração
│   ├── test_conversor.py   # Validação dos arquivos e carregamento completo
│   ├── test_regras_carros.py # Acesso, sentidos, rotatórias e circuitos
│   └── test_mapa.py        # Vértice mais próximo e coordenadas da rota
└── dados/
    └── .gitkeep            # Mantém a pasta vazia no Git
```

`dados/` é uma pasta de armazenamento, não um pacote Python; por isso não
precisa de `__init__.py`. Seu conteúdo local é ignorado pelo Git.

## Executar no Windows (PowerShell)

No terminal do VS Code, na pasta raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Abra a URL informada no terminal (normalmente `http://localhost:8501`).
Para encerrar a aplicação, pressione `Ctrl+C` no terminal.
Os comandos usam diretamente o Python do ambiente virtual, sem necessidade
de ativá-lo ou alterar a política de execução do PowerShell.

## Usar a interface

1. Coloque um JSON da Overpass (dados brutos, no formato com `elements`) em
   `dados/`. A pasta é ignorada pelo Git, então cada pessoa precisa ter o seu mapa
   local. No overpass-turbo.eu, use uma consulta com `[out:json]`,
   `way["highway"];`, `out body;`, `>;` e `out skel qt;`, execute e baixe em
   Exportar > raw OSM data.
2. Inicie o app e escolha o arquivo na barra lateral.
3. Clique no mapa: o primeiro clique define a origem, o segundo o destino e um
   terceiro recomeça o trajeto. Cada clique é convertido no cruzamento mais
   próximo do grafo, por busca linear. "Limpar trajeto" apaga os dois pontos.
4. "Mostrar ruas do grafo" desenha as arestas em roxo. O mapa de fundo cobre
   o mundo todo, mas o grafo só existe na área e nas vias do JSON carregado, e o
   algoritmo enxerga apenas o grafo.
5. A rota vem de `menor_caminho(grafo, origem, destino)`, em
   `grafos/dijkstra.py`, que deve retornar `(ids_das_arestas, distancia_em_metros)`
   ou `None` quando não houver caminho. Enquanto a função não existir, a tela
   mostra só os pontos e um aviso.

## Montar o grafo local

Salve os dados brutos da Overpass em `dados/bairro_teste.json`, no formato
com `elements`, pontos `node` com coordenadas e vias `way` com listas `nodes`.
O arquivo de dados não é versionado. Na raiz do projeto, execute:

```powershell
.\.venv\Scripts\python.exe -m mapas.conversor
```

Para escolher outro arquivo, informe o caminho (relativo ao terminal ou absoluto):

```powershell
.\.venv\Scripts\python.exe -m mapas.conversor "dados/outro_bairro.json"
```

O carregamento verifica o formato, IDs duplicados, coordenadas, listas de pontos
e referências ausentes. GeoJSON não é aceito: exporte os dados brutos (raw data)
da Overpass. Respostas com `remark` são rejeitadas, pois podem conter resultados
parciais de uma consulta com falha. Relações e áreas não são convertidas.
No terminal, falhas mostram `Erro ao carregar mapa: ...` e encerram com erro.

Para usar em outro módulo, chame a função única de entrada:

```python
from mapas.conversor import carregar_mapa

grafo, pontos, vias = carregar_mapa("dados/bairro_teste.json")
```

Ela retorna uma tupla com três valores e não imprime. O chamador pode tratar
`ValueError` (conteúdo inválido) e `OSError` (problema no arquivo, incluindo
`FileNotFoundError`). Os módulos de interface devem mostrar a mensagem ao usuário.
`pontos` contém todas as coordenadas originais; `vias` contém somente as vias
selecionadas para carros e seus atributos originais.

O conversor filtra as vias antes de selecionar os vértices. Mantém cruzamentos,
extremidades e os limites de cada way para preservar mudanças de regra. Em
circuitos isolados, um limite da way serve como vértice de referência. Depois
constrói os percursos, verifica os sentidos permitidos em todos os segmentos,
soma as distâncias com Haversine e chama
`montar_grafo(vertices, arestas, direcionado=True)`. Essa função retorna uma
instância de `Grafo`. Os resultados aparecem no terminal; o Streamlit usa a
mesma função (`carregar_mapa`) para montar o grafo.

A classe mantém `vertices` (ID → coordenadas), `arestas` (ID próprio → dados)
e `adjacencias` (vértice → lista de IDs de arestas). Seus métodos são
`adicionar_vertice`, `adicionar_aresta` e `obter_vizinhos`. A consulta retorna
uma lista de dicionários com `destino`, `distancia_metros` e `id_aresta`,
preservando múltiplas conexões entre os mesmos vértices. No grafo direcionado,
essa consulta mostra apenas as saídas permitidas do vértice.

Os percursos guardam IDs de pontos intermediários. Suas coordenadas continuam
no dicionário `pontos` do conversor, e os atributos das vias continuam em `vias`.
Para desenhar o mapa, use esses dados junto com o grafo. As listas de percurso
ficam orientadas da origem para o destino de cada aresta direcionada. A geometria
e as referências aos segmentos são invertidas juntas quando a conexão é de volta.

## Regras básicas para carros

- `oneway=yes`: permite a ordem dos pontos da way; `oneway=-1`: ordem inversa;
  `oneway=no`: ambos os sentidos. Também são aceitos os valores equivalentes
  `true`, `false`, `1` e `0`.
- Sem indicação explícita, `junction=roundabout` e `highway=motorway` implicam
  sentido único na ordem dos pontos. Uma indicação explícita tem prioridade.
  Exceções `oneway:motorcar`, `oneway:motor_vehicle` e `oneway:vehicle` também
  são consideradas, nessa ordem, antes da tag genérica.
- Uma rua de mão dupla gera duas arestas direcionadas, com percursos inversos
  e a mesma distância. Não some essas duas distâncias para medir o tamanho físico
  da rua: elas representam duas opções de circulação sobre o mesmo trecho.
- As regras de acesso priorizam `motorcar`, `motor_vehicle`, `vehicle` e `access`,
  nessa ordem. A regra mais específica substitui a regra mais geral.
- O perfil permite acesso `yes`, `permissive` e `designated`. Sem restrição
  explícita, aceita as categorias viárias usuais listadas em `regras_carros.py`.
  Caminhos como `footway`, `cycleway`, `pedestrian` e `track` exigem permissão
  explícita para veículos/carros. Escadas, vias em construção e áreas são excluídas.
- Acesso `no`, `private` e valores não reconhecidos são excluídos. Por escolha do
  projeto, vias `destination`, `customers`, `delivery` e semelhantes também ficam
  fora do perfil de passagem. Isso é uma simplificação: esses valores podem
  permitir acesso a usuários ou destinos específicos, mas não trânsito irrestrito.
- Vias com regras condicionais, acesso diferente por sentido ou valores como
  `oneway=reversible` são excluídas nesta versão, pois não há avaliação de horário.
  `filtrar_vias_carros(vias)` retorna as vias aceitas e os motivos das exclusões.

Referências das tags: [oneway](https://wiki.openstreetmap.org/wiki/Key:oneway),
[access](https://wiki.openstreetmap.org/wiki/Key:access) e
[roundabout](https://wiki.openstreetmap.org/wiki/Tag:junction%3Droundabout).

Limitações: não processa relações de restrição de conversão, barreiras ou
restrições em nodes, faixas, condições temporais, dimensões do veículo ou regras
legais locais implícitas. Não estima trânsito ou tempo de viagem. Uma extremidade
pode ser o limite dos dados, e não uma rua sem saída. É um modelo acadêmico básico,
cujo resultado depende da qualidade e da completude das tags do mapa.

A classe `Grafo` continua aceitando `Grafo()` não direcionado para exemplos
genéricos. `montar_grafo` também mantém `direcionado=False` por padrão para esse
uso; é `carregar_mapa` que aplica o perfil de carros e solicita o grafo direcionado.

## Testes

Execute na raiz (os testes usam dados pequenos e não dependem do JSON local):

```powershell
.\.venv\Scripts\python.exe -m pytest testes
```

## Próximas etapas

1. Implementar as consultas à Overpass API em `mapas/overpass.py`.
2. Integrar o resultado do Dijkstra à interface (a rota e a distância já têm lugar na tela).
3. Implementar o algoritmo de Dijkstra usando os IDs das arestas para preservar
   a escolha entre percursos paralelos.
4. Exibir o tempo estimado e comparar critérios de otimização.
5. Ampliar os testes conforme as próximas funcionalidades forem implementadas.

Ao utilizar dados do OpenStreetMap na visualização, incluir a atribuição
aos colaboradores do OpenStreetMap. Definir limites de consulta e tratamento
de falhas da Overpass API durante a implementação da integração.