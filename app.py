import pandas as pd
import streamlit as st

st.set_page_config(page_title="AdaptaBrasil", layout="wide")

ARQUIVO = "tabela_adapta_brasi.xlsx"
ABA = "General_Data_Base"

@st.cache_data
def carregar_dados():
    df = pd.read_excel(ARQUIVO, sheet_name=ABA)
    return df

df = carregar_dados()

st.title("AdaptaBrasil - Explorador de Indicadores")
st.write("Selecione um tema e navegue pela estrutura da base.")

for col in df.columns:
    if df[col].dtype == "object":
        df[col] = df[col].fillna("").astype(str)

st.subheader("Prévia da base")
st.dataframe(df.head(20), use_container_width=True)

st.subheader("Colunas disponíveis")
st.write(df.columns.tolist())
