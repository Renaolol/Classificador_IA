import pandas as pd
from pathlib import Path
from typing import List, Optional
from dependencies import *
from dotenv import load_dotenv
import streamlit as st
from io import BytesIO

st.set_page_config("Classificador",layout="wide")
st.title("Classificador Tributário de Produtos")

load_dotenv()

# -----------------------
# Planilhas Excel
produtos = st.file_uploader("Selecione o Excel")
if produtos:
    lei_complementar = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\database\Lei 214 NCMs - CBSs .xlsx")
    cst_cclass_excel = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\database\CST_cclass.xlsx")
    # -----------------------
    # Load spreadsheets
    produtos_df = extract_data_excel(produtos)
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

