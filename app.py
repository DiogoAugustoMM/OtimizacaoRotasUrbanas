"""Ponto de entrada da interface do projeto."""

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Rotas urbanas", page_icon="🗺️", layout="wide")
    st.title("Otimização de rotas urbanas com base em mapas")
    st.write("Projeto acadêmico de Grafos com dados do OpenStreetMap.")
    st.info(
        "Estrutura inicial pronta. A consulta à Overpass API, a conversão dos "
        "mapas, os algoritmos de grafos e a visualização serão desenvolvidos "
        "pelos integrantes nas próximas etapas."
    )


if __name__ == "__main__":
    main()
