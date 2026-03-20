import pandas as pd
import streamlit as st

st.set_page_config(page_title="AdaptaBrasil", layout="wide")

ARQUIVO = "tabela_adapta_brasi.xlsx"
ABA = "General_Data_Base"


def normalizar_id(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.lower() == "nan":
        return ""
    try:
        num = float(texto)
        if num.is_integer():
            return str(int(num))
        return str(num)
    except:
        return texto


@st.cache_data
def carregar_dados():
    df = pd.read_excel(ARQUIVO, sheet_name=ABA)

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("").astype(str)

    if "indicator_id" in df.columns:
        df["indicator_id"] = df["indicator_id"].apply(normalizar_id)

    if "parent_id" in df.columns:
        df["parent_id"] = df["parent_id"].apply(normalizar_id)

    if "level_num" in df.columns:
        df["level_num"] = pd.to_numeric(df["level_num"], errors="coerce")

    return df


def buscar_descendentes(df, id_raiz):
    id_raiz = normalizar_id(id_raiz)

    mapa_filhos = (
        df.groupby("parent_id")["indicator_id"]
        .apply(list)
        .to_dict()
    )

    visitados = set()
    fila = [id_raiz]

    while fila:
        atual = fila.pop(0)
        filhos = mapa_filhos.get(atual, [])
        for filho in filhos:
            filho = normalizar_id(filho)
            if filho and filho not in visitados:
                visitados.add(filho)
                fila.append(filho)

    return visitados


df = carregar_dados()

st.title("AdaptaBrasil - Explorador de Indicadores")
st.write("A tabela abaixo começa com todos os indicadores. Os filtros apenas refinam a visualização.")

if "indicator_id" not in df.columns or "parent_id" not in df.columns:
    st.error("As colunas indicator_id e parent_id são obrigatórias.")
    st.stop()

df_visual = df.copy()

col1, col2, col3 = st.columns([1, 2, 2])

with col1:
    niveis = sorted([int(x) for x in df["level_num"].dropna().unique().tolist()]) if "level_num" in df.columns else []
    filtro_level = st.selectbox("Filtrar por level", ["Todos"] + niveis)

with col2:
    opcoes_titles = (
        df[["indicator_id", "title", "level_num"]]
        .dropna(subset=["title"])
        .drop_duplicates()
        .copy()
    )

    if "level_num" in opcoes_titles.columns:
        opcoes_titles["label"] = opcoes_titles["title"].astype(str) + " | level " + opcoes_titles["level_num"].fillna(-1).astype(int).astype(str) + " | ID " + opcoes_titles["indicator_id"]
    else:
        opcoes_titles["label"] = opcoes_titles["title"].astype(str) + " | ID " + opcoes_titles["indicator_id"]

    filtro_indicador = st.selectbox(
        "Filtrar pela hierarquia de um indicador",
        ["Todos"] + sorted(opcoes_titles["label"].tolist())
    )

with col3:
    busca = st.text_input("Buscar por título ou descrição")

if filtro_level != "Todos":
    df_visual = df_visual[df_visual["level_num"] == int(filtro_level)].copy()

detalhe_item = None

if filtro_indicador != "Todos":
    linha_sel = opcoes_titles[opcoes_titles["label"] == filtro_indicador].head(1)
    if not linha_sel.empty:
        id_pai = normalizar_id(linha_sel.iloc[0]["indicator_id"])
        ids_desc = buscar_descendentes(df, id_pai)
        ids_filtrar = {id_pai} | ids_desc
        df_visual = df_visual[df_visual["indicator_id"].isin(ids_filtrar)].copy()
        detalhe_item = df[df["indicator_id"] == id_pai].head(1)

if busca.strip():
    termo = busca.lower().strip()
    mascara = pd.Series(False, index=df_visual.index)

    for col in ["title", "indicator_name", "shortname", "simple_description", "complete_description", "sep_description"]:
        if col in df_visual.columns:
            mascara = mascara | df_visual[col].astype(str).str.lower().str.contains(termo, na=False)

    df_visual = df_visual[mascara].copy()

st.subheader("Visão geral")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Indicadores visíveis", len(df_visual))
c2.metric("IDs únicos", df_visual["indicator_id"].nunique() if "indicator_id" in df_visual.columns else 0)
c3.metric("Levels visíveis", df_visual["level_num"].nunique() if "level_num" in df_visual.columns else 0)
c4.metric("Itens com parent_id", int((df_visual["parent_id"].astype(str).str.strip() != "").sum()) if "parent_id" in df_visual.columns else 0)

if detalhe_item is not None and not detalhe_item.empty:
    item = detalhe_item.iloc[0]

    st.divider()
    st.subheader("Detalhes do indicador selecionado")

    a, b = st.columns(2)

    with a:
        st.write(f"Title: {item.get('title', '')}")
        st.write(f"Indicator ID: {item.get('indicator_id', '')}")
        st.write(f"Parent ID: {item.get('parent_id', '')}")
        st.write(f"Level: {item.get('level_num', '')}")
        st.write(f"Shortname: {item.get('shortname', '')}")

    with b:
        st.write(f"Indicator name: {item.get('indicator_name', '')}")
        st.write(f"Climate hazard: {item.get('climate_hazard', '')}")
        st.write(f"Measurement unit: {item.get('measurement_unit', '')}")
        st.write(f"Disturbance: {item.get('disturbance', '')}")
        st.write(f"Schema: {item.get('schema', '')}")

    st.write("Simple description")
    st.info(str(item.get("simple_description", "")))

    st.write("Complete description")
    st.info(str(item.get("complete_description", "")))

    if "sep_description" in df.columns:
        st.write("SEP description")
        st.info(str(item.get("sep_description", "")))

st.divider()
st.subheader("Tabela com todos os indicadores")

colunas_exibir = [
    "indicator_id",
    "parent_id",
    "level_num",
    "indicator_name",
    "title",
    "shortname",
    "simple_description",
    "complete_description",
    "sep_description",
    "climate_hazard",
    "measurement_unit",
    "disturbance",
    "schema"
]

colunas_exibir = [c for c in colunas_exibir if c in df_visual.columns]

st.dataframe(
    df_visual[colunas_exibir].sort_values(["level_num", "title"], na_position="last"),
    use_container_width=True,
    hide_index=True
)

st.divider()
st.subheader("Resumo por level")

if "level_num" in df_visual.columns:
    resumo = (
        df_visual.groupby("level_num")
        .size()
        .reset_index(name="quantidade")
        .sort_values("level_num")
    )
    st.dataframe(resumo, use_container_width=True, hide_index=True)
