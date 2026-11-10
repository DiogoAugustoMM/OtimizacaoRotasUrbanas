"""Leitura dos dados do OpenStreetMap para futura conversão em grafo."""

import json
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path


def carregar_dados(caminho):
    with Path(caminho).open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def organizar_pontos(dados):
    pontos = {}

    for elemento in dados["elements"]:
        if elemento["type"] == "node":
            identificador = elemento["id"]

            pontos[identificador] = {
                "latitude": elemento["lat"],
                "longitude": elemento["lon"],
            }

    return pontos


def organizar_vias(dados):
    """Organiza as vias por ID, preservando a ordem dos pontos e as tags."""
    vias = {}

    for elemento in dados["elements"]:
        if elemento["type"] == "way":
            identificador = elemento["id"]
            vias[identificador] = {
                "nodes": list(elemento["nodes"]),
                "tags": dict(elemento.get("tags", {})),
            }

    return vias


def organizar_vizinhos(vias):
    """Mapeia conexões entre pontos, sem considerar sentidos de circulação.

    Cada chave é um ID de ponto e cada valor é um conjunto de IDs vizinhos.
    Apenas os pontos presentes nas vias são incluídos.
    """
    vizinhos = {}

    for via in vias.values():
        ids = via["nodes"]

        for identificador in ids:
            if identificador not in vizinhos:
                vizinhos[identificador] = set()

        for i in range(len(ids) - 1):
            origem = ids[i]
            destino = ids[i + 1]

            # Repetir o mesmo ID não cria um vizinho diferente.
            if origem == destino:
                continue

            vizinhos[origem].add(destino)
            vizinhos[destino].add(origem)

    return vizinhos


def identificar_vertices(pontos, vizinhos):
    """Seleciona inicialmente cruzamentos e extremidades pela conectividade.

    Extremidades podem ser limites dos dados, e não ruas sem saída reais.
    Esta seleção ainda não trata sentidos, acessos ou circuitos fechados
    formados exclusivamente por pontos com dois vizinhos.
    """
    cruzamentos = {}
    extremidades = {}

    for identificador, adjacentes in vizinhos.items():
        quantidade = len(adjacentes)

        if quantidade >= 3:
            cruzamentos[identificador] = pontos[identificador]
        elif quantidade == 1:
            extremidades[identificador] = pontos[identificador]

    return cruzamentos, extremidades


def construir_arestas(vizinhos, vertices, vias):
    """Agrupa segmentos entre vértices, sem pesos ou sentidos de circulação.

    Circuitos isolados sem vértices selecionados ainda não são incluídos.
    Cada segmento guarda as vias de origem para a futura análise das tags.
    """
    vias_por_segmento = {}
    for id_via, via in vias.items():
        ids = via["nodes"]
        for i in range(len(ids) - 1):
            segmento = tuple(sorted((ids[i], ids[i + 1])))
            vias_por_segmento.setdefault(segmento, set()).add(id_via)

    arestas = []
    visitados = set()

    for origem in sorted(vertices):
        for vizinho in sorted(vizinhos[origem]):
            segmento = tuple(sorted((origem, vizinho)))
            if segmento in visitados:
                continue

            percurso = [origem, vizinho]
            visitados.add(segmento)
            anterior = origem
            atual = vizinho

            while atual not in vertices:
                # Um ponto intermediário tem dois vizinhos; seguimos
                # pelo vizinho diferente daquele de onde chegamos.
                seguintes = vizinhos[atual] - {anterior}
                if len(seguintes) != 1:
                    raise ValueError(f"Ponto intermediário inválido: {atual}")
                proximo = next(iter(seguintes))
                segmento = tuple(sorted((atual, proximo)))
                if segmento in visitados:
                    raise ValueError("Segmento já percorrido antes de alcançar um vértice")
                visitados.add(segmento)
                percurso.append(proximo)
                anterior, atual = atual, proximo

            segmentos = []
            for i in range(len(percurso) - 1):
                a, b = percurso[i], percurso[i + 1]
                segmentos.append({
                    "origem": a,
                    "destino": b,
                    "vias": sorted(vias_por_segmento[tuple(sorted((a, b)))]),
                })

            arestas.append({
                "origem": origem,
                "destino": atual,
                "percurso": percurso,
                "segmentos": segmentos,
            })

    return arestas


def calcular_distancia_metros(ponto_a, ponto_b):
    """Estima a distância de superfície com Haversine, sem considerar altitude."""
    raio_terra_metros = 6_371_000
    latitude_a = radians(ponto_a["latitude"])
    latitude_b = radians(ponto_b["latitude"])
    delta_latitude = latitude_b - latitude_a
    delta_longitude = radians(ponto_b["longitude"] - ponto_a["longitude"])

    haversine = (
        sin(delta_latitude / 2) ** 2
        + cos(latitude_a) * cos(latitude_b) * sin(delta_longitude / 2) ** 2
    )
    # Evita que erros de arredondamento produzam raízes de números negativos.
    haversine = max(0.0, min(1.0, haversine))
    angulo = 2 * atan2(sqrt(haversine), sqrt(1 - haversine))
    return raio_terra_metros * angulo


def adicionar_distancias(arestas, pontos):
    """Adiciona distancia_metros aos próprios dicionários das arestas recebidas."""
    for aresta in arestas:
        distancia_total = 0.0
        percurso = aresta["percurso"]

        for i in range(len(percurso) - 1):
            ponto_a = pontos[percurso[i]]
            ponto_b = pontos[percurso[i + 1]]
            distancia_total += calcular_distancia_metros(ponto_a, ponto_b)

        aresta["distancia_metros"] = distancia_total


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent.parent
    caminho = raiz / "dados" / "bairro_teste.json"

    dados = carregar_dados(caminho)
    pontos = organizar_pontos(dados)
    vias = organizar_vias(dados)
    vizinhos = organizar_vizinhos(vias)
    cruzamentos, extremidades = identificar_vertices(pontos, vizinhos)
    vertices = {**cruzamentos, **extremidades}
    arestas = construir_arestas(vizinhos, vertices, vias)
    adicionar_distancias(arestas, pontos)

    print(f"Total de pontos: {len(pontos)}")

    for identificador, coordenadas in list(pontos.items())[:5]:
        print(identificador, coordenadas)

    print(f"\nTotal de vias: {len(vias)}")

    for identificador, via in list(vias.items())[:5]:
        nome = via["tags"].get("name", "Sem nome")
        print(f"\nVia {identificador}: {nome}")
        print(f"Pontos, na ordem da via: {via['nodes']}")

    print(f"\nTotal de pontos nas vias: {len(vizinhos)}")

    for identificador, adjacentes in list(vizinhos.items())[:5]:
        print(f"Ponto {identificador}: vizinhos {sorted(adjacentes)}")

    print(f"\nCruzamentos (3 ou mais vizinhos): {len(cruzamentos)}")
    print(f"Extremidades (1 vizinho): {len(extremidades)}")
    print(f"Vertices selecionados inicialmente: {len(cruzamentos) + len(extremidades)}")

    for identificador, coordenadas in list(cruzamentos.items())[:5]:
        print(f"Cruzamento {identificador}: {coordenadas}")

    print(f"\nArestas com distancia (ainda sem sentidos): {len(arestas)}")
    for aresta in arestas[:5]:
        print(
            f"{aresta['origem']} -> {aresta['destino']}: "
            f"{aresta['distancia_metros']:.2f} m; percurso {aresta['percurso']}"
        )
