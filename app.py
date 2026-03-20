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

    for col in ["indicator_id", "parent_id"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    if "level_num" in df.columns:
        df["level_num"] = pd.to_numeric(df["level_num"], errors="coerce")

    return df

def buscar_descendentes(df, indicador_raiz):
    filhos_mapa = df.groupby("parent_id")["indicator_id"].apply(list).to_dict()

    descendentes = []
    fila = [str(indicador_raiz)]

    while fila:
        atual = fila.pop(0)
        filhos = filhos_mapa.get(atual, [])
        for filho in filhos:
            if filho not in descendentes:
                descendentes.append(filho)
                fila.append(filho)

    return descendentes

df = carregar_dados()

st.title("AdaptaBrasil - Explorador de Indicadores")
st.write("Selecione um nível e um indicador. O painel exibirá todos os indicadores que estão abaixo dele na hierarquia.")

if "level_num" not in df.columns:
    st.error("A coluna level_num não foi encontrada.")
    st.stop()

if "title" not in df.columns:
    st.error("A coluna title não foi encontrada.")
    st.stop()

if "indicator_id" not in df.columns or "parent_id" not in df.columns:
    st.error("As colunas indicator_id e parent_id são obrigatórias.")
    st.stop()

col_filtro1, col_filtro2 = st.columns([1, 3])

with col_filtro1:
    niveis_disponiveis = sorted([int(x) for x in df["level_num"].dropna().unique().tolist()])
    nivel_escolhido = st.selectbox("Selecione o level", niveis_disponiveis)

df_nivel = df[df["level_num"] == nivel_escolhido].copy()
df_nivel = df_nivel.sort_values("title")

with col_filtro2:
    opcoes = df_nivel[["indicator_id", "title"]].drop_duplicates().copy()
    opcoes["label"] = opcoes["title"] + " | ID " + opcoes["indicator_id"]
    indicador_label = st.selectbox("Selecione o indicador pelo title", opcoes["label"].tolist())

indicador_id_selecionado = opcoes.loc[opcoes["label"] == indicador_label, "indicator_id"].iloc[0]

linha_selecionada = df[df["indicator_id"] == indicador_id_selecionado].head(1)

descendentes = buscar_descendentes(df, indicador_id_selecionado)
ids_filtrados = [indicador_id_selecionado] + descendentes

df_filtrado = df[df["indicator_id"].isin(ids_filtrados)].copy()
df_filtrado = df_filtrado.sort_values(["level_num", "title"])

st.subheader("Visão geral")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Total de indicadores", len(df_filtrado))

with c2:
    st.metric("Níveis envolvidos", df_filtrado["level_num"].nunique())

with c3:
    st.metric("Menor level", int(df_filtrado["level_num"].min()) if len(df_filtrado) > 0 else 0)

with c4:
    st.metric("Maior level", int(df_filtrado["level_num"].max()) if len(df_filtrado) > 0 else 0)

st.divider()

st.subheader("Detalhes do indicador selecionado")

if not linha_selecionada.empty:
    item = linha_selecionada.iloc[0]

    info1, info2 = st.columns(2)

    with info1:
        st.write(f"Title: {item.get('title', '')}")
        st.write(f"Indicator ID: {item.get('indicator_id', '')}")
        st.write(f"Parent ID: {item.get('parent_id', '')}")
        st.write(f"Level: {item.get('level_num', '')}")
        st.write(f"Shortname: {item.get('shortname', '')}")

    with info2:
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

st.subheader("Tabela com todos os indicadores abaixo do item selecionado")

busca = st.text_input("Buscar dentro da tabela filtrada")

if busca.strip():
    termo = busca.lower().strip()
    mascara = pd.Series(False, index=df_filtrado.index)

    for col in ["title", "indicator_name", "shortname", "simple_description", "complete_description", "sep_description"]:
        if col in df_filtrado.columns:
            mascara = mascara | df_filtrado[col].astype(str).str.lower().str.contains(termo, na=False)

    df_filtrado = df_filtrado[mascara].copy()

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

colunas_exibir = [c for c in colunas_exibir if c in df_filtrado.columns]

st.dataframe(
    df_filtrado[colunas_exibir],
    use_container_width=True,
    hide_index=True
)

st.divider()

st.subheader("Resumo por level dos indicadores filtrados")

resumo = (
    df_filtrado.groupby("level_num")
    .size()
    .reset_index(name="quantidade")
    .sort_values("level_num")
)

st.dataframe(resumo, use_container_width=True, hide_index=True)
