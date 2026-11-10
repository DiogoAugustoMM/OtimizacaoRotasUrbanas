# Otimização de rotas urbanas com base em mapas

Projeto acadêmico de Grafos em Python. O objetivo é obter dados geográficos
do OpenStreetMap pela Overpass API e utilizar uma implementação própria de
grafos para estudar rotas urbanas.

Esta versão contém apenas a estrutura inicial e uma tela de apresentação.
Ainda não realiza consultas, conversão de mapas, cálculo ou exibição de rotas.

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
│   └── conversor.py        # Reservado para conversão dos dados em grafo
├── grafos/
│   ├── __init__.py
│   ├── grafo.py            # Reservado para a estrutura própria de grafo
│   └── dijkstra.py         # Reservado para o algoritmo de Dijkstra
├── visualizacao/
│   ├── __init__.py
│   └── mapa.py             # Reservado para a visualização com Folium
├── testes/
│   └── __init__.py         # Pacote dos futuros testes
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

## Testes

Quando os testes forem adicionados, execute na raiz:

```powershell
.\.venv\Scripts\python.exe -m pytest testes
```

Use nomes como `test_grafo.py` e funções iniciadas por `test_`.
Nesta etapa não há casos de teste; o Pytest informará que nenhum teste foi
coletado (código de saída 5).

## Próximas etapas

1. Implementar as consultas à Overpass API em `mapas/overpass.py`.
2. Definir a estrutura própria do grafo e o contrato da conversão.
3. Implementar a conversão dos dados e o algoritmo de Dijkstra.
4. Desenvolver a visualização com Folium e integrá-la ao Streamlit.
5. Adicionar testes para os módulos implementados.

Ao utilizar dados do OpenStreetMap na visualização, incluir a atribuição
aos colaboradores do OpenStreetMap. Definir limites de consulta e tratamento
de falhas da Overpass API durante a implementação da integração.
