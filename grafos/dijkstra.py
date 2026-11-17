import heapq
from math import inf


def calcular_menor_caminho(grafo, origem, destino):
    """Calcula o menor caminho entre dois vértices usando o algoritmo de Dijkstra.

    Consulta o objeto Grafo e retorna um dicionário contendo a distância total,
    a sequência de vértices, os IDs das arestas escolhidas e o percurso completo
    de pontos para exibição no mapa. Retorna None se não houver caminho.
    """
    if origem not in grafo.vertices:
        raise ValueError(f"Vértice de origem não cadastrado: {origem}")
    if destino not in grafo.vertices:
        raise ValueError(f"Vértice de destino não cadastrado: {destino}")

    # Caso trivial: origem e destino são o mesmo ponto
    if origem == destino:
        return {
            "distancia_total": 0.0,
            "vertices": [origem],
            "arestas": [],
            "percurso_completo": [origem],
        }

    # Estruturas de controle do Dijkstra
    distancias = {v: inf for v in grafo.vertices}
    distancias[origem] = 0.0

    # Guarda (vertice_anterior, id_aresta_utilizada) para reconstruir a rota exata
    anteriores = {v: None for v in grafo.vertices}

    # Fila de prioridade: (distancia_acumulada, id_vertice)
    fila_prioridade = [(0.0, origem)]
    visitados = set()

    while fila_prioridade:
        dist_atual, vertice_atual = heapq.heappop(fila_prioridade)

        if vertice_atual in visitados:
            continue
        visitados.add(vertice_atual)

        # Retorno antecipado: ao tirar o destino da fila, o menor caminho já está garantido
        if vertice_atual == destino:
            return _reconstruir_rota(grafo, origem, destino, dist_atual, anteriores)

        # Consulta conexões e pesos no Grafo
        for conexao in grafo.obter_vizinhos(vertice_atual):
            vizinho = conexao["destino"]
            peso = conexao["distancia_metros"]
            id_aresta = conexao["id_aresta"]

            if vizinho in visitados:
                continue

            nova_distancia = dist_atual + peso

            if nova_distancia < distancias[vizinho]:
                distancias[vizinho] = nova_distancia
                anteriores[vizinho] = (vertice_atual, id_aresta)
                heapq.heappush(fila_prioridade, (nova_distancia, vizinho))

    # Se a fila esvaziar sem alcançar o destino, o grafo é desconexo entre esses pontos
    return None


def _reconstruir_rota(grafo, origem, destino, distancia_total, anteriores):
    """Reconstrói a sequência de vértices, arestas e pontos intermediários."""
    caminho_vertices = []
    caminho_arestas = []

    atual = destino
    while atual != origem:
        caminho_vertices.append(atual)
        vertice_anterior, id_aresta = anteriores[atual]
        caminho_arestas.append(id_aresta)
        atual = vertice_anterior

    caminho_vertices.append(origem)

    # Inverte para ficar na ordem origem -> destino
    caminho_vertices.reverse()
    caminho_arestas.reverse()

    # Monta a lista contínua de IDs de pontos (incluindo curvas/intermediários)
    percurso_completo = [origem]
    for i, id_aresta in enumerate(caminho_arestas):
        u = caminho_vertices[i]
        v = caminho_vertices[i + 1]
        aresta = grafo.arestas[id_aresta]

        pontos_aresta = aresta["percurso"]
        # Se a aresta foi percorrida no sentido inverso (em grafo não direcionado)
        if aresta["origem"] != u or aresta["destino"] != v:
            pontos_aresta = list(reversed(pontos_aresta))

        # Adiciona do segundo ponto em diante para não duplicar o vértice de junção
        percurso_completo.extend(pontos_aresta[1:])

    return {
        "distancia_total": distancia_total,
        "vertices": caminho_vertices,
        "arestas": caminho_arestas,
        "percurso_completo": percurso_completo,
    }