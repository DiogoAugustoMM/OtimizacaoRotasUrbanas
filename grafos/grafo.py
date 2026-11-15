"""Estrutura própria de grafo com pesos e suporte a arestas paralelas."""

from copy import deepcopy
from math import isfinite


class Grafo:
    """Armazena vértices, arestas e listas de adjacência.

    Por padrão, cada aresta pode ser percorrida nos dois sentidos.
    Com direcionado=True, só permite ir da origem para o destino.
    Isso não interpreta automaticamente as regras do OpenStreetMap.
    """

    def __init__(self, direcionado=False):
        self.direcionado = direcionado
        self.vertices = {}
        self.arestas = {}
        self.adjacencias = {}
        self._proximo_id_aresta = 0

    def adicionar_vertice(self, identificador, latitude, longitude):
        """Registra um vértice sem sobrescrever um ID já existente."""
        if identificador in self.vertices:
            raise ValueError(f"Vértice já cadastrado: {identificador}")

        self.vertices[identificador] = {
            "latitude": latitude,
            "longitude": longitude,
        }
        self.adjacencias[identificador] = []

    def adicionar_aresta(
        self, origem, destino, distancia_metros, percurso=None, segmentos=None
    ):
        """Registra uma aresta e retorna seu ID, gerado pelo próprio grafo.

        O percurso guarda IDs de pontos, inclusive intermediários que não
        são vértices. Os segmentos preservam as referências às vias de origem.
        """
        if origem not in self.vertices or destino not in self.vertices:
            raise ValueError("Os dois extremos precisam estar cadastrados como vértices")
        if not isfinite(distancia_metros) or distancia_metros < 0:
            raise ValueError("A distância deve ser finita e não negativa")

        if percurso is None:
            percurso = [origem, destino]
        if len(percurso) < 2 or percurso[0] != origem or percurso[-1] != destino:
            raise ValueError("O percurso deve começar na origem e terminar no destino")

        identificador = self._proximo_id_aresta
        self.arestas[identificador] = {
            "origem": origem,
            "destino": destino,
            "distancia_metros": distancia_metros,
            "percurso": list(percurso),
            "segmentos": deepcopy(segmentos) if segmentos is not None else [],
        }
        self.adjacencias[origem].append(identificador)
        # Um laço (origem == destino) já está na lista do seu único extremo.
        if not self.direcionado and destino != origem:
            self.adjacencias[destino].append(identificador)
        self._proximo_id_aresta += 1
        return identificador

    def obter_vizinhos(self, identificador):
        """Retorna uma lista de conexões, preservando alternativas paralelas.

        Cada conexão contém destino, distancia_metros e id_aresta.
        No grafo não direcionado, o destino consultado é o outro extremo.
        O percurso armazenado mantém a orientação original da aresta.
        """
        if identificador not in self.vertices:
            raise ValueError(f"Vértice não cadastrado: {identificador}")

        conexoes = []
        for id_aresta in self.adjacencias[identificador]:
            aresta = self.arestas[id_aresta]
            if aresta["origem"] == identificador:
                destino = aresta["destino"]
            else:
                destino = aresta["origem"]
            conexoes.append({
                "destino": destino,
                "distancia_metros": aresta["distancia_metros"],
                "id_aresta": id_aresta,
            })
        return conexoes
