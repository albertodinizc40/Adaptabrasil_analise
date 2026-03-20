import pandas as pd
import streamlit as st
import graphviz
from html import escape

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
    except Exception:
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


def buscar_ancestrais(df, indicador_id):
    mapa_pai = df.set_index("indicator_id")["parent_id"].to_dict()
    ancestrais = []
    atual = normalizar_id(indicador_id)

    while True:
        pai = normalizar_id(mapa_pai.get(atual, ""))
        if not pai or pai == atual:
            break
        ancestrais.append(pai)
        atual = pai

    ancestrais.reverse()
    return ancestrais


def buscar_descendentes(df, indicador_id):
    mapa_filhos = df.groupby("parent_id")["indicator_id"].apply(list).to_dict()

    visitados = []
    fila = [normalizar_id(indicador_id)]

    while fila:
        atual = fila.pop(0)
        filhos = mapa_filhos.get(atual, [])
        for filho in filhos:
            filho = normalizar_id(filho)
            if filho and filho not in visitados:
                visitados.append(filho)
                fila.append(filho)

    return visitados


def montar_arvore(df, indicador_selecionado):
    ancestrais = buscar_ancestrais(df, indicador_selecionado)
    descendentes = buscar_descendentes(df, indicador_selecionado)

    ids_cadeia = ancestrais + [indicador_selecionado] + descendentes
    df_cadeia = df[df["indicator_id"].isin(ids_cadeia)].copy()

    tipo_no = []
    for _, row in df_cadeia.iterrows():
        iid = row["indicator_id"]
        if iid == indicador_selecionado:
            tipo_no.append("selecionado")
        elif iid in ancestrais:
            tipo_no.append("ancestral")
        else:
            tipo_no.append("descendente")

    df_cadeia["tipo_no"] = tipo_no
    return ancestrais, descendentes, df_cadeia


def gerar_grafo(df_cadeia, indicador_selecionado):
    dot = graphviz.Digraph()
    dot.attr(rankdir="TB")
    dot.attr("node", shape="box", style="rounded,filled", fontname="Arial")

    for _, row in df_cadeia.iterrows():
        iid = row["indicator_id"]
        titulo = str(row.get("title", ""))
        level = row.get("level_num", "")
        label = f"{titulo}\nID: {iid} | level: {level}"

        if iid == indicador_selecionado:
            dot.node(iid, label=label, fillcolor="#1f77b4", fontcolor="white")
        elif row["tipo_no"] == "ancestral":
            dot.node(iid, label=label, fillcolor="#f2c14e")
        else:
            dot.node(iid, label=label, fillcolor="#8ecae6")

    for _, row in df_cadeia.iterrows():
        pai = normalizar_id(row.get("parent_id", ""))
        filho = normalizar_id(row.get("indicator_id", ""))
        if pai and pai in df_cadeia["indicator_id"].tolist():
            dot.edge(pai, filho)

    return dot


def render_tabela_html(df_tabela):
    if df_tabela.empty:
        return "<p>Nenhum registro encontrado.</p>"

    colunas = list(df_tabela.columns)

    html = """
    <style>
    .wrap-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    .wrap-table th, .wrap-table td {
        border: 1px solid #333;
        padding: 8px;
        text-align: left;
        vertical-align: top;
        white-space: normal !important;
        word-wrap: break-word;
        max-width: 280px;
    }
    .wrap-table th {
        background-color: #1f1f1f;
        color: white;
        position: sticky;
        top: 0;
    }
    .row-ancestral {
        background-color: #fff3cd;
        color: #000;
    }
    .row-selecionado {
        background-color: #cfe2ff;
        color: #000;
        font-weight: bold;
    }
    .row-descendente {
        background-color: #d9f2e6;
        color: #000;
    }
    </style>
    <table class="wrap-table">
        <thead>
            <tr>
    """

    for col in colunas:
        html += f"<th>{escape(str(col))}</th>"

    html += "</tr></thead><tbody>"

    for _, row in df_tabela.iterrows():
        classe = "row-descendente"
        if row.get("tipo_no", "") == "ancestral":
            classe = "row-ancestral"
        elif row.get("tipo_no", "") == "selecionado":
            classe = "row-selecionado"

        html += f'<tr class="{classe}">'
        for col in colunas:
            valor = row.get(col, "")
            html += f"<td>{escape(str(valor))}</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return html


df = carregar_dados()

