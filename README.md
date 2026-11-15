# Otimização de rotas urbanas com base em mapas

Projeto acadêmico de Grafos em Python. O objetivo é obter dados geográficos
do OpenStreetMap pela Overpass API e utilizar uma implementação própria de
grafos para estudar rotas urbanas.

Esta versão contém uma tela inicial e a conversão de um JSON local da Overpass
em um grafo próprio não direcionado, com distâncias em metros. Ainda não
realiza consultas à API, cálculo de rotas ou visualização do grafo.

## Tecnologias

- Python 3.10 ou superior.
- Streamlit: interface da aplicação.
- Folium: futura visualização de mapas e rotas.
- Requests: futuras requisições à Overpass API.
- Pytest: testes das implementações do grupo.

Não utilizar NetworkX nem outras bibliotecas prontas para criar ou processar
grafos. As estruturas e os algoritmos serão implementados pelo grupo.

## Estrutura

```text
.
├── app.py                  # Interface inicial do Streamlit
├── requirements.txt        # Dependências
├── .gitignore              # Exclusões do controle de versão
├── README.md
├── mapas/
│   ├── __init__.py
│   ├── overpass.py         # Reservado para acesso à Overpass API
│   └── conversor.py        # Leitura do JSON e montagem do grafo
├── grafos/
│   ├── __init__.py
│   ├── grafo.py            # Classe Grafo, com pesos e arestas paralelas
│   └── dijkstra.py         # Reservado para o algoritmo de Dijkstra
├── visualizacao/
│   ├── __init__.py
│   └── mapa.py             # Reservado para a visualização com Folium
├── testes/
│   ├── __init__.py
│   └── test_grafo.py       # Testes da estrutura e integração
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

## Montar o grafo local

Salve os dados brutos da Overpass em `dados/bairro_teste.json`, no formato
com `elements`, pontos `node` com coordenadas e vias `way` com listas `nodes`.
O arquivo de dados não é versionado. Na raiz do projeto, execute:

```powershell
.\.venv\Scripts\python.exe -m mapas.conversor
```

O conversor seleciona cruzamentos e extremidades, constrói percursos, soma as
distâncias dos segmentos com Haversine e chama `montar_grafo(vertices, arestas)`.
Essa função retorna uma instância de `Grafo`. Os resultados aparecem no terminal;
o Streamlit ainda não está integrado à conversão.

A classe mantém `vertices` (ID → coordenadas), `arestas` (ID próprio → dados)
e `adjacencias` (vértice → lista de IDs de arestas). Seus métodos são
`adicionar_vertice`, `adicionar_aresta` e `obter_vizinhos`. A consulta retorna
uma lista de dicionários com `destino`, `distancia_metros` e `id_aresta`,
preservando múltiplas conexões entre os mesmos vértices.

Os percursos guardam IDs de pontos intermediários. Suas coordenadas continuam
no dicionário `pontos` do conversor, e os atributos das vias continuam em `vias`.
Para desenhar o mapa, use esses dados junto com o grafo. As listas de percurso
ficam na orientação original da aresta; inverta-as ao desenhar o sentido inverso.

Limitações: todos os trechos são tratados como transitáveis nos dois sentidos,
sem filtrar acesso ou meio de transporte. Circuitos isolados compostos apenas
por pontos com dois vizinhos ainda não são selecionados. Uma extremidade pode
ser o limite dos dados, e não uma rua sem saída. A opção `Grafo(direcionado=True)`
permite inserir conexões em um único sentido, mas não interpreta as tags do OSM;
essa integração será desenvolvida posteriormente.

## Testes

Execute na raiz (os testes usam dados pequenos e não dependem do JSON local):

```powershell
.\.venv\Scripts\python.exe -m pytest testes
```

## Próximas etapas

1. Implementar as consultas à Overpass API em `mapas/overpass.py`.
2. Tratar sentidos, acesso e casos especiais na conversão.
3. Implementar o algoritmo de Dijkstra usando os IDs das arestas para preservar
   a escolha entre percursos paralelos.
4. Desenvolver a visualização com Folium e integrá-la ao Streamlit.
5. Ampliar os testes conforme as próximas funcionalidades forem implementadas.

Ao utilizar dados do OpenStreetMap na visualização, incluir a atribuição
aos colaboradores do OpenStreetMap. Definir limites de consulta e tratamento
de falhas da Overpass API durante a implementação da integração.
