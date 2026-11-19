"""Mede o desempenho do projeto sem alterar os seus módulos.

Copie este arquivo para a raiz do repositório e execute no PowerShell:
    .\\.venv\\Scripts\\python.exe benchmark_desempenho_rotas_leve.py

As medições usam arquivos JSON já existentes em dados/. Os resultados serão
exibidos no terminal e registrados em dados/resultados_desempenho_leve.csv.
"""

from collections import deque
from csv import DictWriter
from pathlib import Path
from random import Random
from statistics import median
from time import perf_counter

from grafos.dijkstra import calcular_menor_caminho
from mapas.conversor import carregar_mapa
from mapas.localizacao import (
    criar_indice_segmentos,
    inserir_pontos_temporarios,
    localizar_ponto_na_via,
)
from resultados import comparar_rotas


REPETICOES = 3
MAX_PARES = 2
SEMENTE = 2026
PASTA_DADOS = Path(__file__).resolve().parent / "dados"
SAIDA = PASTA_DADOS / "resultados_desempenho_leve.csv"


def medir_mediana_ms(funcao):
    """Executa um aquecimento e retorna a mediana de várias execuções, em ms."""
    funcao()  # Aquecimento: não entra no resultado.
    tempos_ms = []
    for _ in range(REPETICOES):
        inicio = perf_counter()
        funcao()
        tempos_ms.append((perf_counter() - inicio) * 1000)
    return median(tempos_ms)


def escolher_pares_alcancaveis(grafo):
    """Gera pares dirigidos alcançáveis, de forma reproduzível, sem cronometrar."""
    aleatorio = Random(SEMENTE)
    origens = list(grafo.vertices)
    aleatorio.shuffle(origens)
    pares = []
    for origem in origens:
        visitados = {origem}
        fila = deque([origem])
        while fila:
            atual = fila.popleft()
            for conexao in grafo.obter_vizinhos(atual):
                destino = conexao["destino"]
                if destino not in visitados:
                    visitados.add(destino)
                    fila.append(destino)
        destinos = sorted(visitados - {origem})
        if destinos:
            pares.append((origem, destinos[aleatorio.randrange(len(destinos))]))
        if len(pares) == MAX_PARES:
            break
    return pares


def ponto_medio(indice, pontos, posicao):
    """Retorna a coordenada central de um segmento físico do índice."""
    segmento = indice["segmentos"][posicao]
    a, b = segmento["ids"]
    return (
        (pontos[a]["latitude"] + pontos[b]["latitude"]) / 2,
        (pontos[a]["longitude"] + pontos[b]["longitude"]) / 2,
    )


