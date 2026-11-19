"""Verifica a tradução entre cliques, grafo e coordenadas usada pela interface."""

import pytest

from grafos.grafo import Grafo
from visualizacao.mapa import (
    coordenadas_da_rota,
    coordenadas_do_percurso,
    criar_mapa,
    geometria_das_ruas,
    limites_do_grafo,
    vertice_mais_proximo,
)


def criar_cenario():
    """Três cruzamentos em linha reta, ligados por duas arestas.

    A primeira aresta tem um ponto intermediário (99) que não é vértice.
    """
    grafo = Grafo()
    pontos = {
        1: {"latitude": -19.920, "longitude": -43.940},
        99: {"latitude": -19.921, "longitude": -43.935},
        2: {"latitude": -19.920, "longitude": -43.930},
        3: {"latitude": -19.920, "longitude": -43.920},
    }
    for identificador in (1, 2, 3):
        ponto = pontos[identificador]
        grafo.adicionar_vertice(identificador, ponto["latitude"], ponto["longitude"])
    primeira = grafo.adicionar_aresta(1, 2, 1100, percurso=[1, 99, 2])
    segunda = grafo.adicionar_aresta(2, 3, 1045, percurso=[2, 3])
    return grafo, pontos, primeira, segunda


def test_clique_vira_o_vertice_mais_proximo():
    grafo, _, _, _ = criar_cenario()
    assert vertice_mais_proximo(grafo, -19.9201, -43.9399) == 1
    assert vertice_mais_proximo(grafo, -19.9199, -43.9201) == 3
    assert vertice_mais_proximo(grafo, -19.920, -43.930) == 2


def test_clique_longe_do_grafo_ainda_escolhe_o_vertice_mais_proximo():
    grafo, _, _, _ = criar_cenario()
    assert vertice_mais_proximo(grafo, -10.0, -43.941) == 1


def test_grafo_sem_vertices_nao_tem_vertice_mais_proximo():
    with pytest.raises(ValueError):
        vertice_mais_proximo(Grafo(), -19.9, -43.9)


def test_percurso_vira_pares_de_latitude_e_longitude():
    _, pontos, _, _ = criar_cenario()
    assert coordenadas_do_percurso(pontos, [1, 99, 2]) == [
        (-19.920, -43.940),
        (-19.921, -43.935),
        (-19.920, -43.930),
    ]


def test_rota_junta_as_arestas_sem_repetir_o_cruzamento_de_ligacao():
    grafo, pontos, primeira, segunda = criar_cenario()
    coordenadas = coordenadas_da_rota(grafo, pontos, [primeira, segunda])
    assert coordenadas == [
        (-19.920, -43.940),
        (-19.921, -43.935),
        (-19.920, -43.930),  # aparece uma vez, apesar de fechar uma aresta e abrir a outra
        (-19.920, -43.920),
    ]


def test_rota_vazia_nao_gera_coordenadas():
    grafo, pontos, _, _ = criar_cenario()
    assert coordenadas_da_rota(grafo, pontos, []) == []


def test_limites_cobrem_todos_os_vertices():
    grafo, _, _, _ = criar_cenario()
    assert limites_do_grafo(grafo) == [[-19.920, -43.940], [-19.920, -43.920]]


def test_criar_mapa_com_rota_origem_e_destino_nao_falha():
    folium = pytest.importorskip("folium")
    grafo, pontos, primeira, segunda = criar_cenario()
    mapa = criar_mapa(grafo, pontos, [primeira, segunda], origem=1, destino=3,
                      mostrar_ruas=True)
    assert isinstance(mapa, folium.Map)


def test_geometria_agrupa_ruas_sem_duplicar_ida_e_volta():
    grafo, pontos, _, _ = criar_cenario()
    grafo.adicionar_aresta(2, 1, 1100, percurso=[2, 99, 1])
    geometria = geometria_das_ruas(grafo, pontos)
    assert geometria["type"] == "MultiLineString"
    assert len(geometria["coordinates"]) == 2
    # GeoJSON utiliza longitude antes de latitude.
    assert geometria["coordinates"][0][0] == [-43.940, -19.920]


def test_mostrar_ruas_usa_uma_camada_agrupada():
    folium = pytest.importorskip("folium")
    grafo, pontos, _, _ = criar_cenario()
    geometria = geometria_das_ruas(grafo, pontos)
    mapa = criar_mapa(grafo, pontos, mostrar_ruas=True, geometria_ruas=geometria)
    assert sum(isinstance(c, folium.GeoJson) for c in mapa._children.values()) == 1
