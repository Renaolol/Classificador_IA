import pandas as pd
from pathlib import Path
from typing import List, Optional
from dependencies import *
from dotenv import load_dotenv
import streamlit as st
from io import BytesIO

st.set_page_config("Classificador",layout="wide")
st.title("Classificador Tributário de Produtos - Gcont")
require_login()
load_dotenv()

empresa_id = st.session_state.get("empresa_codigo")
if not empresa_id:
    st.error("Não foi possível identificar sua empresa. Faça login novamente.")
    st.stop()

status_plano = obter_status_plano(empresa_id)
if not status_plano:
    st.error("Plano não configurado. Contate o suporte.")
    st.stop()

status_placeholder = st.empty()
progress_placeholder = st.empty()

def render_status(status: dict) -> None:
    status_placeholder.info(
        f"Plano {status['plano']} — {status['usados']} classificados de {status['limite']} "
        f"({status['restantes']} restantes)"
    )
    progress_placeholder.progress(min(status["usados"] / status["limite"], 1.0))

render_status(status_plano)

# -----------------------
# Planilhas Excel
produtos = st.file_uploader("Selecione o Excel")
if produtos:
    produtos_df = extract_data_excel(produtos)
    total_itens = produtos_df.shape[0]
    if total_itens > status_plano["restantes"]:
        st.error(
            f"O arquivo possui {total_itens} itens, mas restam apenas {status_plano['restantes']} no seu plano. "
            "Atualize o plano ou envie um arquivo menor."
        )
        st.stop()
    lei_complementar = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\database\Lei 214 NCMs - CBSs .xlsx")
    cst_cclass_excel = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\database\CST_cclass.xlsx")
    # -----------------------
    # Load spreadsheets

    lei_df = extract_data_excel(lei_complementar)
    cst_cclass_excel_df = extract_data_excel(cst_cclass_excel)

    # Placeholder so linting tools know the sheet was loaded intentionally
    _ = lei_df

    # Prepare CST mapping once
    cst_prefixes = build_cst_prefixes(cst_cclass_excel_df)
    default_rule = get_default_rule(cst_cclass_excel_df)

    # Apply merge to the full product list
    produtos_df["NCM"] = normalize_ncm(produtos_df["NCM"])
    description_col = "Descrição" if "Descrição" in produtos_df.columns else None
    df_merged = merge_by_prefix(
        produtos_df,
        cst_prefixes,
        description_column=description_col,
        fallback_row=default_rule,
    )
    novos_classificados = df_merged.shape[0]  # ou total_itens, conforme regra de negócio
    total_atual = registrar_classificacao(empresa_id, novos_classificados)
    status_plano = obter_status_plano(empresa_id)
    render_status(status_plano)
    st.success(
        f"{novos_classificados} itens contabilizados. Total acumulado do plano: {total_atual}/{status_plano['limite']}."
    )
    st.write(df_merged[["Descrição_x","NCM_x","CST","cClassTrib","DescricaoClassTrib","pRedIBS","pRedCBS"]])
    buffer = BytesIO()
    df_merged[["Descrição_x","NCM_x","CST","cClassTrib","DescricaoClassTrib","pRedIBS","pRedCBS"]].to_excel(buffer, index=False)
    buffer.seek(0)  # reposiciona para o início antes do download
    st.download_button(
        label="Baixar Excel",
        data=buffer,
        file_name="df_merged.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
