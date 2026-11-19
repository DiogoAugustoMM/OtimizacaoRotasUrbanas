"""Associa cliques às ruas e prepara vértices temporários para uma consulta.

Não altera o grafo em cache. Usa uma projeção plana local aproximada, adequada
à escala urbana, para encontrar o ponto mais próximo sobre os segmentos.
As distâncias das novas arestas continuam sendo calculadas com Haversine.
"""

from copy import copy
from math import cos, isfinite, pi, radians

from mapas.conversor import calcular_distancia_metros


TOLERANCIA_METROS = 0.01


def criar_indice_segmentos(grafo, pontos):
    """Prepara uma lista de segmentos físicos, sem duplicar ida e volta.

    A busca ainda é linear, mas as coordenadas projetadas são calculadas uma
    única vez. IDs distintos não são unidos apenas por terem coordenadas iguais.
    """
    if not grafo.vertices or not grafo.arestas:
        raise ValueError("O grafo não possui trechos para selecionar pontos")
    latitude_media = sum(p["latitude"] for p in grafo.vertices.values()) / len(grafo.vertices)
    escala_latitude = 6_371_000 * pi / 180
    escala_longitude = escala_latitude * cos(radians(latitude_media))
    if abs(escala_longitude) < 1e-6:
        raise ValueError("A projeção urbana não é adequada a pontos nos polos")

    segmentos = {}
    for aresta in grafo.arestas.values():
        percurso = aresta["percurso"]
        for a, b in zip(percurso, percurso[1:]):
            chave = tuple(sorted((a, b)))
            if chave in segmentos or a == b:
                continue
            a, b = chave
            pa, pb = pontos[a], pontos[b]
            x = pa["longitude"] * escala_longitude
            y = pa["latitude"] * escala_latitude
            dx = (pb["longitude"] - pa["longitude"]) * escala_longitude
            dy = (pb["latitude"] - pa["latitude"]) * escala_latitude
            segmentos[chave] = {
                "ids": chave, "x": x, "y": y, "dx": dx, "dy": dy,
                "comprimento_quadrado": dx * dx + dy * dy,
            }
    if not segmentos:
        raise ValueError("O grafo não possui segmentos para selecionar pontos")
    return {
        "escala_latitude": escala_latitude,
        "escala_longitude": escala_longitude,
        "segmentos": list(segmentos.values()),
    }


def localizar_ponto_na_via(indice, pontos, latitude, longitude):
    """Projeta um clique no segmento mais próximo e retorna sua localização.

    fracao vai de 0 a 1 na ordem dos IDs de segmento. id_ponto identifica um
    ponto OSM existente quando a projeção cai numa extremidade do segmento.
    """
    for valor, limite in ((latitude, 90), (longitude, 180)):
        if type(valor) not in (int, float) or not isfinite(valor) or not -limite <= valor <= limite:
            raise ValueError("O clique deve conter latitude e longitude válidas")

    x = longitude * indice["escala_longitude"]
    y = latitude * indice["escala_latitude"]
    melhor = None
    menor_distancia = float("inf")
    for segmento in indice["segmentos"]:
        comprimento = segmento["comprimento_quadrado"]
        fracao = (
            ((x - segmento["x"]) * segmento["dx"] + (y - segmento["y"]) * segmento["dy"])
            / comprimento if comprimento else 0.0
        )
        fracao = max(0.0, min(1.0, fracao))
        distancia = (
            (x - segmento["x"] - fracao * segmento["dx"]) ** 2
            + (y - segmento["y"] - fracao * segmento["dy"]) ** 2
        )
        if distancia < menor_distancia:
            menor_distancia = distancia
            melhor = segmento, fracao

    if melhor is None:
        raise ValueError("O índice não possui segmentos para selecionar pontos")
    segmento, fracao = melhor
    a, b = segmento["ids"]
    pa, pb = pontos[a], pontos[b]
    id_ponto = None
    comprimento = segmento["comprimento_quadrado"] ** 0.5
    if fracao * comprimento <= TOLERANCIA_METROS:
        fracao, id_ponto = 0.0, a
    elif (1 - fracao) * comprimento <= TOLERANCIA_METROS:
        fracao, id_ponto = 1.0, b
    posicao = {
        "latitude": pa["latitude"] + fracao * (pb["latitude"] - pa["latitude"]),
        "longitude": pa["longitude"] + fracao * (pb["longitude"] - pa["longitude"]),
    }
    return {
        **posicao, "segmento": (a, b), "fracao": fracao, "id_ponto": id_ponto,
        "distancia_clique_metros": calcular_distancia_metros(
            {"latitude": latitude, "longitude": longitude}, posicao
        ),
    }


