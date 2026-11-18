"""Interface do projeto: seleção de origem e destino e rota no mapa."""

from pathlib import Path

import streamlit as st

from mapas.conversor import carregar_mapa
from visualizacao.mapa import criar_mapa, vertice_mais_proximo

try:
    from streamlit_folium import st_folium
except ImportError:  # pacote de exibição do Folium no Streamlit
    st_folium = None

from resultados import comparar_rotas

PASTA_DADOS = Path(__file__).resolve().parent / "dados"

ESTILO = """
<style>
.block-container {padding: 2.2rem 2rem 1rem 2rem; max-width: 100%;}
h1 {font-size: 1.9rem !important; padding-bottom: .2rem;}
.dica {font-size: .95rem; margin: 0 0 1rem 0; padding-left: .8rem;
       border-left: 3px solid #1565C0;}
.trajeto {position: relative; margin-bottom: 1rem;}
.trajeto::before {content: ""; position: absolute; left: 9px; top: 24px;
                  bottom: 24px; width: 2px; background: #C9D3DB;}
.trajeto.pronto::before {background: #1565C0;}
.ponto {position: relative; display: flex; gap: .9rem; align-items: flex-start;
        padding: .6rem 0;}
.marca {flex: 0 0 20px; height: 20px; border-radius: 50%; margin-top: 2px;
        border: 3px solid #fff; box-shadow: 0 0 0 2px currentColor;
        background: currentColor; z-index: 1;}
.marca.origem {color: #2E7D32;}
.marca.destino {color: #C62828;}
.marca.vazio {color: #AEB9C2; background: #fff;}
.nome {font-weight: 600; line-height: 1.25;}
.nome.apagado {font-weight: 400; opacity: .55;}
.detalhe {font-size: .85rem; opacity: .7;}
</style>
"""


@st.cache_resource(show_spinner="Convertendo o mapa em grafo...")
def carregar(caminho):
    return carregar_mapa(caminho)


def iniciar_estado():
    for chave, valor in (("origem", None), ("destino", None), ("ultimo_clique", None)):
        st.session_state.setdefault(chave, valor)


def formatar_distancia(metros):
    return f"{metros / 1000:.2f} km" if metros >= 1000 else f"{metros:.0f} m"

def formatar_tempo(segundos):
    minutos = round(segundos / 60)
    if minutos < 1:
        return f"{segundos:.0f} s"
    if minutos < 60:
        return f"{minutos} min"
    horas, mins = divmod(minutos, 60)
    return f"{horas}h {mins:02d}min"


def dica(origem, destino):
    if origem is None:
        return "Clique no mapa para escolher a origem."
    if destino is None:
        return "Agora clique no mapa para escolher o destino."
    return "Trajeto definido. Clique no mapa para começar outro."


def trajeto_html(grafo, origem, destino):
    def ponto(classe, titulo, vertice, vazio):
        if vertice is None:
            return ('<div class="ponto"><span class="marca vazio"></span><div>'
                    f'<div class="nome apagado">{vazio}</div></div></div>')
        c = grafo.vertices[vertice]
        return (f'<div class="ponto"><span class="marca {classe}"></span><div>'
                f'<div class="nome">{titulo}</div>'
                f'<div class="detalhe">Cruzamento {vertice} em '
                f'{c["latitude"]:.5f}, {c["longitude"]:.5f}</div></div></div>')

    pronto = "pronto" if origem is not None and destino is not None else ""
    return (f'<div class="trajeto {pronto}">'
            + ponto("origem", "Origem", origem, "Origem não definida")
            + ponto("destino", "Destino", destino, "Destino não definido")
            + "</div>")


