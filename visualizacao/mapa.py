"""Visualização de mapas e rotas com Folium (RF04 e RF06).

Este módulo só desenha: não cria nem processa grafos. Ele usa o grafo, os
pontos e as arestas que já vêm de mapas.conversor.carregar_mapa.
"""

from mapas.conversor import calcular_distancia_metros


def vertice_mais_proximo(grafo, latitude, longitude):
    """Retorna o ID do vértice mais próximo de uma coordenada (busca linear).

    Usado para transformar o clique do usuário no mapa em origem/destino.
    """
    if not grafo.vertices:
        raise ValueError("O grafo não possui vértices")
    ponto = {"latitude": latitude, "longitude": longitude}
    return min(
        grafo.vertices,
        key=lambda v: calcular_distancia_metros(grafo.vertices[v], ponto),
    )


def coordenadas_do_percurso(pontos, percurso):
    """Converte uma lista de IDs de pontos em pares (latitude, longitude)."""
    return [(pontos[i]["latitude"], pontos[i]["longitude"]) for i in percurso]


def coordenadas_da_rota(grafo, pontos, ids_arestas):
    """Junta os percursos das arestas da rota, na ordem, sem repetir a junção."""
    coordenadas = []
    for id_aresta in ids_arestas:
        trecho = coordenadas_do_percurso(pontos, grafo.arestas[id_aresta]["percurso"])
        # O último ponto de uma aresta é o primeiro da seguinte.
        coordenadas.extend(trecho if not coordenadas else trecho[1:])
    return coordenadas


def limites_do_grafo(grafo):
    """Retorna [[lat_min, lon_min], [lat_max, lon_max]] dos vértices."""
    latitudes = [v["latitude"] for v in grafo.vertices.values()]
    longitudes = [v["longitude"] for v in grafo.vertices.values()]
    return [[min(latitudes), min(longitudes)], [max(latitudes), max(longitudes)]]


def geometria_das_ruas(grafo, pontos):
    """Agrupa as ruas para desenhá-las uma vez, mesmo quando têm ida e volta."""
    vistos = set()
    linhas = []
    for aresta in grafo.arestas.values():
        percurso = tuple(aresta["percurso"])
        chave = min(percurso, percurso[::-1])
        if chave not in vistos:
            vistos.add(chave)
            linhas.append([
                [pontos[i]["longitude"], pontos[i]["latitude"]] for i in percurso
            ])
    return {"type": "MultiLineString", "coordinates": linhas}


def criar_mapa(grafo, pontos, ids_arestas=None, origem=None, destino=None,
               mostrar_ruas=False, geometria_ruas=None):
    """Monta o mapa Folium com a rota, a origem e o destino."""
    import folium  # importado aqui para os cálculos acima não exigirem Folium

    limites = limites_do_grafo(grafo)
    centro = [(limites[0][0] + limites[1][0]) / 2, (limites[0][1] + limites[1][1]) / 2]
    mapa = folium.Map(location=centro, zoom_start=15, prefer_canvas=True)
    mapa.fit_bounds(limites)

    if mostrar_ruas:
        folium.GeoJson(
            geometria_ruas if geometria_ruas is not None else geometria_das_ruas(grafo, pontos),
            style_function=lambda feature: {"weight": 3, "color": "#6A1B9A", "opacity": 0.85},
            name="Ruas do grafo",
        ).add_to(mapa)

    if ids_arestas:
        folium.PolyLine(
            coordenadas_da_rota(grafo, pontos, ids_arestas),
            weight=6, color="blue", opacity=0.9,
        ).add_to(mapa)

    for vertice, cor, rotulo in ((origem, "green", "Origem"), (destino, "red", "Destino")):
        if vertice is not None:
            c = grafo.vertices[vertice]
            folium.Marker(
                [c["latitude"], c["longitude"]],
                tooltip=rotulo, icon=folium.Icon(color=cor),
            ).add_to(mapa)
    return mapa
