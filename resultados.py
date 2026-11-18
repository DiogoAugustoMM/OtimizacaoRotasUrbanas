from grafos.dijkstra import calcular_menor_caminho


def comparar_rotas(grafo, origem, destino, pontos, vias):
    """Compara as rotas de menor distância e menor tempo."""

    rota_distancia = calcular_menor_caminho(
        grafo,
        origem,
        destino,
        criterio="distancia",
        pontos=pontos,
        vias=vias,
    )

    rota_tempo = calcular_menor_caminho(
        grafo,
        origem,
        destino,
        criterio="tempo",
        pontos=pontos,
        vias=vias,
    )

    if rota_distancia is None or rota_tempo is None:
        return None

    return {
        "rota_distancia": rota_distancia,
        "rota_tempo": rota_tempo,
        "mesmo_trajeto": rota_distancia["arestas"] == rota_tempo["arestas"],
        "distancia_adicional_metros": (
            rota_tempo["distancia_total"] - rota_distancia["distancia_total"]
        ),
        "tempo_economizado_segundos": (
            rota_distancia["tempo_total"] - rota_tempo["tempo_total"]
        ),
    }