def main() -> None:
    st.set_page_config(page_title="Rotas urbanas", page_icon="🗺️", layout="wide")
    st.markdown(ESTILO, unsafe_allow_html=True)
    iniciar_estado()

    st.title("Otimização de rotas urbanas")
    st.caption("Menor caminho sobre mapas do OpenStreetMap, com grafo e algoritmos "
               "implementados do zero.")

    arquivos = sorted(PASTA_DADOS.glob("*.json"))
    if not arquivos:
        st.warning("Nenhum mapa encontrado. Salve um JSON da Overpass na pasta `dados/`.")
        st.stop()

    with st.sidebar:
        st.header("Mapa")
        arquivo = st.selectbox("Arquivo", arquivos, format_func=lambda p: p.name)
        criterio_label = st.radio(
            "Critério de otimização",
            options=["Mais curta (Distância)", "Mais rápida (Tempo)"],
            index=0,
        )
        criterio = "tempo" if "Tempo" in criterio_label else "distancia"
        mostrar_ruas = st.checkbox("Mostrar ruas do grafo", value=False)

    try:
        grafo, pontos, vias = carregar(str(arquivo))
    except (OSError, ValueError) as erro:
        st.error(f"Não foi possível carregar o mapa: {erro}")
        st.stop()

    st.sidebar.caption(f"{len(grafo.vertices)} cruzamentos e "
                       f"{len(grafo.arestas)} trechos de rua no grafo.")

    if st_folium is None:
        st.error("Falta o pacote `streamlit-folium`. Rode "
                 "`pip install -r requirements.txt` e abra o app de novo.")
        st.stop()

    origem, destino = st.session_state.origem, st.session_state.destino

    # Calcula e compara as rotas por distância e tempo.
    ids_arestas, distancia, tempo, aviso, comparacao = (
        None, None, None, None, None
    )

    if origem is not None and destino is not None:
        if origem == destino:
            aviso = (
                "info",
                "Origem e destino caíram no mesmo cruzamento. "
                "Escolha pontos mais afastados."
            )
        else:
            comparacao = comparar_rotas(
                grafo, origem, destino, pontos, vias
            )

            if comparacao is None:
                aviso = (
                    "error",
                    "Não existe caminho entre esses dois pontos."
                )
            else:
                if criterio == "tempo":
                    resultado = comparacao["rota_tempo"]
                else:
                    resultado = comparacao["rota_distancia"]

                ids_arestas = resultado["arestas"]
                distancia = resultado["distancia_total"]
                tempo = resultado["tempo_total"]



    col_mapa, col_painel = st.columns([4, 1], gap="medium")

    with col_painel:
        st.subheader("Trajeto")
        st.markdown(f'<p class="dica">{dica(origem, destino)}</p>', unsafe_allow_html=True)
        st.markdown(trajeto_html(grafo, origem, destino), unsafe_allow_html=True)
        if distancia is not None:
            st.metric("Distância total", formatar_distancia(distancia))  # RF07
        if tempo is not None:
            st.metric("Tempo estimado", formatar_tempo(tempo))
        if comparacao is not None:
            with st.expander("Comparação das rotas", expanded=True):
                rota_curta = comparacao["rota_distancia"]
                rota_rapida = comparacao["rota_tempo"]

                st.write("**Mais curta (distância)**")
                st.write(
                    f"{formatar_distancia(rota_curta['distancia_total'])} | "
                    f"{formatar_tempo(rota_curta['tempo_total'])}"
                )

                st.write("**Mais rápida (tempo)**")
                st.write(
                    f"{formatar_distancia(rota_rapida['distancia_total'])} | "
                    f"{formatar_tempo(rota_rapida['tempo_total'])}"
                )

                if comparacao["mesmo_trajeto"]:
                    st.caption(
                        "Os dois critérios recomendam o mesmo trajeto."
                    )
                else:
                    distancia_extra = comparacao["distancia_adicional_metros"]
                    tempo_economizado = comparacao["tempo_economizado_segundos"]

                    st.caption(
                        f"A rota mais rápida percorre "
                        f"{distancia_extra:.0f} m a mais e economiza "
                        f"{tempo_economizado:.0f} segundos."
                    )

        if aviso:
            (st.error if aviso[0] == "error" else st.info)(aviso[1])
        if st.button("Limpar trajeto", disabled=origem is None):
            st.session_state.origem = None
            st.session_state.destino = None
            st.rerun()

    with col_mapa:
        mapa = criar_mapa(grafo, pontos, ids_arestas, origem, destino, mostrar_ruas)
        retorno = st_folium(mapa, height=720, use_container_width=True,
                            returned_objects=["last_clicked"], key="mapa")

    clique = (retorno or {}).get("last_clicked")
    if clique and clique != st.session_state.ultimo_clique:
        st.session_state.ultimo_clique = clique
        vertice = vertice_mais_proximo(grafo, clique["lat"], clique["lng"])
        if origem is None or destino is not None:
            # 1º clique, ou um clique novo com o trajeto já completo: recomeça.
            st.session_state.origem = vertice
            st.session_state.destino = None
        else:
            st.session_state.destino = vertice
        st.rerun()


if __name__ == "__main__":
    main()