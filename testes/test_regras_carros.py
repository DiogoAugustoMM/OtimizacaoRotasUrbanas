"""Sentidos de circulação, acesso e preservação dos percursos para carros."""

import json

import pytest

from mapas.conversor import carregar_mapa
from mapas.regras_carros import filtrar_vias_carros, motivo_exclusao_carros, sentido_da_via


def criar_via(identificador, nodes, **tags):
    return {
        "type": "way", "id": identificador, "nodes": nodes,
        "tags": {"highway": "residential", **tags},
    }


def carregar_exemplo(tmp_path, vias):
    ids = {identificador for via in vias for identificador in via["nodes"]}
    dados = {"elements": [
        *vias,
        *[
            {"type": "node", "id": i, "lat": -19.9 + i * 0.0001, "lon": -43.9}
            for i in sorted(ids)
        ],
    ]}
    caminho = tmp_path / "carros.json"
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return carregar_mapa(caminho)


@pytest.mark.parametrize("tags, esperado", [
    ({}, 0),
    ({"oneway": "yes"}, 1),
    ({"oneway": "true"}, 1),
    ({"oneway": "1"}, 1),
    ({"oneway": "-1"}, -1),
    ({"oneway": "no"}, 0),
    ({"oneway": "false"}, 0),
    ({"oneway": "0"}, 0),
    ({"junction": "roundabout"}, 1),
    ({"junction": "roundabout", "oneway": "no"}, 0),
    ({"highway": "motorway"}, 1),
    ({"highway": "motorway", "oneway": "no"}, 0),
    ({"oneway": "reversible"}, None),
    ({"oneway": "alternating"}, None),
    ({"oneway": "yes", "oneway:bicycle": "no"}, 1),
    ({"oneway": "yes", "oneway:motorcar": "no"}, 0),
    ({"oneway": "yes", "oneway:motor_vehicle": "-1"}, -1),
])
def test_interpretar_sentido(tags, esperado):
    assert sentido_da_via(tags) == esperado


@pytest.mark.parametrize("tags, permitida", [
    ({"highway": "residential"}, True),
    ({"highway": "service"}, True),
    ({"highway": "living_street"}, True),
    ({"highway": "footway"}, False),
    ({"highway": "cycleway", "bicycle": "yes"}, False),
    ({"highway": "steps", "motorcar": "yes"}, False),
    ({"highway": "construction", "motorcar": "yes"}, False),
    ({"highway": "proposed"}, False),
    ({"highway": "pedestrian", "motorcar": "yes"}, True),
    ({"highway": "footway", "access": "yes"}, False),
    ({"highway": "residential", "access": "private"}, False),
    ({"highway": "residential", "motor_vehicle": "no"}, False),
    ({"highway": "residential", "motorcar": "no", "access": "yes"}, False),
    ({"highway": "residential", "motorcar": "yes", "access": "private"}, True),
    ({"highway": "residential", "motor_vehicle": "yes", "vehicle": "no"}, True),
    ({"highway": "residential", "vehicle": "no", "access": "yes"}, False),
    ({"highway": "residential", "access": "destination"}, False),
    ({"highway": "service", "access": "customers"}, False),
    ({"highway": "residential", "access": "permissive"}, True),
    ({"highway": "residential", "motorcar": "designated"}, True),
    ({"highway": "residential", "motorcar": "desconhecido"}, False),
    ({"highway": "residential", "oneway": "reversible"}, False),
    ({"highway": "residential", "oneway:conditional": "yes @ (Mo-Fr)"}, False),
    ({"highway": "residential", "motor_vehicle:conditional": "no @ (Mo-Fr)"}, False),
    ({"highway": "residential", "vehicle:forward": "no"}, False),
    ({"highway": "residential", "area": "yes"}, False),
    ({"building": "yes"}, False),
])
def test_filtrar_acesso_e_tipo_de_via(tags, permitida):
    assert (motivo_exclusao_carros(tags) is None) == permitida


def test_filtro_retorna_motivos_sem_alterar_vias():
    vias = {
        10: {"nodes": [1, 2], "tags": {"highway": "residential"}},
        20: {"nodes": [2, 3], "tags": {"highway": "residential", "access": "private"}},
    }
    permitidas, excluidas = filtrar_vias_carros(vias)
    assert set(permitidas) == {10}
    assert "private" in excluidas[20]
    assert set(vias) == {10, 20}


@pytest.mark.parametrize("oneway, percurso", [("yes", [30, 20, 10]), ("-1", [10, 20, 30])])
def test_mao_unica_usa_ordem_dos_nodes_e_nao_ordem_dos_ids(tmp_path, oneway, percurso):
    grafo, _, _ = carregar_exemplo(tmp_path, [criar_via(100, [30, 20, 10], oneway=oneway)])
    assert grafo.direcionado
    assert len(grafo.arestas) == 1
    aresta = grafo.arestas[0]
    assert aresta["percurso"] == percurso
    assert aresta["origem"] == percurso[0]
    assert aresta["destino"] == percurso[-1]
    assert grafo.obter_vizinhos(percurso[-1]) == []
    assert [(s["origem"], s["destino"]) for s in aresta["segmentos"]] == list(zip(percurso, percurso[1:]))


