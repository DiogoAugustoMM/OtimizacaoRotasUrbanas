import heapq
from math import inf
from mapas.conversor import calcular_distancia_metros


# Velocidades médias em km/h quando a via do OSM não possui a tag 'maxspeed'
VELOCIDADES_PADRAO_KMH = {
    "motorway": 90.0,
    "motorway_link": 60.0,
    "trunk": 80.0,
    "trunk_link": 50.0,
    "primary": 60.0,
    "primary_link": 40.0,
    "secondary": 50.0,
    "secondary_link": 40.0,
    "tertiary": 40.0,
    "tertiary_link": 30.0,
    "residential": 30.0,
    "living_street": 20.0,
    "unclassified": 30.0,
    "service": 20.0,
}
VELOCIDADE_FALLBACK_KMH = 30.0


def _extrair_velocidade_via_kmh(tags):
    """Obtém a velocidade em km/h a partir das tags do OpenStreetMap."""
    maxspeed = tags.get("maxspeed")
    if maxspeed:
        # Trata formatos comuns do OSM como "60", "60 km/h", "40;60"
        texto = maxspeed.lower().replace("km/h", "").replace("kmh", "").strip()
        if ";" in texto:
            texto = texto.split(";")[0].strip()
        try:
            velocidade = float(texto)
            if velocidade > 0:
                return velocidade
        except ValueError:
            pass

    tipo_via = tags.get("highway", "")
    return VELOCIDADES_PADRAO_KMH.get(tipo_via, VELOCIDADE_FALLBACK_KMH)


def calcular_tempo_aresta_segundos(aresta, pontos, vias):
    """Calcula o tempo total (em segundos) para percorrer uma aresta.

    Soma o tempo de cada segmento individual usando a maior velocidade
    permitida entre as vias compatíveis daquele trecho.
    """
    tempo_total = 0.0

    for segmento in aresta["segmentos"]:
        ponto_a = pontos[segmento["origem"]]
        ponto_b = pontos[segmento["destino"]]
        dist_segmento_m = calcular_distancia_metros(ponto_a, ponto_b)

        # Se houver mais de uma via associada ao segmento, pega a maior velocidade
        velocidades = [
            _extrair_velocidade_via_kmh(vias[id_via]["tags"])
            for id_via in segmento["vias"]
            if id_via in vias
        ]
        vel_kmh = max(velocidades) if velocidades else VELOCIDADE_FALLBACK_KMH
        vel_ms = vel_kmh / 3.6

        tempo_total += dist_segmento_m / vel_ms

    return tempo_total


def calcular_menor_caminho(
    grafo, origem, destino, criterio="distancia", pontos=None, vias=None
):
    """Calcula o menor caminho entre origem e destino usando Dijkstra.

    Parâmetros:
        grafo: instância de Grafo.
        origem: ID do vértice inicial.
        destino: ID do vértice final.
        criterio: "distancia" (em metros) ou "tempo" (em segundos).
        pontos: dicionário retornado por carregar_mapa (obrigatório se criterio="tempo").
        vias: dicionário retornado por carregar_mapa (obrigatório se criterio="tempo").
    """
    if origem not in grafo.vertices:
        raise ValueError(f"Vértice de origem não cadastrado: {origem}")
    if destino not in grafo.vertices:
        raise ValueError(f"Vértice de destino não cadastrado: {destino}")
    if criterio not in ("distancia", "tempo"):
        raise ValueError("Critério inválido: use 'distancia' ou 'tempo'")
    if criterio == "tempo" and (pontos is None or vias is None):
        raise ValueError("Os dicionários 'pontos' e 'vias' são obrigatórios para o critério 'tempo'")

    if origem == destino:
        return {
            "criterio": criterio,
            "distancia_total": 0.0,
            "tempo_total": 0.0 if (pontos and vias) else None,
            "vertices": [origem],
            "arestas": [],
            "percurso_completo": [origem],
        }

    # Pré-calcula o peso de cada aresta uma única vez se o critério for tempo
    tempos_arestas = {}
    if pontos is not None and vias is not None:
        for id_aresta, aresta in grafo.arestas.items():
            tempos_arestas[id_aresta] = calcular_tempo_aresta_segundos(aresta, pontos, vias)

    custos = {v: inf for v in grafo.vertices}
    custos[origem] = 0.0
    anteriores = {v: None for v in grafo.vertices}

    fila_prioridade = [(0.0, origem)]
    visitados = set()

    while fila_prioridade:
        custo_atual, vertice_atual = heapq.heappop(fila_prioridade)

        if vertice_atual in visitados:
            continue
        visitados.add(vertice_atual)

        if vertice_atual == destino:
            return _reconstruir_rota(
                grafo, origem, destino, criterio, anteriores, tempos_arestas
            )

        for conexao in grafo.obter_vizinhos(vertice_atual):
            vizinho = conexao["destino"]
            id_aresta = conexao["id_aresta"]

            if vizinho in visitados:
                continue

            peso = (
                tempos_arestas[id_aresta]
                if criterio == "tempo"
                else conexao["distancia_metros"]
            )
            novo_custo = custo_atual + peso

            if novo_custo < custos[vizinho]:
                custos[vizinho] = novo_custo
                anteriores[vizinho] = (vertice_atual, id_aresta)
                heapq.heappush(fila_prioridade, (novo_custo, vizinho))

    return None


def _reconstruir_rota(grafo, origem, destino, criterio, anteriores, tempos_arestas):
    """Reconstrói vértices, arestas, percurso e métricas totais da rota."""
    caminho_vertices = []
    caminho_arestas = []

    atual = destino
    while atual != origem:
        caminho_vertices.append(atual)
        vertice_anterior, id_aresta = anteriores[atual]
        caminho_arestas.append(id_aresta)
        atual = vertice_anterior

    caminho_vertices.append(origem)
    caminho_vertices.reverse()
    caminho_arestas.reverse()

    distancia_total = 0.0
    tempo_total = 0.0 if tempos_arestas else None
    percurso_completo = [origem]

    for i, id_aresta in enumerate(caminho_arestas):
        u = caminho_vertices[i]
        v = caminho_vertices[i + 1]
        aresta = grafo.arestas[id_aresta]

        distancia_total += aresta["distancia_metros"]
        if tempo_total is not None:
            tempo_total += tempos_arestas[id_aresta]

        pontos_aresta = aresta["percurso"]
        if aresta["origem"] != u or aresta["destino"] != v:
            pontos_aresta = list(reversed(pontos_aresta))

        percurso_completo.extend(pontos_aresta[1:])

    return {
        "criterio": criterio,
        "distancia_total": distancia_total,
        "tempo_total": tempo_total,
        "vertices": caminho_vertices,
        "arestas": caminho_arestas,
        "percurso_completo": percurso_completo,
    }