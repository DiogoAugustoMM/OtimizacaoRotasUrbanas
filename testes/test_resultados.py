
import resultados


def test_comparar_rotas_diferentes(monkeypatch):
    respostas = {
        "distancia": {
            "arestas": [0, 1],
            "distancia_total": 1000.0,
            "tempo_total": 180.0,
        },
        "tempo": {
            "arestas": [2, 3],
            "distancia_total": 1200.0,
            "tempo_total": 120.0,
        },
    }

    chamadas = []

    def dijkstra_simulado(grafo, origem, destino, criterio, pontos, vias):
        chamadas.append((origem, destino, criterio))
        return respostas[criterio]

    monkeypatch.setattr(
        resultados, "calcular_menor_caminho", dijkstra_simulado
    )

    comparacao = resultados.comparar_rotas(None, 1, 4, {}, {})

    assert chamadas == [
        (1, 4, "distancia"),
        (1, 4, "tempo"),
    ]
    assert comparacao["rota_distancia"] == respostas["distancia"]
    assert comparacao["rota_tempo"] == respostas["tempo"]
    assert comparacao["mesmo_trajeto"] is False
    assert comparacao["distancia_adicional_metros"] == 200.0
    assert comparacao["tempo_economizado_segundos"] == 60.0


def test_comparar_rotas_iguais(monkeypatch):
    rota = {
        "arestas": [0, 1],
        "distancia_total": 1000.0,
        "tempo_total": 120.0,
    }

    monkeypatch.setattr(
        resultados,
        "calcular_menor_caminho",
        lambda *args, **kwargs: rota,
    )

    comparacao = resultados.comparar_rotas(None, 1, 4, {}, {})

    assert comparacao["mesmo_trajeto"] is True
    assert comparacao["distancia_adicional_metros"] == 0.0
    assert comparacao["tempo_economizado_segundos"] == 0.0


def test_comparar_rotas_sem_caminho(monkeypatch):
    monkeypatch.setattr(
        resultados,
        "calcular_menor_caminho",
        lambda *args, **kwargs: None,
    )

    comparacao = resultados.comparar_rotas(None, 1, 4, {}, {})

    assert comparacao is None
