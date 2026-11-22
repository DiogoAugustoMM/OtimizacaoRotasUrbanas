"""Leitura, validação e conversão dos dados do OpenStreetMap em grafo."""

import json
from argparse import ArgumentParser
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

from grafos.grafo import Grafo
from mapas.regras_carros import filtrar_vias_carros, sentido_da_via


def carregar_dados(caminho):
    """Lê um JSON da Overpass e valida os dados antes de devolvê-los.
    """
    caminho = Path(caminho)
    try:
        # utf-8-sig também aceita arquivos UTF-8 com marcador BOM.
        with caminho.open(encoding="utf-8-sig") as arquivo:
            dados = json.load(arquivo)
    except FileNotFoundError as erro:
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}") from erro
    except json.JSONDecodeError as erro:
        raise ValueError(
            f"JSON inválido em {caminho}: linha {erro.lineno}, coluna {erro.colno}"
        ) from erro
    except UnicodeDecodeError as erro:
        raise ValueError(f"O arquivo deve estar em UTF-8: {caminho}") from erro
    except OSError as erro:
        raise OSError(f"Não foi possível ler {caminho}: {erro}") from erro

    validar_dados(dados)
    return dados


def validar_dados(dados):
    """Verifica o formato e as referências sem modificar os dados recebidos.
    """
    if not isinstance(dados, dict):
        raise ValueError("O JSON deve conter um objeto com a lista 'elements'")
    if dados.get("type") in ("FeatureCollection", "Feature"):
        raise ValueError(
            "O arquivo é GeoJSON. Exporte os dados brutos (raw data) da Overpass, "
            "com a lista 'elements' e os IDs dos pontos"
        )
    if dados.get("remark"):
        raise ValueError(f"A Overpass informou um problema na consulta: {dados['remark']}")

    elementos = dados.get("elements")
    if not isinstance(elementos, list):
        raise ValueError("O JSON da Overpass deve conter uma lista 'elements'")

    ids_pontos = set()
    ids_vias = set()
    vias = []

    for indice, elemento in enumerate(elementos):
        if not isinstance(elemento, dict):
            raise ValueError(f"O elemento na posição {indice} deve ser um objeto")
        tipo = elemento.get("type")
        if tipo in ("relation", "area"):
            continue
        if tipo not in ("node", "way"):
            raise ValueError(f"Tipo de elemento inválido na posição {indice}: {tipo!r}")

        identificador = elemento.get("id")
        if type(identificador) is not int:
            raise ValueError(f"O elemento na posição {indice} deve ter um ID inteiro")
        tags = elemento.get("tags", {})
        if not isinstance(tags, dict) or any(
            not isinstance(chave, str) or not isinstance(valor, str)
            for chave, valor in tags.items()
        ):
            raise ValueError(f"As tags de {tipo} {identificador} devem associar textos a textos")

        if tipo == "node":
            if identificador in ids_pontos:
                raise ValueError(f"ID de ponto duplicado: {identificador}")
            ids_pontos.add(identificador)
            for campo, limite in (("lat", 90), ("lon", 180)):
                valor = elemento.get(campo)
                if type(valor) not in (int, float) or not -limite <= valor <= limite:
                    raise ValueError(f"Coordenada '{campo}' inválida no ponto {identificador}")
        else:
            if identificador in ids_vias:
                raise ValueError(f"ID de via duplicado: {identificador}")
            ids_vias.add(identificador)
            nodes = elemento.get("nodes")
            if (
                not isinstance(nodes, list)
                or len(nodes) < 2
                or any(type(id_ponto) is not int for id_ponto in nodes)
            ):
                raise ValueError(
                    f"A via {identificador} deve ter uma lista 'nodes' com pelo menos dois IDs inteiros"
                )
            vias.append(elemento)

    if not vias:
        raise ValueError("O arquivo não contém vias (way) para converter")

    # A ordem no JSON é livre: conferimos as referências após ler todos os pontos.
    for via in vias:
        for id_ponto in via["nodes"]:
            if id_ponto not in ids_pontos:
                raise ValueError(
                    f"A via {via['id']} referencia o ponto ausente {id_ponto}. "
                    "Exporte também os pontos das vias na consulta Overpass"
                )


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


def selecionar_vertices_carros(pontos, vizinhos, vias):
    """Mantém ramificações, extremidades e limites de cada way selecionada.
    """
    cruzamentos, extremidades = identificar_vertices(pontos, vizinhos)
    vertices = {**cruzamentos, **extremidades}
    for via in vias.values():
        for identificador in (via["nodes"][0], via["nodes"][-1]):
            vertices[identificador] = pontos[identificador]
    return vertices


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


