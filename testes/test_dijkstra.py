from pathlib import Path
import pytest

from grafos.dijkstra import calcular_menor_caminho
from grafos.grafo import Grafo
from mapas.conversor import calcular_distancia_metros, carregar_mapa


@pytest.fixture
def cenario_base():
    """Prepara um grafo direcionado base e um dicionário de pontos."""
    grafo = Grafo(direcionado=True)
    pontos = {
        1: {"latitude": -19.9200, "longitude": -43.9300},
        2: {"latitude": -19.9210, "longitude": -43.9300},
        3: {"latitude": -19.9220, "longitude": -43.9300},
        4: {"latitude": -19.9210, "longitude": -43.9320},
        99: {"latitude": -19.9205, "longitude": -43.9300},  # Ponto intermediário (curva)
    }
    for vid in (1, 2, 3, 4):
        grafo.adicionar_vertice(
            vid, pontos[vid]["latitude"], pontos[vid]["longitude"]
        )
    return grafo, pontos


def test_menor_caminho_por_distancia(cenario_base):
    """Deve escolher o caminho com menor soma de metros."""
    grafo, _ = cenario_base

    # Caminho 1 -> 2 -> 3 = 100 + 150 = 250m
    a1 = grafo.adicionar_aresta(1, 2, 100.0)
    a2 = grafo.adicionar_aresta(2, 3, 150.0)
    # Caminho alternativo 1 -> 4 -> 3 = 200 + 200 = 400m
    grafo.adicionar_aresta(1, 4, 200.0)
    grafo.adicionar_aresta(4, 3, 200.0)

    resultado = calcular_menor_caminho(grafo, 1, 3, criterio="distancia")

    assert resultado is not None
    assert resultado["distancia_total"] == pytest.approx(250.0)
    assert resultado["vertices"] == [1, 2, 3]
    assert resultado["arestas"] == [a1, a2]
    assert resultado["percurso_completo"] == [1, 2, 3]


def test_arestas_paralelas_escolhe_mais_curta(cenario_base):
    """Entre duas arestas ligando os mesmos vértices, deve escolher a menor."""
    grafo, _ = cenario_base

    grafo.adicionar_aresta(1, 2, 500.0)
    aresta_curta = grafo.adicionar_aresta(1, 2, 120.0)

    resultado = calcular_menor_caminho(grafo, 1, 2)

    assert resultado["distancia_total"] == pytest.approx(120.0)
    assert resultado["arestas"] == [aresta_curta]


def test_criterio_tempo_vs_distancia(cenario_base):
    """Deve preferir uma rota mais longa se a velocidade da via compensar no tempo."""
    grafo, pontos = cenario_base

    # Rota A (curta e lenta): 1 -> 2 -> 3 a 20 km/h
    d_1_2 = calcular_distancia_metros(pontos[1], pontos[2])
    d_2_3 = calcular_distancia_metros(pontos[2], pontos[3])
    grafo.adicionar_aresta(
        1, 2, d_1_2, segmentos=[{"origem": 1, "destino": 2, "vias": [10]}]
    )
    grafo.adicionar_aresta(
        2, 3, d_2_3, segmentos=[{"origem": 2, "destino": 3, "vias": [10]}]
    )

    # Rota B (mais longa, porém avenida rápida): 1 -> 4 -> 3 a 80 km/h
    d_1_4 = calcular_distancia_metros(pontos[1], pontos[4])
    d_4_3 = calcular_distancia_metros(pontos[4], pontos[3])
    a_rapida_1 = grafo.adicionar_aresta(
        1, 4, d_1_4, segmentos=[{"origem": 1, "destino": 4, "vias": [20]}]
    )
    a_rapida_2 = grafo.adicionar_aresta(
        4, 3, d_4_3, segmentos=[{"origem": 4, "destino": 3, "vias": [20]}]
    )

    vias = {
        10: {"tags": {"highway": "residential", "maxspeed": "20"}},
        20: {"tags": {"highway": "trunk", "maxspeed": "80"}},
    }

    rota_curta = calcular_menor_caminho(
        grafo, 1, 3, criterio="distancia", pontos=pontos, vias=vias
    )
    rota_rapida = calcular_menor_caminho(
        grafo, 1, 3, criterio="tempo", pontos=pontos, vias=vias
    )

    assert rota_curta["vertices"] == [1, 2, 3]
    assert rota_rapida["vertices"] == [1, 4, 3]
    assert rota_rapida["arestas"] == [a_rapida_1, a_rapida_2]
    assert rota_rapida["tempo_total"] < rota_curta["tempo_total"]


