# Otimização de rotas urbanas com base em mapas

Projeto acadêmico de Teoria dos Grafos desenvolvido em Python. A aplicação utiliza dados geográficos do OpenStreetMap, convertidos em um grafo próprio, para calcular e comparar rotas urbanas de carros particulares.

A versão atual carrega arquivos JSON locais exportados da Overpass, considera o sentido de circulação das vias e utiliza uma implementação própria do algoritmo de Dijkstra para encontrar a rota de menor distância e a rota de menor tempo estimado. A interface permite escolher origem e destino no mapa, visualizar o trajeto selecionado e comparar os resultados dos dois critérios.

**Importante:** a consulta automática à Overpass API não foi implementada. Os arquivos de mapa precisam ser obtidos e salvos localmente na pasta `dados/`.

## Tecnologias

- Python 3.10 ou superior.
- Streamlit: interface da aplicação.
- Folium e streamlit-folium: mapa interativo, seleção de pontos e desenho da rota.
- Requests: dependência prevista para futuras consultas à Overpass API.
- Pytest: testes automatizados.

O grafo e o algoritmo de Dijkstra são implementações do grupo, sem bibliotecas prontas para criação ou processamento de grafos, como NetworkX.

## Funcionalidades implementadas

- Leitura e validação de JSON bruto do OpenStreetMap exportado pela Overpass.
- Conversão de ruas e cruzamentos em um grafo direcionado para carros, com distâncias em metros e respeito aos sentidos de circulação considerados pelo conversor.
- Seleção de origem e destino por cliques no mapa.
- Cálculo da rota de menor distância e da rota de menor tempo estimado usando Dijkstra.
- Exibição da rota selecionada sobre o mapa, da distância total e do tempo estimado.
- Comparação dos dois critérios, indicando se os trajetos são iguais ou diferentes e, quando diferentes, a distância adicional e a economia de tempo da rota mais rápida.
- Mensagem informativa quando não existe caminho entre os pontos selecionados.

## Estrutura

```text
.
├── app.py                     # Interface Streamlit e exibição dos resultados
├── resultados.py              # Cálculo e organização da comparação entre rotas
├── requirements.txt           # Dependências
├── .gitignore                 # Exclusões do controle de versão
├── .streamlit/
│   └── config.toml            # Tema do Streamlit
├── README.md
├── mapas/
│   ├── __init__.py
│   ├── overpass.py             # Reservado para futuras consultas à Overpass API
│   ├── regras_carros.py       # Filtro de acesso e interpretação dos sentidos
│   ├── localizacao.py         # Cliques sobre vias e vértices temporários
│   └── conversor.py           # Leitura do JSON e montagem do grafo
├── grafos/
│   ├── __init__.py
│   ├── grafo.py                # Classe Grafo, com pesos e arestas paralelas
│   └── dijkstra.py            # Menor caminho por distância ou tempo
├── visualizacao/
│   ├── __init__.py
│   └── mapa.py                # Mapa Folium e desenho da rota
├── testes/
│   ├── __init__.py
│   ├── test_conversor.py      # Validação dos arquivos e carregamento
│   ├── test_localizacao.py    # Seleção e divisão de trechos para uma consulta
│   ├── test_app.py            # Estado da interface com cliques simulados
│   ├── test_dijkstra.py       # Caminhos por distância e tempo e casos especiais
│   ├── test_grafo.py          # Estrutura e conexões do grafo
│   ├── test_mapa.py           # Seleção de vértices e coordenadas da rota
│   ├── test_regras_carros.py  # Acesso, sentidos, rotatórias e circuitos
│   └── test_resultados.py     # Comparação de rotas
└── dados/
    └── .gitkeep               # Mantém a pasta vazia no Git
```

`dados/` é uma pasta de armazenamento, não um pacote Python; por isso não precisa de `__init__.py`. Os mapas locais são ignorados pelo Git conforme o `.gitignore` atual.

## Executar no Windows (PowerShell)

No terminal do VS Code, na pasta raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Abra o endereço informado no terminal (normalmente `http://localhost:8501`). Para encerrar a aplicação, pressione `Ctrl+C` no terminal.

Os comandos utilizam diretamente o Python do ambiente virtual, sem precisar ativá-lo ou alterar a política de execução do PowerShell.

