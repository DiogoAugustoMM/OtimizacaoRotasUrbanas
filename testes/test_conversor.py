"""Entrada de arquivos e conversão integrada, sem rede ou dados locais do bairro."""

import json
from copy import deepcopy

import pytest

from mapas.conversor import carregar_dados, carregar_mapa, validar_dados


@pytest.fixture
def dados_mapa():
    # A via aparece antes dos pontos, e 5 é intermediário entre 1 e 2.
    return {"elements": [
        {"type": "way", "id": 10, "nodes": [1, 5, 2, 3], "tags": {"name": "Rua A", "highway": "residential"}},
        {"type": "way", "id": 20, "nodes": [2, 4], "tags": {"name": "Rua B", "highway": "residential"}},
        *[
            {"type": "node", "id": i, "lat": -19.9 + i * 0.001, "lon": -43.9}
            for i in range(1, 6)
        ],
    ]}


def salvar_json(tmp_path, dados, encoding="utf-8"):
    caminho = tmp_path / "mapa.json"
    caminho.write_text(json.dumps(dados), encoding=encoding)
    return caminho


def test_carregar_mapa_entrega_grafo_pontos_e_vias_sem_imprimir(tmp_path, dados_mapa, capsys):
    caminho = salvar_json(tmp_path, dados_mapa)
    grafo, pontos, vias = carregar_mapa(caminho)

    assert set(grafo.vertices) == {1, 2, 3, 4}
    assert grafo.direcionado
    assert len(grafo.arestas) == 6
    assert set(pontos) == {1, 2, 3, 4, 5}
    assert vias[10]["tags"]["name"] == "Rua A"
    aresta = next(ar for ar in grafo.arestas.values() if ar["origem"] == 1)
    assert aresta["percurso"] == [1, 5, 2]
    assert aresta["distancia_metros"] > 0
    assert aresta["segmentos"][0]["vias"] == [10]
    assert grafo.obter_vizinhos(1)[0]["destino"] == 2
    assert any(conexao["destino"] == 1 for conexao in grafo.obter_vizinhos(2))
    assert capsys.readouterr().out == ""


def test_leitura_aceita_bom_e_nao_modifica_dados(tmp_path, dados_mapa):
    original = deepcopy(dados_mapa)
    validar_dados(dados_mapa)
    assert dados_mapa == original
    assert carregar_dados(salvar_json(tmp_path, dados_mapa, "utf-8-sig")) == original


def test_arquivo_ausente(tmp_path):
    with pytest.raises(FileNotFoundError, match="Arquivo não encontrado"):
        carregar_mapa(tmp_path / "ausente.json")


def test_json_invalido(tmp_path):
    caminho = tmp_path / "invalido.json"
    caminho.write_text('{"elements": [}', encoding="utf-8")
    with pytest.raises(ValueError, match="JSON inválido.*linha.*coluna"):
        carregar_mapa(caminho)


def test_codificacao_invalida(tmp_path):
    caminho = tmp_path / "invalido.json"
    caminho.write_bytes(b"\xff\xfe")
    with pytest.raises(ValueError, match="UTF-8"):
        carregar_mapa(caminho)


def test_pasta_em_vez_de_arquivo(tmp_path):
    with pytest.raises(OSError, match="Não foi possível ler"):
        carregar_mapa(tmp_path)


@pytest.mark.parametrize("dados, mensagem", [
    ([], "objeto"),
    ({"type": "FeatureCollection", "features": []}, "GeoJSON"),
    ({}, "lista 'elements'"),
    ({"elements": {}}, "lista 'elements'"),
    ({"elements": []}, "não contém vias"),
    ({"elements": [42]}, "posição 0"),
    ({"elements": [{}]}, "Tipo de elemento inválido"),
    ({"elements": [], "remark": "runtime error: Query timed out"}, "problema na consulta"),
])
def test_formato_invalido_interrompe_carregamento(tmp_path, dados, mensagem):
    with pytest.raises(ValueError, match=mensagem):
        carregar_mapa(salvar_json(tmp_path, dados))


@pytest.mark.parametrize("campo, valor", [
    ("lat", 91), ("lat", -91), ("lon", 181), ("lon", -181),
    ("lat", None), ("lat", True), ("lat", "-19.9"),
    ("lat", float("nan")), ("lon", float("inf")),
])
def test_coordenadas_invalidas(dados_mapa, campo, valor):
    dados_mapa["elements"][2][campo] = valor
    with pytest.raises(ValueError, match="Coordenada.*ponto 1"):
        validar_dados(dados_mapa)


def test_coordenada_ausente(dados_mapa):
    del dados_mapa["elements"][2]["lat"]
    with pytest.raises(ValueError, match="Coordenada 'lat'"):
        validar_dados(dados_mapa)


@pytest.mark.parametrize("nodes", [None, "1,2", [], [1], [1, "2"], [1, True]])
def test_lista_de_pontos_da_via_invalida(dados_mapa, nodes):
    dados_mapa["elements"][0]["nodes"] = nodes
    with pytest.raises(ValueError, match="via 10.*nodes"):
        validar_dados(dados_mapa)


def test_ponto_referenciado_ausente(dados_mapa):
    dados_mapa["elements"][0]["nodes"].append(999)
    with pytest.raises(ValueError, match="via 10.*ponto ausente 999"):
        validar_dados(dados_mapa)


@pytest.mark.parametrize("indice, mensagem", [(0, "via duplicado"), (2, "ponto duplicado")])
def test_ids_duplicados(dados_mapa, indice, mensagem):
    dados_mapa["elements"].append(deepcopy(dados_mapa["elements"][indice]))
    with pytest.raises(ValueError, match=mensagem):
        validar_dados(dados_mapa)


@pytest.mark.parametrize("identificador", [None, "10", True])
def test_id_invalido(dados_mapa, identificador):
    dados_mapa["elements"][0]["id"] = identificador
    with pytest.raises(ValueError, match="ID inteiro"):
        validar_dados(dados_mapa)


@pytest.mark.parametrize("tags", [None, [], {"name": 42}])
def test_tags_invalidas(dados_mapa, tags):
    dados_mapa["elements"][0]["tags"] = tags
    with pytest.raises(ValueError, match="tags de way 10"):
        validar_dados(dados_mapa)


def test_relacoes_nao_sao_convertidas_e_ids_de_tipos_distintos_podem_coincidir(dados_mapa):
    dados_mapa["elements"][0]["id"] = 1
    dados_mapa["elements"].append({"type": "relation", "id": 1})
    validar_dados(dados_mapa)