def test_percurso_com_pontos_intermediarios_e_sentido_inverso(cenario_base):
    """Deve reconstruir curvas corretamente mesmo percorrendo aresta não direcionada ao contrário."""
    _, pontos = cenario_base
    grafo_nao_dir = Grafo(direcionado=False)

    for vid in (1, 2, 3):
        grafo_nao_dir.adicionar_vertice(
            vid, pontos[vid]["latitude"], pontos[vid]["longitude"]
        )

    # Aresta cadastrada no sentido 1 -> 2 passando pelo ponto intermediário 99
    grafo_nao_dir.adicionar_aresta(1, 2, 100.0, percurso=[1, 99, 2])
    grafo_nao_dir.adicionar_aresta(2, 3, 100.0, percurso=[2, 3])

    # Buscando no sentido inverso: 3 -> 1
    resultado = calcular_menor_caminho(grafo_nao_dir, 3, 1)

    assert resultado["vertices"] == [3, 2, 1]
    assert resultado["percurso_completo"] == [3, 2, 99, 1]


def test_respeita_mao_unica_em_grafo_direcionado(cenario_base):
    """Não deve percorrer aresta na contramão quando direcionado=True."""
    grafo, _ = cenario_base
    grafo.adicionar_aresta(1, 2, 100.0)

    assert calcular_menor_caminho(grafo, 1, 2) is not None
    assert calcular_menor_caminho(grafo, 2, 1) is None


def test_origem_igual_ao_destino(cenario_base):
    """Quando origem == destino, deve retornar custo zero e apenas o próprio vértice."""
    grafo, _ = cenario_base
    resultado = calcular_menor_caminho(grafo, 1, 1)

    assert resultado["distancia_total"] == 0.0
    assert resultado["vertices"] == [1]
    assert resultado["arestas"] == []
    assert resultado["percurso_completo"] == [1]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"origem": 999, "destino": 1},
        {"origem": 1, "destino": 999},
        {"origem": 1, "destino": 2, "criterio": "invalido"},
        {"origem": 1, "destino": 2, "criterio": "tempo"},
    ],
)
def test_validacoes_de_entrada(cenario_base, kwargs):
    """Deve lançar ValueError para vértices inexistentes ou parâmetros inválidos."""
    grafo, _ = cenario_base
    with pytest.raises(ValueError):
        calcular_menor_caminho(grafo, **kwargs)


def test_integracao_com_mapa_real():
    """Valida o fluxo completo carregando o JSON padrão se ele existir."""
    caminho_json = Path(__file__).resolve().parent.parent / "dados" / "bairro_teste.json"
    if not caminho_json.exists():
        pytest.skip("Arquivo dados/bairro_teste.json não disponível no ambiente")

    grafo, pontos, vias = carregar_mapa(caminho_json)
    assert len(grafo.vertices) > 0

    primeira_aresta = next(iter(grafo.arestas.values()))
    origem = primeira_aresta["origem"]
    destino = primeira_aresta["destino"]

    rota = calcular_menor_caminho(
        grafo, origem, destino, criterio="tempo", pontos=pontos, vias=vias
    )

    assert rota is not None
    assert rota["distancia_total"] >= 0.0
    assert rota["tempo_total"] >= 0.0
    assert rota["vertices"][0] == origem
    assert rota["vertices"][-1] == destino