def test_mao_dupla_cria_dois_arcos_com_percursos_inversos_e_mesmo_peso(tmp_path):
    grafo, _, _ = carregar_exemplo(tmp_path, [criar_via(100, [1, 2, 3])])
    assert len(grafo.arestas) == 2
    ida, volta = grafo.arestas.values()
    assert ida["percurso"] == [1, 2, 3]
    assert volta["percurso"] == [3, 2, 1]
    assert ida["distancia_metros"] == pytest.approx(volta["distancia_metros"])


def test_mudanca_de_mao_em_ponto_com_dois_vizinhos_preserva_vertice(tmp_path):
    grafo, _, _ = carregar_exemplo(tmp_path, [
        criar_via(100, [1, 2], oneway="yes"),
        criar_via(200, [3, 2], oneway="yes"),
    ])
    assert set(grafo.vertices) == {1, 2, 3}
    assert {(a["origem"], a["destino"]) for a in grafo.arestas.values()} == {(1, 2), (3, 2)}
    assert grafo.obter_vizinhos(2) == []


def test_mudanca_de_mao_dupla_para_unica(tmp_path):
    grafo, _, _ = carregar_exemplo(tmp_path, [
        criar_via(100, [1, 2]), criar_via(200, [2, 3], oneway="yes"),
    ])
    assert {(a["origem"], a["destino"]) for a in grafo.arestas.values()} == {(1, 2), (2, 1), (2, 3)}


def test_rotatoria_respeita_sentido_do_anel_nas_conexoes(tmp_path):
    grafo, _, _ = carregar_exemplo(tmp_path, [
        criar_via(100, [1, 2, 3, 4, 1], junction="roundabout"),
        criar_via(200, [5, 1]), criar_via(300, [6, 3]),
    ])
    anel = [a for a in grafo.arestas.values() if a["segmentos"][0]["vias"] == [100]]
    assert [a["percurso"] for a in anel] == [[1, 2, 3], [3, 4, 1]]
    assert len(grafo.arestas) == 6  # Dois arcos do anel e quatro das aproximações.


def test_circuito_isolado_nao_desaparece(tmp_path):
    grafo, _, _ = carregar_exemplo(tmp_path, [
        criar_via(100, [1, 2, 3, 1], junction="roundabout"),
    ])
    assert set(grafo.vertices) == {1}
    assert len(grafo.arestas) == 1
    assert grafo.arestas[0]["percurso"] == [1, 2, 3, 1]
    assert grafo.arestas[0]["distancia_metros"] > 0


def test_caminhos_paralelos_entre_mesmos_vertices_sao_preservados(tmp_path):
    grafo, _, _ = carregar_exemplo(tmp_path, [
        criar_via(100, [1, 2, 4]), criar_via(200, [1, 3, 4]),
    ])
    assert set(grafo.vertices) == {1, 4}
    assert len(grafo.arestas) == 4
    assert len(grafo.obter_vizinhos(1)) == 2
    assert {tuple(a["percurso"]) for a in grafo.arestas.values()} == {
        (1, 2, 4), (4, 2, 1), (1, 3, 4), (4, 3, 1),
    }


def test_segmentos_sobrepostos_guardam_apenas_vias_compativeis_com_o_sentido(tmp_path):
    grafo, _, _ = carregar_exemplo(tmp_path, [
        criar_via(100, [1, 2], oneway="yes", name="Ida"),
        criar_via(200, [2, 1], oneway="yes", name="Volta"),
    ])
    assert len(grafo.arestas) == 2
    por_origem = {a["origem"]: a for a in grafo.arestas.values()}
    assert por_origem[1]["segmentos"][0]["vias"] == [100]
    assert por_origem[2]["segmentos"][0]["vias"] == [200]


def test_filtragem_ocorre_antes_de_identificar_cruzamentos(tmp_path):
    grafo, pontos, vias = carregar_exemplo(tmp_path, [
        criar_via(100, [1, 2, 3]),
        criar_via(200, [4, 2, 5], highway="cycleway"),
    ])
    assert set(vias) == {100}
    assert set(grafo.vertices) == {1, 3}
    assert set(pontos) == {1, 2, 3, 4, 5}
    assert grafo.arestas[0]["percurso"] == [1, 2, 3]


def test_arquivo_sem_vias_para_carros_informa_problema(tmp_path):
    with pytest.raises(ValueError, match="Nenhuma via compatível"):
        carregar_exemplo(tmp_path, [criar_via(100, [1, 2], highway="steps")])
