import pandas as pd
import streamlit as st

st.set_page_config(page_title="AdaptaBrasil", layout="wide")

ARQUIVO = "tabela_adapta_brasi.xlsx"
ABA = "General_Data_Base"

@st.cache_data
def carregar_dados():
    df = pd.read_excel(ARQUIVO, sheet_name=ABA)

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("").astype(str)

    if "indicator_id" in df.columns:
        df["indicator_id"] = df["indicator_id"].astype(str)

    if "parent_id" in df.columns:
        df["parent_id"] = df["parent_id"].astype(str)

    if "menu_structure" not in df.columns:
        df["menu_structure"] = ""

    def limpar_menu(x):
        x = str(x).strip()
        if x.lower() == "nan":
            return ""
        return x

    df["menu_structure"] = df["menu_structure"].apply(limpar_menu)

    separadores = [" > ", ">", " / ", "/", " | ", "|", " - "]

    def split_hierarquia(texto):
        partes = [texto]
        for sep in separadores:
            if sep in texto:
                partes = [p.strip() for p in texto.split(sep) if str(p).strip()]
                break
        return partes

    df["hierarquia_partes"] = df["menu_structure"].apply(split_hierarquia)

    max_niveis = max(df["hierarquia_partes"].apply(len).max(), 1)

    for i in range(max_niveis):
        df[f"nivel_{i+1}"] = df["hierarquia_partes"].apply(
            lambda x: x[i] if len(x) > i else ""
        )

    return df, max_niveis

df, max_niveis = carregar_dados()

st.title("AdaptaBrasil - Explorador de Indicadores")
st.write("Explore a hierarquia dos indicadores, filtre por nível e veja os detalhes completos.")

with st.sidebar:
    st.header("Filtros da hierarquia")

    df_filtrado = df.copy()

    filtros_escolhidos = {}

    for i in range(1, max_niveis + 1):
        col_nivel = f"nivel_{i}"

        opcoes = sorted([x for x in df_filtrado[col_nivel].unique().tolist() if str(x).strip() != ""])
        opcoes = ["Todos"] + opcoes

        escolha = st.selectbox(f"Nível {i}", opcoes, key=f"filtro_nivel_{i}")
        filtros_escolhidos[col_nivel] = escolha

        if escolha != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_nivel] == escolha].copy()

st.subheader("Visão geral")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Indicadores filtrados", len(df_filtrado))

with c2:
    if "indicator_id" in df_filtrado.columns:
        st.metric("IDs únicos", df_filtrado["indicator_id"].nunique())
    else:
        st.metric("IDs únicos", 0)

with c3:
    if "level_num" in df_filtrado.columns:
        st.metric("Profundidade máxima", int(pd.to_numeric(df_filtrado["level_num"], errors="coerce").max() or 0))
    else:
        st.metric("Profundidade máxima", 0)

with c4:
    if "parent_id" in df_filtrado.columns:
        qtd_com_pai = (df_filtrado["parent_id"].astype(str).str.strip() != "").sum()
        st.metric("Itens com parent_id", int(qtd_com_pai))
    else:
        st.metric("Itens com parent_id", 0)

st.divider()

st.subheader("Distribuição por nível")

colunas_niveis = [f"nivel_{i}" for i in range(1, max_niveis + 1)]
aba1, aba2 = st.tabs(["Tabela hierárquica", "Resumo por nível"])

with aba1:
    colunas_tabela_hierarquia = [c for c in colunas_niveis if c in df_filtrado.columns]
    colunas_tabela_hierarquia += [c for c in ["indicator_id", "title", "shortname", "level", "level_num", "parent_id"] if c in df_filtrado.columns]

    st.dataframe(
        df_filtrado[colunas_tabela_hierarquia],
        use_container_width=True,
        hide_index=True
    )

with aba2:
    for col_nivel in colunas_niveis:
        if col_nivel in df_filtrado.columns:
            resumo = (
                df_filtrado[df_filtrado[col_nivel].astype(str).str.strip() != ""]
                .groupby(col_nivel, dropna=False)
                .size()
                .reset_index(name="quantidade")
                .sort_values("quantidade", ascending=False)
            )
            st.write(f"Resumo de {col_nivel}")
            st.dataframe(resumo, use_container_width=True, hide_index=True)

st.divider()

st.subheader("Detalhes dos indicadores")

colunas_detalhes = [
    "indicator_id",
    "title",
    "shortname",
    "simple_description",
    "complete_description",
    "sep_description",
    "equation",
    "years",
    "years_description",
    "scenarios",
    "measurement_unit",
    "climate_hazard",
    "disturbance",
    "geometrytype",
    "legend",
    "schema",
    "imageurl",
    "level",
    "level_num",
    "parent_id"
]

colunas_detalhes = [c for c in colunas_detalhes if c in df_filtrado.columns]

busca = st.text_input("Buscar por título, shortname ou descrição")

if busca.strip():
    busca_lower = busca.lower().strip()

    mascara = pd.Series(False, index=df_filtrado.index)

    for col in ["title", "shortname", "simple_description", "complete_description", "sep_description"]:
        if col in df_filtrado.columns:
            mascara = mascara | df_filtrado[col].astype(str).str.lower().str.contains(busca_lower, na=False)

    df_detalhes = df_filtrado[mascara].copy()
else:
    df_detalhes = df_filtrado.copy()

st.dataframe(
    df_detalhes[colunas_detalhes],
    use_container_width=True,
    hide_index=True
)

st.divider()

st.subheader("Ficha resumida")

if len(df_detalhes) > 0:
    opcoes_indicador = (
        df_detalhes[["indicator_id", "title"]]
        .fillna("")
        .astype(str)
        .drop_duplicates()
    )
    opcoes_indicador["label"] = opcoes_indicador["indicator_id"] + " - " + opcoes_indicador["title"]

    indicador_escolhido = st.selectbox(
        "Selecione um indicador para ver os detalhes",
        opcoes_indicador["label"].tolist()
    )

    id_escolhido = indicador_escolhido.split(" - ")[0]
    detalhe = df_detalhes[df_detalhes["indicator_id"].astype(str) == id_escolhido].head(1)

    if not detalhe.empty:
        linha = detalhe.iloc[0]

        st.write(f"ID: {linha.get('indicator_id', '')}")
        st.write(f"Título: {linha.get('title', '')}")
        st.write(f"Shortname: {linha.get('shortname', '')}")
        st.write(f"Nível textual: {linha.get('level', '')}")
        st.write(f"Nível numérico: {linha.get('level_num', '')}")
        st.write(f"Parent ID: {linha.get('parent_id', '')}")

        st.write("Simple description")
        st.info(str(linha.get("simple_description", "")))

        st.write("Complete description")
        st.info(str(linha.get("complete_description", "")))

        st.write("SEP description")
        st.info(str(linha.get("sep_description", "")))
else:
    st.warning("Nenhum indicador encontrado com os filtros aplicados.")
