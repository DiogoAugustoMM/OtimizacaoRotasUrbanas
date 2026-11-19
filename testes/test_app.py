"""Integração da seleção de pontos com o estado da interface Streamlit.

Simula as respostas de clique do componente Folium; não testa seu JavaScript.
"""

import json
import os

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("folium")
from streamlit.testing.v1 import AppTest

import app


def salvar_mapa(caminho, inicio=1):
    dados = {"elements": [
        {"type": "way", "id": 10, "nodes": [inicio, inicio + 1],
         "tags": {"highway": "residential", "maxspeed": "30"}},
        {"type": "node", "id": inicio, "lat": 0, "lon": 0},
        {"type": "node", "id": inicio + 1, "lat": 0, "lon": 0.01},
    ]}
    caminho.write_text(json.dumps(dados), encoding="utf-8")


@pytest.fixture
def interface(tmp_path, monkeypatch):
    salvar_mapa(tmp_path / "a.json")
    monkeypatch.setattr(app, "PASTA_DADOS", tmp_path)
    app.carregar.clear()

    def componente_simulado(*args, **kwargs):
        eventos = app.st.session_state.get("_eventos_teste", {})
        return {"last_clicked": eventos.get(kwargs["key"])}

    monkeypatch.setattr(app, "st_folium", componente_simulado)
    teste = AppTest.from_string("import app\napp.main()", default_timeout=30).run()
    assert not teste.exception
    yield teste, tmp_path
    app.carregar.clear()


def clicar(teste, longitude, latitude=0):
    chave = f"mapa_{teste.session_state['geracao_mapa']}"
    eventos = dict(teste.session_state.get("_eventos_teste", {}))
    eventos[chave] = {"lat": latitude, "lng": longitude}
    teste.session_state["_eventos_teste"] = eventos
    teste.run()
    assert not teste.exception


def test_cliques_criam_pontos_no_meio_da_rua_e_comparacao_e_reutilizada(interface, monkeypatch):
    teste, _ = interface
    chamadas = []
    comparar = app.comparar_rotas

    def comparar_contando(*args, **kwargs):
        chamadas.append(1)
        return comparar(*args, **kwargs)

    monkeypatch.setattr(app, "comparar_rotas", comparar_contando)
    clicar(teste, 0.002)
    clicar(teste, 0.008)
    origem, destino = teste.session_state["origem"], teste.session_state["destino"]
    grafo, pontos = teste.session_state["preparacao"]
    assert origem < 0 and destino < 0
    assert pontos[origem]["longitude"] == pytest.approx(0.002)
    assert pontos[destino]["longitude"] == pytest.approx(0.008)
    assert teste.metric[0].value == "667 m"
    assert len(chamadas) == 1

    teste.radio[0].set_value("Mais rápida (Tempo)").run()
    teste.checkbox[0].check().run()
    assert not teste.exception
    assert len(chamadas) == 1
    assert teste.session_state["preparacao"][0] is grafo


def test_limpar_permite_selecionar_novamente_no_mesmo_local(interface):
    teste, _ = interface
    clicar(teste, 0.002)
    clicar(teste, 0.008)
    teste.button[0].click().run()
    assert not teste.exception
    assert teste.session_state["origem"] is None
    assert teste.session_state["destino"] is None
    assert teste.session_state["preparacao"] is None
    clicar(teste, 0.008)
    assert teste.session_state["origem"] is not None
    assert teste.session_state["destino"] is None


def test_terceiro_clique_inicia_outra_rota_sem_mudar_o_componente(interface):
    teste, _ = interface
    clicar(teste, 0.002)
    clicar(teste, 0.008)
    geracao = teste.session_state["geracao_mapa"]
    clicar(teste, 0.004)
    assert teste.session_state["destino"] is None
    assert teste.session_state["comparacao"] is None
    assert teste.session_state["geracao_mapa"] == geracao
    origem = teste.session_state["origem"]
    assert teste.session_state["preparacao"][1][origem]["longitude"] == pytest.approx(0.004)


def test_trocar_de_mapa_descarta_os_pontos_temporarios(interface):
    teste, pasta = interface
    clicar(teste, 0.002)
    clicar(teste, 0.008)
    salvar_mapa(pasta / "b.json", inicio=101)
    teste.run()
    teste.selectbox[0].select(pasta / "b.json").run()
    assert not teste.exception
    assert teste.session_state["origem"] is None
    assert teste.session_state["destino"] is None
    assert teste.session_state["preparacao"] is None


def test_substituir_arquivo_no_mesmo_caminho_invalida_cache_e_selecao(interface):
    teste, pasta = interface
    clicar(teste, 0.002)
    caminho = pasta / "a.json"
    antes = caminho.stat()
    salvar_mapa(caminho, inicio=101)
    os.utime(caminho, ns=(antes.st_atime_ns, antes.st_mtime_ns + 1_000_000_000))
    teste.run()
    assert not teste.exception
    assert teste.session_state["origem"] is None
    dados = caminho.stat()
    grafo, *_ = app.carregar(str(caminho), (dados.st_mtime_ns, dados.st_size))
    assert set(grafo.vertices) == {101, 102}