def inserir_pontos_temporarios(grafo, pontos, localizacoes):
    """Retorna (grafo_consulta, pontos_consulta, ids_selecionados).

    Divide simultaneamente origem e destino, inclusive se estão na mesma
    aresta. Atualiza todas as conexões sobre o segmento escolhido, preservando
    os sentidos existentes e as vias de cada pedaço. Não conecta linhas que
    apenas se cruzam no desenho sem compartilhar IDs.

    Copia os dicionários principais e somente as adjacências afetadas. Registros
    não alterados são compartilhados para leitura; o grafo original não é modificado.
    """
    novos_pontos = {}
    insercoes = {}
    ids = []
    proximo_id = min(0, min(pontos, default=0), min(grafo.vertices, default=0)) - 1

    for local in localizacoes:
        identificador = local["id_ponto"]
        if identificador is None:
            chave = local["segmento"]
            lista = insercoes.setdefault(chave, [])
            # Reutiliza um ponto temporário se os dois cliques projetam no mesmo local.
            identificador = next((
                id_existente for _, id_existente in lista
                if calcular_distancia_metros(novos_pontos[id_existente], local) <= TOLERANCIA_METROS
            ), None)
            if identificador is None:
                identificador = proximo_id
                proximo_id -= 1
                novos_pontos[identificador] = {
                    "latitude": local["latitude"], "longitude": local["longitude"],
                }
                lista.append((local["fracao"], identificador))
        ids.append(identificador)

    selecionados = set(ids)
    promovidos = selecionados - grafo.vertices.keys()
    if not promovidos:
        return grafo, pontos, ids

    consulta = copy(grafo)
    consulta.vertices = dict(grafo.vertices)
    consulta.arestas = dict(grafo.arestas)
    consulta.adjacencias = dict(grafo.adjacencias)
    pontos_consulta = {**pontos, **novos_pontos}
    for identificador in promovidos:
        p = pontos_consulta[identificador]
        consulta.adicionar_vertice(identificador, p["latitude"], p["longitude"])

    afetadas = []
    for id_aresta, aresta in grafo.arestas.items():
        percurso = aresta["percurso"]
        if (
            promovidos.intersection(percurso[1:-1])
            or any(tuple(sorted((a, b))) in insercoes for a, b in zip(percurso, percurso[1:]))
        ):
            afetadas.append((id_aresta, aresta))

    # As listas desses extremos receberão novas arestas; precisam ser cópias.
    extremos = {a[campo] for _, a in afetadas for campo in ("origem", "destino")}
    for identificador in extremos:
        consulta.adjacencias[identificador] = list(grafo.adjacencias[identificador])
    for id_aresta, aresta in afetadas:
        del consulta.arestas[id_aresta]
        for extremo in {aresta["origem"], aresta["destino"]}:
            consulta.adjacencias[extremo] = [
                i for i in consulta.adjacencias[extremo] if i != id_aresta
            ]

        percurso = [aresta["percurso"][0]]
        segmentos = []
        for i, (a, b) in enumerate(zip(aresta["percurso"], aresta["percurso"][1:])):
            chave = tuple(sorted((a, b)))
            intermediarios = sorted(insercoes.get(chave, []), reverse=a > b)
            trecho = [a, *[id_ponto for _, id_ponto in intermediarios], b]
            vias = aresta["segmentos"][i]["vias"] if aresta["segmentos"] else []
            for inicio, fim in zip(trecho, trecho[1:]):
                segmentos.append({"origem": inicio, "destino": fim, "vias": list(vias)})
            percurso.extend(trecho[1:])

        inicio = 0
        for fim in range(1, len(percurso)):
            if percurso[fim] in selecionados or fim == len(percurso) - 1:
                parte = percurso[inicio:fim + 1]
                distancia = sum(
                    calcular_distancia_metros(pontos_consulta[a], pontos_consulta[b])
                    for a, b in zip(parte, parte[1:])
                )
                consulta.adicionar_aresta(
                    parte[0], parte[-1], distancia,
                    percurso=parte, segmentos=segmentos[inicio:fim],
                )
                inicio = fim
    return consulta, pontos_consulta, ids
