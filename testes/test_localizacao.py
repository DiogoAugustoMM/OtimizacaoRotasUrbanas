"""Seleção em trechos, divisão das arestas e integração com os algoritmos existentes."""

from copy import deepcopy

import pytest

from grafos.grafo import Grafo
from grafos.dijkstra import calcular_menor_caminho
from mapas.conversor import calcular_distancia_metros
from mapas.localizacao import (
    criar_indice_segmentos, inserir_pontos_temporarios, localizar_ponto_na_via,
)
from resultados import comparar_rotas
from visualizacao.mapa import coordenadas_da_rota

 
def adicionar_trecho(grafo, pontos, percurso, id_via=10):
    segmentos = [{"origem": a, "destino": b, "vias": [id_via]}
                 for a, b in zip(percurso, percurso[1:])]
    distancia = sum(calcular_distancia_metros(pontos[a], pontos[b])
                    for a, b in zip(percurso, percurso[1:]))
    return grafo.adicionar_aresta(
        percurso[0], percurso[-1], distancia, percurso=percurso, segmentos=segmentos,
    )


def criar_rua(mao_dupla=True, curva=False):
    grafo = Grafo(direcionado=True)
    pontos = {
        1: {"latitude": 0.0, "longitude": 0.0},
        2: {"latitude": 0.0, "longitude": 0.01},
    }
    percurso = [1, 2]
    if curva:
        pontos[99] = {"latitude": 0.005, "longitude": 0.005}
        percurso = [1, 99, 2]
    for i in (1, 2):
        grafo.adicionar_vertice(i, pontos[i]["latitude"], pontos[i]["longitude"])
    adicionar_trecho(grafo, pontos, percurso)
    if mao_dupla:
        adicionar_trecho(grafo, pontos, list(reversed(percurso)))
    return grafo, pontos, {10: {"tags": {"highway": "residential", "maxspeed": "30"}}}


def preparar(grafo, pontos, cliques):
    indice = criar_indice_segmentos(grafo, pontos)
    locais = [localizar_ponto_na_via(indice, pontos, lat, lon) for lat, lon in cliques]
    return inserir_pontos_temporarios(grafo, pontos, locais)


def test_projeta_no_meio_da_rua_em_vez_de_escolher_cruzamento_distante():
    grafo, pontos, _ = criar_rua()
    indice = criar_indice_segmentos(grafo, pontos)
    assert len(indice["segmentos"]) == 1  # Ida e volta compartilham o índice.
    local = localizar_ponto_na_via(indice, pontos, 0.001, 0.004)
    assert local["latitude"] == pytest.approx(0)
    assert local["longitude"] == pytest.approx(0.004)
    assert local["fracao"] == pytest.approx(0.4)
    assert local["id_ponto"] is None
    assert local["distancia_clique_metros"] == pytest.approx(111.1949, rel=1e-5)


@pytest.mark.parametrize("cliques", [
    [(0, 0.002), (0, 0.008)], [(0, 0.008), (0, 0.002)],
])
def test_dois_pontos_na_mesma_aresta_tem_rota_direta_nos_dois_sentidos(cliques):
    grafo, pontos, vias = criar_rua()
    consulta, coordenadas, ids = preparar(grafo, pontos, cliques)
    assert len(consulta.vertices) == 4
    assert len(consulta.arestas) == 6
    assert all(i < 0 for i in ids)
    comparacao = comparar_rotas(consulta, *ids, coordenadas, vias)
    rota = comparacao["rota_distancia"]
    assert rota["vertices"] == ids
    assert len(rota["arestas"]) == 1
    assert rota["distancia_total"] == pytest.approx(grafo.arestas[0]["distancia_metros"] * 0.6)
    assert rota["tempo_total"] == pytest.approx(rota["distancia_total"] / (30 / 3.6))
    assert comparacao["mesmo_trajeto"]
    assert coordenadas_da_rota(consulta, coordenadas, rota["arestas"]) == [
        (coordenadas[i]["latitude"], coordenadas[i]["longitude"]) for i in ids
    ]


def test_mao_unica_nao_cria_contramao_ao_dividir():
    grafo, pontos, _ = criar_rua(mao_dupla=False)
    consulta, _, (a, b) = preparar(grafo, pontos, [(0, 0.002), (0, 0.008)])
    assert len(consulta.arestas) == 3
    assert calcular_menor_caminho(consulta, a, b) is not None
    assert calcular_menor_caminho(consulta, b, a) is None


