"""Verifica conexões, pesos e preservação dos dados na estrutura própria."""

import pytest

from grafos.grafo import Grafo
from mapas.conversor import montar_grafo


def criar_grafo(direcionado=False):
    grafo = Grafo(direcionado=direcionado)
    for identificador in (1, 2, 3):
        grafo.adicionar_vertice(identificador, -19.9, -43.9)
    return grafo


def test_arestas_paralelas_e_consulta_nos_dois_sentidos():
    grafo = criar_grafo()
    primeira = grafo.adicionar_aresta(1, 2, 150)
    segunda = grafo.adicionar_aresta(1, 2, 100, percurso=[1, 99, 2])
    grafo.adicionar_aresta(2, 3, 50)

    assert len(grafo.arestas) == 3
    assert grafo.obter_vizinhos(1) == [
        {"destino": 2, "distancia_metros": 150, "id_aresta": primeira},
        {"destino": 2, "distancia_metros": 100, "id_aresta": segunda},
    ]
    assert grafo.obter_vizinhos(2)[0] == {
        "destino": 1, "distancia_metros": 150, "id_aresta": primeira,
    }
    assert grafo.arestas[segunda]["percurso"] == [1, 99, 2]
    assert 99 not in grafo.vertices


def test_grafo_direcionado_nao_cria_conexao_inversa():
    grafo = criar_grafo(direcionado=True)
    grafo.adicionar_aresta(1, 2, 150)
    assert grafo.obter_vizinhos(1)[0]["destino"] == 2
    assert grafo.obter_vizinhos(2) == []


def test_laco_aparece_uma_vez_e_vertice_isolado_nao_tem_conexoes():
    grafo = criar_grafo()
    id_aresta = grafo.adicionar_aresta(1, 1, 200, percurso=[1, 99, 1])
    assert grafo.adjacencias[1] == [id_aresta]
    assert grafo.obter_vizinhos(1)[0]["destino"] == 1
    assert grafo.obter_vizinhos(3) == []


@pytest.mark.parametrize("distancia", [-1, float("nan"), float("inf")])
def test_distancia_invalida_nao_altera_grafo(distancia):
    grafo = criar_grafo()
    with pytest.raises(ValueError):
        grafo.adicionar_aresta(1, 2, distancia)
    assert grafo.arestas == {}
    assert grafo.adjacencias == {1: [], 2: [], 3: []}


def test_rejeita_extremos_ausentes_percurso_invalido_e_vertice_duplicado():
    grafo = criar_grafo()
    with pytest.raises(ValueError):
        grafo.adicionar_aresta(1, 4, 10)
    with pytest.raises(ValueError):
        grafo.adicionar_aresta(1, 2, 10, percurso=[2, 1])
    with pytest.raises(ValueError):
        grafo.adicionar_vertice(1, 0, 0)
    with pytest.raises(ValueError):
        grafo.obter_vizinhos(4)
    assert grafo.vertices[1]["latitude"] == -19.9
    assert grafo.arestas == {}


def test_integracao_preserva_geometria_e_referencias_sem_compartilhar_listas():
    vertices = {
        1: {"latitude": -19.9, "longitude": -43.9},
        2: {"latitude": -19.8, "longitude": -43.8},
    }
    arestas = [{
        "origem": 1,
        "destino": 2,
        "distancia_metros": 150.5,
        "percurso": [1, 99, 2],
        "segmentos": [
            {"origem": 1, "destino": 99, "vias": [500]},
            {"origem": 99, "destino": 2, "vias": [501]},
        ],
    }]
    grafo = montar_grafo(vertices, arestas)
    assert grafo.vertices == vertices
    assert list(grafo.arestas.values()) == arestas
    assert grafo.obter_vizinhos(2)[0]["distancia_metros"] == 150.5

    arestas[0]["percurso"].append(7)
    arestas[0]["segmentos"][0]["vias"].append(999)
    vertices[1]["latitude"] = 0
    assert grafo.arestas[0]["percurso"] == [1, 99, 2]
    assert grafo.arestas[0]["segmentos"][0]["vias"] == [500]
    assert grafo.vertices[1]["latitude"] == -19.9