def analisar_mapa(caminho):
    print("  Montando grafo do mapa...", flush=True)
    grafo, pontos, vias = carregar_mapa(str(caminho))
    print(f"  Grafo pronto: {len(grafo.vertices)} vertices e {len(grafo.arestas)} arestas", flush=True)
    print("  Preparando indice de segmentos...", flush=True)
    indice = criar_indice_segmentos(grafo, pontos)
    print("  Selecionando pares alcançaveis...", flush=True)
    pares = escolher_pares_alcancaveis(grafo)
    print(f"  {len(pares)} pares selecionados", flush=True)

    # O tempo de carregar o JSON e construir o grafo é separado do roteamento.
    print("  Medindo carregamento...", flush=True)
    carregar_ms = medir_mediana_ms(lambda: carregar_mapa(str(caminho)))
    print("  Medindo indice...", flush=True)
    indice_ms = medir_mediana_ms(lambda: criar_indice_segmentos(grafo, pontos))

    # Cliques simulados em dois pontos do meio de ruas do mapa.
    p1 = ponto_medio(indice, pontos, 0)
    p2 = ponto_medio(indice, pontos, len(indice["segmentos"]) // 2)
    print("  Medindo localizacao do clique...", flush=True)
    localizar_ms = medir_mediana_ms(
        lambda: localizar_ponto_na_via(indice, pontos, *p1)
    )
    locais = [
        localizar_ponto_na_via(indice, pontos, *p1),
        localizar_ponto_na_via(indice, pontos, *p2),
    ]
    print("  Medindo vertices temporarios...", flush=True)
    preparar_ms = medir_mediana_ms(
        lambda: inserir_pontos_temporarios(grafo, pontos, locais)
    )

    # As buscas usam os mesmos pares para permitir comparação justa.
    # Os dicionários pontos/vias são fornecidos como ocorre no frontend.
    def medir_buscas(operacao):
        if not pares:
            return None
        return median([
            medir_mediana_ms(lambda o=o, d=d: operacao(o, d))
            for o, d in pares
        ])

    print("  Medindo Dijkstra por distancia...", flush=True)
    distancia_ms = medir_buscas(
        lambda o, d: calcular_menor_caminho(
            grafo, o, d, criterio="distancia", pontos=pontos, vias=vias
        )
    )
    print("  Medindo Dijkstra por tempo...", flush=True)
    tempo_ms = medir_buscas(
        lambda o, d: calcular_menor_caminho(
            grafo, o, d, criterio="tempo", pontos=pontos, vias=vias
        )
    )
    print("  Medindo comparacao das duas rotas...", flush=True)
    comparacao_ms = medir_buscas(
        lambda o, d: comparar_rotas(grafo, o, d, pontos, vias)
    )

    return {
        "mapa": caminho.name,
        "vertices": len(grafo.vertices),
        "arestas": len(grafo.arestas),
        "segmentos_fisicos": len(indice["segmentos"]),
        "pares_avaliados": len(pares),
        "carregamento_ms": carregar_ms,
        "indice_ms": indice_ms,
        "localizacao_clique_ms": localizar_ms,
        "vertices_temporarios_ms": preparar_ms,
        "dijkstra_distancia_ms": distancia_ms,
        "dijkstra_tempo_ms": tempo_ms,
        "comparacao_ms": comparacao_ms,
    }


def salvar_resultados(resultados):
    """Grava tambem resultados parciais apos concluir cada mapa."""
    if not resultados:
        return
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with SAIDA.open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = DictWriter(arquivo, fieldnames=list(resultados[0]))
        escritor.writeheader()
        for registro in resultados:
            escritor.writerow({
                chave: (f"{valor:.6f}" if isinstance(valor, float) else valor)
                if valor is not None else ""
                for chave, valor in registro.items()
            })


def principal():
    arquivos = sorted(PASTA_DADOS.glob("*.json"))
    if not arquivos:
        raise SystemExit(
            "Nenhum JSON encontrado em dados/. Salve seus mapas nessa pasta primeiro."
        )

    resultados = []
    for caminho in arquivos:
        print(f"\nAnalisando: {caminho.name}")
        try:
            registro = analisar_mapa(caminho)
        except (OSError, ValueError, KeyError) as erro:
            print(f"  Ignorado devido a erro de dados: {erro}")
            continue
        resultados.append(registro)
        salvar_resultados(resultados)
        print(f"  Resultado deste mapa salvo em: {SAIDA}", flush=True)
        print(
            f"  Grafo: {registro['vertices']} vertices, "
            f"{registro['arestas']} arestas; "
            f"{registro['pares_avaliados']} pares alcancaveis"
        )
        for campo in (
            "carregamento_ms", "indice_ms", "localizacao_clique_ms",
            "vertices_temporarios_ms", "dijkstra_distancia_ms",
            "dijkstra_tempo_ms", "comparacao_ms",
        ):
            valor = registro[campo]
            print(f"  {campo}: {valor:.3f} ms" if valor is not None
                  else f"  {campo}: sem pares alcancaveis")

    if not resultados:
        raise SystemExit("Nenhum mapa pôde ser analisado.")

    print(f"\nResultados registrados em: {SAIDA}")
    print(
        f"Metodologia: um aquecimento e {REPETICOES} execucoes por caso; "
        f"mediana; ate {MAX_PARES} pares dirigidos alcancaveis por mapa (semente {SEMENTE})."
    )
    print(
        "Observacao: carregamento, localizacao, insercao e Dijkstra "
        "foram medidos separadamente. Nao some as medianas como se fossem "
        "um tempo total medido."
    )


if __name__ == "__main__":
    principal()