def test_nao_modifica_grafo_pontos_ou_adjacencias_originais():
    grafo, pontos, _ = criar_rua()
    estado_grafo = deepcopy(grafo.__dict__)
    estado_pontos = deepcopy(pontos)
    consulta, _, ids = preparar(grafo, pontos, [(0, 0.004), (0, 0.006)])
    assert consulta is not grafo
    assert grafo.__dict__ == estado_grafo
    assert pontos == estado_pontos
    assert not set(ids).intersection(pontos)


def test_clique_em_vertice_existente_reutiliza_o_grafo():
    grafo, pontos, _ = criar_rua()
    consulta, coordenadas, ids = preparar(grafo, pontos, [(0, 0), (0, 0.01)])
    assert ids == [1, 2]
    assert consulta is grafo
    assert coordenadas is pontos


def test_ponto_intermediario_existente_e_promovido_sem_duplicar_coordenadas():
    grafo, pontos, _ = criar_rua(curva=True)
    consulta, coordenadas, ids = preparar(grafo, pontos, [(0.005, 0.005)])
    assert ids == [99]
    assert set(consulta.vertices) == {1, 2, 99}
    assert set(coordenadas) == set(pontos)
    assert len(consulta.arestas) == 4


def test_cliques_diferentes_projetados_no_mesmo_local_reutilizam_id():
    grafo, pontos, _ = criar_rua()
    consulta, _, ids = preparar(grafo, pontos, [(0.001, 0.005), (-0.001, 0.005)])
    assert ids[0] == ids[1]
    assert len(consulta.vertices) == 3
    assert len(consulta.arestas) == 4


def test_preserva_curvas_pesos_e_vias_dos_segmentos():
    grafo, pontos, _ = criar_rua(curva=True)
    consulta, coordenadas, ids = preparar(grafo, pontos, [(0.0025, 0.0025), (0.0025, 0.0075)])
    rota = calcular_menor_caminho(consulta, *ids)
    assert rota["percurso_completo"] == [ids[0], 99, ids[1]]
    assert rota["distancia_total"] == pytest.approx(grafo.arestas[0]["distancia_metros"] / 2, rel=1e-6)
    assert all(s["vias"] == [10] for a in consulta.arestas.values() for s in a["segmentos"])
    for aresta in consulta.arestas.values():
        assert [(s["origem"], s["destino"]) for s in aresta["segmentos"]] == list(zip(aresta["percurso"], aresta["percurso"][1:]))
    assert coordenadas[99] == pontos[99]


def test_linhas_que_se_cruzam_sem_node_compartilhado_nao_sao_conectadas():
    grafo = Grafo(direcionado=True)
    pontos = {
        1: {"latitude": 0, "longitude": -0.01},
        2: {"latitude": 0, "longitude": 0.01},
        3: {"latitude": -0.01, "longitude": 0},
        4: {"latitude": 0.01, "longitude": 0},
    }
    for i, p in pontos.items():
        grafo.adicionar_vertice(i, p["latitude"], p["longitude"])
    for percurso in ([1, 2], [2, 1], [3, 4], [4, 3]):
        adicionar_trecho(grafo, pontos, percurso)
    consulta, _, ids = preparar(grafo, pontos, [(0, 0), (0.005, 0)])
    assert calcular_menor_caminho(consulta, *ids) is None


def test_circuito_fechado_preserva_circulacao_ao_dividir():
    grafo = Grafo(direcionado=True)
    pontos = {1: {"latitude": 0, "longitude": 0},
              2: {"latitude": 0, "longitude": 0.01},
              3: {"latitude": 0.01, "longitude": 0}}
    grafo.adicionar_vertice(1, 0, 0)
    adicionar_trecho(grafo, pontos, [1, 2, 3, 1])
    consulta, _, ids = preparar(grafo, pontos, [(0, 0.002), (0, 0.008)])
    ida = calcular_menor_caminho(consulta, *ids)
    volta = calcular_menor_caminho(consulta, *reversed(ids))
    assert ida["vertices"] == ids
    assert volta["vertices"] == [ids[1], 1, ids[0]]
    assert volta["distancia_total"] > ida["distancia_total"]


@pytest.mark.parametrize("clique", [(float("nan"), 0), (0, float("inf")), (91, 0), (0, 181), (True, 0)])
def test_coordenadas_invalidas(clique):
    grafo, pontos, _ = criar_rua()
    with pytest.raises(ValueError, match="latitude e longitude válidas"):
        localizar_ponto_na_via(criar_indice_segmentos(grafo, pontos), pontos, *clique)


def test_grafo_sem_trechos():
    with pytest.raises(ValueError, match="não possui trechos"):
        criar_indice_segmentos(Grafo(), {})