### Obter um mapa para teste

1. Acesse [Overpass Turbo](https://overpass-turbo.eu/) e selecione uma região no mapa.
2. Utilize uma consulta para vias no retângulo visível, por exemplo:

   ```text
   [out:json][timeout:60];
   way["highway"]({{bbox}});
   out body;
   >;
   out skel qt;
   ```

3. Execute a consulta e, em **Export**, baixe os dados brutos (*raw OSM data*) em JSON, não GeoJSON.
4. Salve o arquivo na pasta `dados/`, por exemplo `dados/bairro_teste.json`.

Como os JSONs de `dados/` não são versionados, cada integrante precisa salvar um arquivo local para utilizar a interface.

## Usar a interface

1. Inicie a aplicação e selecione o arquivo JSON na barra lateral.
2. Clique no mapa para definir a **origem** e depois o **destino**. Cada clique é projetado sobre o segmento de via mais próximo, incluindo o meio de ruas longas. Os pontos selecionados viram vértices temporários em uma cópia para a consulta. Um novo clique após definir os dois pontos inicia outro trajeto; o botão **Limpar trajeto** remove a seleção.
3. Escolha o critério **Mais curta (Distância)** ou **Mais rápida (Tempo)**. A rota selecionada aparece em azul.
4. Consulte, no painel **Trajeto**, a distância total e o tempo estimado da rota selecionada.
5. Na seção **Comparação das rotas**, confira distância e tempo das duas alternativas. Se os trajetos forem diferentes, o sistema informa quantos metros a mais a rota rápida percorre e quantos segundos ela economiza; se forem iguais, informa que ambos os critérios recomendam o mesmo trajeto.
6. A opção **Mostrar ruas do grafo** desenha os percursos em roxo, agrupados em uma camada GeoJSON, sem duplicar ida e volta. O mapa de fundo pode mostrar ruas fora do grafo; o cálculo considera somente as vias representadas no JSON carregado.

Quando não existe caminho dirigido entre origem e destino, a interface informa a situação e não apresenta uma comparação de rotas inexistentes. Quando os dois cliques correspondem ao mesmo ponto da via, a interface solicita pontos mais afastados. O deslocamento entre clique e via é informado no painel; ele não faz parte da distância da rota de carro.

A troca de arquivo limpa a seleção. Alterações no mesmo arquivo invalidam o cache
por data de modificação e tamanho. A cópia para a consulta é preparada somente
quando os pontos mudam; alternar o critério ou a exibição das ruas reutiliza as
rotas já calculadas. A geometria da camada de ruas e o índice de segmentos também
são preparados uma vez por versão do mapa.

## Seleção no meio das ruas

O módulo `mapas/localizacao.py` preserva o formato esperado por Dijkstra e pela
comparação. Não altera o JSON nem o grafo base compartilhado em cache.

```python
from mapas.localizacao import (
    criar_indice_segmentos, localizar_ponto_na_via, inserir_pontos_temporarios,
)

indice = criar_indice_segmentos(grafo, pontos)
local_origem = localizar_ponto_na_via(indice, pontos, latitude_origem, longitude_origem)
local_destino = localizar_ponto_na_via(indice, pontos, latitude_destino, longitude_destino)
grafo_consulta, pontos_consulta, ids = inserir_pontos_temporarios(
    grafo, pontos, [local_origem, local_destino]
)
origem, destino = ids
# Use grafo_consulta e pontos_consulta, junto com vias, nos cálculos existentes.
```

O índice guarda segmentos físicos sem duplicar os sentidos. A busca linear usa
uma projeção plana local aproximada para encontrar a posição ao longo do segmento,
adequada à escala urbana. O ajuste respeita a geometria de cada rua; não projeta
somente sobre a linha reta entre os cruzamentos.

Os dois pontos são inseridos simultaneamente, ordenados ao longo dos segmentos.
Se ambos estiverem na mesma aresta, o trecho entre eles é criado diretamente.
Se a projeção coincidir com um ponto OSM existente, seu ID é reutilizado e, quando
necessário, ele é promovido a vértice. Novos pontos recebem IDs negativos sem
colisão. Coincidências a até 1 cm são tratadas como o mesmo ponto.

As conexões afetadas são substituídas por trechos menores. Mãos únicas continuam
em um sentido; os dois sentidos de uma rua de mão dupla são divididos juntos.
Pesos são recalculados com Haversine e as referências às vias são preservadas
em cada segmento, mantendo o cálculo de tempo existente. Pontes e ruas que só se
cruzam visualmente não são unidas, pois a divisão usa os IDs dos segmentos.

As estruturas principais do grafo são copiadas, mas os registros não alterados
são reutilizados para leitura; apenas adjacências e arestas afetadas são refeitas.
Os algoritmos consumidores devem tratar os registros do grafo como dados de leitura.
Detalhes para a apresentação estão em [docs/localizacao.md](docs/localizacao.md).

## Montar o grafo local

O arquivo de entrada deve ser um JSON bruto da Overpass com `elements`, nós (`node`) com coordenadas e vias (`way`) com listas `nodes`. Para processar `dados/bairro_teste.json` pelo terminal:

```powershell
.\.venv\Scripts\python.exe -m mapas.conversor
```

Para escolher outro arquivo:

```powershell
.\.venv\Scripts\python.exe -m mapas.conversor "dados/outro_bairro.json"
```

O carregamento verifica formato, IDs duplicados, coordenadas, listas de pontos e referências ausentes. GeoJSON não é aceito. Respostas com `remark` são rejeitadas, pois podem conter resultados parciais de uma consulta com falha. Relações e áreas não são convertidas. Em caso de falha, o terminal informa `Erro ao carregar mapa: ...`.

Para carregar os dados em outro módulo:

```python
from mapas.conversor import carregar_mapa

grafo, pontos, vias = carregar_mapa("dados/bairro_teste.json")
```

A função retorna uma tupla com três valores e não imprime. O chamador pode tratar `ValueError` para conteúdo inválido e `OSError` para problemas com o arquivo. `pontos` contém as coordenadas originais e `vias` contém as vias selecionadas para carros com seus atributos.

O conversor filtra as vias antes de selecionar os vértices. Mantém cruzamentos, extremidades e limites de cada *way* para preservar mudanças de regra. Em circuitos isolados, um limite da *way* serve como vértice de referência. Em seguida, constrói os percursos, verifica os sentidos permitidos, soma as distâncias com Haversine e chama `montar_grafo(vertices, arestas, direcionado=True)`.

A classe `Grafo` armazena `vertices` (ID → coordenadas), `arestas` (ID próprio → dados) e `adjacencias` (vértice → IDs de arestas). Seus métodos incluem `adicionar_vertice`, `adicionar_aresta` e `obter_vizinhos`. A consulta aos vizinhos retorna `destino`, `distancia_metros` e `id_aresta`, preservando conexões paralelas entre os mesmos vértices. No grafo direcionado, só apresenta as conexões que podem sair do vértice.

Os percursos guardam IDs de pontos intermediários, que continuam disponíveis em `pontos`. As arestas também preservam as referências aos segmentos e às vias de origem para permitir o cálculo do tempo e o desenho do trajeto. A classe `Grafo` mantém a opção não direcionada (`Grafo()`) para exemplos genéricos; `carregar_mapa` utiliza o modelo direcionado para carros.

## Cálculo e comparação das rotas

O módulo `grafos/dijkstra.py` implementa `calcular_menor_caminho(grafo, origem, destino, criterio="distancia", pontos=None, vias=None)`.

- **Distância:** considera a soma das distâncias das arestas, em metros.
- **Tempo:** considera o tempo estimado de cada segmento, a partir de sua distância e velocidade em km/h. Usa `maxspeed` quando há um valor numérico reconhecido e adota velocidades padrão por categoria de via (`highway`) quando essa informação não está disponível ou não é reconhecida. O tempo é calculado em segundos.

O cálculo por tempo exige `pontos` e `vias`. Quando encontra um caminho, a função retorna um dicionário com `criterio`, `distancia_total`, `tempo_total`, `vertices`, `arestas` e `percurso_completo`. Caso não exista caminho, retorna `None`.

A função `comparar_rotas(grafo, origem, destino, pontos, vias)`, em `resultados.py`, executa o Dijkstra pelos dois critérios e reúne os resultados. Também informa:

- `mesmo_trajeto`: se as duas rotas usam a mesma sequência de IDs de arestas;
- `distancia_adicional_metros`: quanto a rota mais rápida é mais longa que a mais curta;
- `tempo_economizado_segundos`: quanto tempo estimado a rota mais rápida economiza.

A interface usa esses resultados para mostrar a opção selecionada no mapa e a comparação no painel lateral. Se não houver caminho, `comparar_rotas` retorna `None`.

## Regras básicas para carros

- `oneway=yes`: permite a ordem dos pontos da *way*; `oneway=-1`: ordem inversa; `oneway=no`: ambos os sentidos. Também são aceitos `true`, `false`, `1` e `0`.
- Sem indicação explícita, `junction=roundabout` e `highway=motorway` implicam sentido único na ordem dos pontos. Uma indicação explícita tem prioridade. As tags `oneway:motorcar`, `oneway:motor_vehicle` e `oneway:vehicle` também são consideradas, nessa ordem, antes da tag genérica.
- Uma rua de mão dupla gera duas arestas direcionadas, com percursos inversos e a mesma distância. Essas arestas representam opções de circulação, não duas ruas físicas diferentes.
- As regras de acesso priorizam `motorcar`, `motor_vehicle`, `vehicle` e `access`, nessa ordem. A regra mais específica substitui a mais geral.
- O perfil permite acesso `yes`, `permissive` e `designated`. Sem restrição explícita, aceita as categorias viárias usuais listadas em `regras_carros.py`. Caminhos como `footway`, `cycleway`, `pedestrian` e `track` exigem permissão explícita para veículos/carros. Escadas, vias em construção e áreas são excluídas.
- Acesso `no`, `private` e valores não reconhecidos são excluídos. Por escolha do projeto, vias `destination`, `customers`, `delivery` e semelhantes também ficam fora do perfil de passagem, mesmo que possam permitir acessos específicos.
- Vias com regras condicionais, acesso diferente por sentido ou valores como `oneway=reversible` são excluídas nesta versão, pois não há avaliação de horários. `filtrar_vias_carros(vias)` retorna as vias aceitas e os motivos das exclusões.

Referências das tags: [oneway](https://wiki.openstreetmap.org/wiki/Key:oneway), [access](https://wiki.openstreetmap.org/wiki/Key:access) e [roundabout](https://wiki.openstreetmap.org/wiki/Tag:junction%3Droundabout).

## Limitações

- Não há consulta automática à Overpass API; os dados do mapa são carregados de arquivos JSON locais.
- O tempo calculado é uma **estimativa** baseada na distância dos segmentos e nas velocidades das vias, não no trânsito real. Não considera congestionamentos, semáforos, paradas ou condições momentâneas de tráfego.
- O perfil básico para carros não processa relações de restrição de conversão, barreiras ou restrições em nós, faixas, condições temporais, dimensões do veículo ou todas as regras legais locais implícitas.
- A área exportada pode conter limites artificiais e componentes sem conexão; uma extremidade do grafo pode representar apenas o limite dos dados. O sistema só encontra caminhos existentes e permitidos dentro do grafo carregado.
- Os resultados dependem da qualidade e da completude dos dados e das tags do OpenStreetMap.
- A seleção considera a proximidade geométrica, sem conhecer o endereço, o lado
  de acesso de um prédio ou a intenção do motorista. Em pistas paralelas, viadutos
  e trechos sobrepostos, confira a posição do marcador. A projeção local não é
  destinada a consultas em escala continental ou nas regiões polares.

## Testes

Para executar a suíte automatizada, na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -m pytest testes
```

Os testes cobrem validação e conversão do mapa, regras para carros, estrutura do grafo, Dijkstra, visualização e comparação de resultados. A maioria utiliza dados pequenos criados nos próprios testes, sem depender dos JSONs locais. O teste `test_integracao_com_mapa_real`, em `testes/test_dijkstra.py`, utiliza `dados/bairro_teste.json` caso o arquivo esteja disponível; caso contrário, é ignorado.

## Próximas etapas

1. Implementar a consulta à Overpass API em `mapas/overpass.py`, incluindo limites de consulta e tratamento de falhas.
2. Ampliar a validação integrada da aplicação conforme novas funcionalidades forem adicionadas.

Os mapas e a visualização devem manter a atribuição aos [colaboradores do OpenStreetMap](https://www.openstreetmap.org/copyright).
