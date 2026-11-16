"""Regras básicas para carros particulares, sem condições de horário.

Referências: wiki.openstreetmap.org/wiki/Key:access e /wiki/Key:oneway.
O perfil considera trânsito de passagem. Acesso restrito ao destino, clientes
ou proprietários é excluído nesta versão, mesmo que possa atender alguns usuários.
"""


VIAS_USUAIS_CARROS = {
    "motorway", "motorway_link", "trunk", "trunk_link",
    "primary", "primary_link", "secondary", "secondary_link",
    "tertiary", "tertiary_link", "unclassified", "residential",
    "living_street", "service",
}
VIAS_COM_PERMISSAO_EXPLICITA = {
    "pedestrian", "footway", "cycleway", "path", "bridleway", "track", "road",
}
ACESSOS_PERMITIDOS = {"yes", "permissive", "designated"}
CHAVES_ACESSO = ("motorcar", "motor_vehicle", "vehicle", "access")


def sentido_da_via(tags):
    """Retorna 1 (ordem dos nodes), -1 (ordem inversa), 0 (ambos) ou None.

    None indica um valor não suportado, como reversible ou alternating.
    Tags mais específicas para carros têm prioridade sobre a tag genérica.
    """
    for chave in ("oneway:motorcar", "oneway:motor_vehicle", "oneway:vehicle", "oneway"):
        if chave in tags:
            valor = tags[chave].strip().lower()
            if valor in {"yes", "true", "1"}:
                return 1
            if valor in {"no", "false", "0"}:
                return 0
            if valor == "-1":
                return -1
            return None

    if tags.get("junction") == "roundabout" or tags.get("highway") == "motorway":
        return 1
    return 0


def motivo_exclusao_carros(tags):
    """Retorna o motivo da exclusão, ou None quando a via pode ser usada."""
    tipo = tags.get("highway")
    if tipo not in VIAS_USUAIS_CARROS | VIAS_COM_PERMISSAO_EXPLICITA:
        return f"Tipo de via fora do perfil de carros: {tipo or 'sem highway'}"
    if tags.get("area") == "yes":
        return "Área sem percurso viário definido"

    # Não interpreta condições temporais nem permissões diferentes por sentido.
    # Excluir essas vias evita tratá-las silenciosamente como acesso irrestrito.
    for chave in tags:
        partes = chave.split(":")
        if partes[0] in (*CHAVES_ACESSO, "oneway") and any(
            parte in {"conditional", "forward", "backward"} for parte in partes[1:]
        ):
            return f"Regra ainda não suportada: {chave}"

    for chave in CHAVES_ACESSO:
        if chave in tags:
            acesso = tags[chave].strip().lower()
            if acesso not in ACESSOS_PERMITIDOS:
                return f"Acesso fora do perfil de passagem: {chave}={acesso}"
            # A regra mais específica substitui as regras de acesso mais gerais.
            break

    if tipo in VIAS_COM_PERMISSAO_EXPLICITA and not any(
        tags.get(chave, "").strip().lower() in ACESSOS_PERMITIDOS
        for chave in CHAVES_ACESSO[:-1]
    ):
        return f"Via {tipo} sem permissão explícita para veículos/carros"
    if sentido_da_via(tags) is None:
        return "Sentido de circulação ainda não suportado"
    return None


def filtrar_vias_carros(vias):
    """Retorna (vias_permitidas, motivos_das_excluidas), sem alterar a entrada."""
    permitidas = {}
    excluidas = {}
    for identificador, via in vias.items():
        motivo = motivo_exclusao_carros(via["tags"])
        if motivo is None:
            permitidas[identificador] = via
        else:
            excluidas[identificador] = motivo
    return permitidas, excluidas