def direcionar_arestas(arestas, vias):
    """Cria arcos apenas quando todos os segmentos permitem aquele sentido.

    Não deduz o sentido a partir dos IDs: usa a ordem original dos nodes de
    cada via. Mantém, em cada segmento orientado, apenas as vias compatíveis.
    """
    vias_por_direcao = {}
    for id_via, via in vias.items():
        sentido = sentido_da_via(via["tags"])
        if sentido is None:
            raise ValueError(f"Sentido não suportado na via {id_via}")
        ids = via["nodes"]
        for origem, destino in zip(ids, ids[1:]):
            if origem == destino:
                continue
            if sentido in (0, 1):
                vias_por_direcao.setdefault((origem, destino), set()).add(id_via)
            if sentido in (0, -1):
                vias_por_direcao.setdefault((destino, origem), set()).add(id_via)

    direcionadas = []
    for aresta in arestas:
        for percurso in (aresta["percurso"], list(reversed(aresta["percurso"]))):
            segmentos = []
            for origem, destino in zip(percurso, percurso[1:]):
                ids_vias = vias_por_direcao.get((origem, destino))
                if not ids_vias:
                    break
                segmentos.append({
                    "origem": origem,
                    "destino": destino,
                    "vias": sorted(ids_vias),
                })
            else:
                direcionadas.append({
                    "origem": percurso[0],
                    "destino": percurso[-1],
                    "percurso": list(percurso),
                    "segmentos": segmentos,
                })
    return direcionadas


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


def obter_nomes_da_aresta(aresta, vias):
    """Retorna os nomes das vias do percurso, sem repetir nomes iguais."""
    nomes = []
    for segmento in aresta["segmentos"]:
        for id_via in segmento["vias"]:
            nome = vias[id_via]["tags"].get("name") or f"Via sem nome (OSM {id_via})"
            if nome not in nomes:
                nomes.append(nome)
    return " / ".join(nomes) or "Sem via identificada"


def montar_grafo(vertices, arestas, direcionado=False):
    """Preenche um Grafo com os dados já convertidos.

    Os IDs intermediários ficam nos percursos; suas coordenadas continuam
    no dicionário pontos. As tags das vias continuam no dicionário vias.
    """
    grafo = Grafo(direcionado=direcionado)

    for identificador, coordenadas in vertices.items():
        grafo.adicionar_vertice(
            identificador, coordenadas["latitude"], coordenadas["longitude"]
        )

    for aresta in arestas:
        grafo.adicionar_aresta(
            origem=aresta["origem"],
            destino=aresta["destino"],
            distancia_metros=aresta["distancia_metros"],
            percurso=aresta["percurso"],
            segmentos=aresta["segmentos"],
        )

    return grafo


def carregar_mapa(caminho):
    """Retorna (grafo, pontos, vias) a partir de um arquivo JSON validado.

    Pontos inclui as coordenadas intermediárias dos percursos, e vias guarda
    as tags originais. Não faz consultas à API nem imprime no terminal.
    O grafo é direcionado e usa o perfil básico de carros particulares.
    As vias retornadas são apenas as selecionadas para esse perfil.
    """
    dados = carregar_dados(caminho)
    pontos = organizar_pontos(dados)
    vias, _ = filtrar_vias_carros(organizar_vias(dados))
    if not vias:
        raise ValueError("Nenhuma via compatível com o perfil de carros foi encontrada")
    vizinhos = organizar_vizinhos(vias)
    vertices = selecionar_vertices_carros(pontos, vizinhos, vias)
    trechos = construir_arestas(vizinhos, vertices, vias)
    arestas = direcionar_arestas(trechos, vias)
    adicionar_distancias(arestas, pontos)
    grafo = montar_grafo(vertices, arestas, direcionado=True)
    return grafo, pontos, vias


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent.parent
    parser = ArgumentParser(description="Carrega um JSON da Overpass e monta o grafo inicial")
    parser.add_argument(
        "caminho", nargs="?", type=Path, default=raiz / "dados" / "bairro_teste.json",
        help="Arquivo JSON da Overpass (padrão: dados/bairro_teste.json)",
    )
    argumentos = parser.parse_args()
    try:
        grafo, pontos, vias = carregar_mapa(argumentos.caminho)
    except (OSError, ValueError) as erro:
        raise SystemExit(f"Erro ao carregar mapa: {erro}") from None

    # Reconstrói apenas as informações usadas no resumo de diagnóstico.
    vizinhos = organizar_vizinhos(vias)
    cruzamentos, extremidades = identificar_vertices(pontos, vizinhos)
    vertices = grafo.vertices
    arestas = list(grafo.arestas.values())

    print(f"Total de pontos: {len(pontos)}")

    for identificador, coordenadas in list(pontos.items())[:5]:
        print(identificador, coordenadas)

    print(f"\nVias selecionadas para carros: {len(vias)}")

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
    print(f"Vertices apos preservar limites das vias e circuitos: {len(vertices)}")

    for identificador, coordenadas in list(cruzamentos.items())[:5]:
        print(f"Cruzamento {identificador}: {coordenadas}")

    print(f"\nArestas direcionadas para carros: {len(arestas)}")
    for aresta in arestas[:5]:
        nomes = obter_nomes_da_aresta(aresta, vias)
        print(
            f"{nomes} | {aresta['origem']} -> {aresta['destino']}: "
            f"{aresta['distancia_metros']:.2f} m; percurso {aresta['percurso']}"
        )

    print(f"\nGrafo direcionado: {len(grafo.vertices)} vertices e {len(grafo.arestas)} arestas")
    if grafo.vertices:
        primeiro_vertice = next(iter(grafo.vertices))
        print(f"Conexoes do vertice {primeiro_vertice}:")
        for conexao in grafo.obter_vizinhos(primeiro_vertice):
            aresta = grafo.arestas[conexao["id_aresta"]]
            nomes = obter_nomes_da_aresta(aresta, vias)
            print(
                f"  {nomes} | destino {conexao['destino']} | "
                f"{conexao['distancia_metros']:.2f} m | aresta {conexao['id_aresta']}"
            )