st.title("AdaptaBrasil - Explorador de Indicadores")
st.write("Escolha um level apenas para localizar um indicador. Depois o sistema mostra toda a cadeia: pais, item selecionado e filhos.")

if "indicator_id" not in df.columns or "parent_id" not in df.columns or "title" not in df.columns or "level_num" not in df.columns:
    st.error("A base precisa conter indicator_id, parent_id, title e level_num.")
    st.stop()

col1, col2 = st.columns([1, 3])

with col1:
    niveis = sorted([int(x) for x in df["level_num"].dropna().unique().tolist()])
    level_referencia = st.selectbox("Level de referência", niveis)

df_level = df[df["level_num"] == level_referencia].copy().sort_values("title")

with col2:
    opcoes = df_level[["indicator_id", "title"]].drop_duplicates().copy()
    opcoes["label"] = opcoes["title"].astype(str) + " | ID " + opcoes["indicator_id"].astype(str)
    indicador_label = st.selectbox("Selecione o indicador", opcoes["label"].tolist())

indicador_id = opcoes.loc[opcoes["label"] == indicador_label, "indicator_id"].iloc[0]

ancestrais, descendentes, df_cadeia = montar_arvore(df, indicador_id)

ordem_ids = ancestrais + [indicador_id] + descendentes
ordem_map = {iid: i for i, iid in enumerate(ordem_ids)}
df_cadeia["ordem"] = df_cadeia["indicator_id"].map(ordem_map)

st.subheader("Resumo da cadeia")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total na cadeia", len(df_cadeia))
c2.metric("Pais acima", len(ancestrais))
c3.metric("Filhos abaixo", len(descendentes))
c4.metric("Levels envolvidos", int(df_cadeia["level_num"].nunique()))

st.divider()

st.subheader("Fluxograma da cadeia")
grafo = gerar_grafo(df_cadeia, indicador_id)
st.graphviz_chart(grafo, use_container_width=True)

st.divider()

item_sel = df[df["indicator_id"] == indicador_id].head(1)
if not item_sel.empty:
    item = item_sel.iloc[0]

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

st.subheader("Tabela da cadeia completa")

filtro_texto = st.text_input("Buscar dentro da cadeia")

df_tabela = df_cadeia.copy()

if filtro_texto.strip():
    termo = filtro_texto.lower().strip()
    mascara = pd.Series(False, index=df_tabela.index)

    for col in ["title", "indicator_name", "shortname", "simple_description", "complete_description", "sep_description"]:
        if col in df_tabela.columns:
            mascara = mascara | df_tabela[col].astype(str).str.lower().str.contains(termo, na=False)

    df_tabela = df_tabela[mascara].copy()

colunas_exibir = [
    "tipo_no",
    "level_num",
    "indicator_id",
    "parent_id",
    "indicator_name",
    "title",
    "shortname",
    "simple_description",
    "complete_description",
    "sep_description",
    "climate_hazard",
    "measurement_unit",
    "disturbance",
    "schema",
    "ordem"
]

colunas_exibir = [c for c in colunas_exibir if c in df_tabela.columns]

df_tabela = df_tabela[colunas_exibir].sort_values(["ordem", "level_num"], na_position="last")

st.markdown(render_tabela_html(df_tabela), unsafe_allow_html=True)

st.divider()

st.subheader("Blocos da cadeia")

aba1, aba2, aba3 = st.tabs(["Pais", "Selecionado", "Filhos"])

with aba1:
    df_pais = df_cadeia[df_cadeia["tipo_no"] == "ancestral"].copy().sort_values("level_num")
    colunas_pais = [c for c in colunas_exibir if c in df_pais.columns]
    st.markdown(render_tabela_html(df_pais[colunas_pais]), unsafe_allow_html=True)

with aba2:
    df_sel = df_cadeia[df_cadeia["tipo_no"] == "selecionado"].copy()
    colunas_sel = [c for c in colunas_exibir if c in df_sel.columns]
    st.markdown(render_tabela_html(df_sel[colunas_sel]), unsafe_allow_html=True)

with aba3:
    df_filhos = df_cadeia[df_cadeia["tipo_no"] == "descendente"].copy().sort_values(["level_num", "title"])
    colunas_filhos = [c for c in colunas_exibir if c in df_filhos.columns]
    st.markdown(render_tabela_html(df_filhos[colunas_filhos]), unsafe_allow_html=True)
