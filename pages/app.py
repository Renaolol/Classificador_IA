import hashlib
import pandas as pd
from pathlib import Path
from typing import List, Optional, Tuple
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

if status_plano.get("pendencias"):
    st.warning("Você possui créditos pendentes aguardando pagamento. Use a tela de planos para registrar o pagamento.")

if status_plano["restantes"] <= 0:
    st.error("Seu saldo de itens acabou. Recarregue o plano ou adicione limite extra na tela de planos.")
    st.stop()

DISPLAY_COLUMNS = ["Descrição_x","NCM_x","CST","cClassTrib","DescricaoClassTrib","pRedIBS","pRedCBS"]

def _reset_upload_state():
    for key in ("last_upload_key", "last_df", "last_excel", "last_status_msg"):
        st.session_state.pop(key, None)

def _file_signature(empresa: int, file) -> Optional[Tuple[str, int, str]]:
    if not file:
        return None
    content = file.getvalue()
    digest = hashlib.md5(content).hexdigest()
    size = len(content)
    name = file.name or "upload"
    return (f"{empresa}", size, digest, name)

# -----------------------
# Planilhas Excel
produtos = st.file_uploader("Selecione o Excel")

if not produtos:
    _reset_upload_state()

if produtos:
    signature = _file_signature(empresa_id, produtos)
    cached_key = st.session_state.get("last_upload_key")
    cached_df = st.session_state.get("last_df")
    cached_bytes = st.session_state.get("last_excel")
    already_processed = cached_key == signature and cached_df is not None and cached_bytes is not None

    if not already_processed:
        produtos_bytes = produtos.getvalue()
        produtos_df = extract_data_excel(BytesIO(produtos_bytes))
        total_itens = produtos_df.shape[0]
        if total_itens > status_plano["restantes"]:
            st.error(
                f"O arquivo possui {total_itens} itens, mas restam apenas {status_plano['restantes']} no seu plano. "
                "Atualize o plano ou envie um arquivo menor."
            )
            st.stop()
        base_dir = Path(__file__).resolve().parents[1]
        database_dir = base_dir / "database"
        lei_complementar = database_dir / "Lei 214 NCMs - CBSs .xlsx"
        cst_cclass_excel = database_dir / "CST_cclass.xlsx"
        lei_df = extract_data_excel(lei_complementar)
        cst_cclass_excel_df = extract_data_excel(cst_cclass_excel)
        _ = lei_df

        cst_prefixes = build_cst_prefixes(cst_cclass_excel_df)
        default_rule = get_default_rule(cst_cclass_excel_df)

        produtos_df["NCM"] = normalize_ncm(produtos_df["NCM"])
        description_col = "Descrição" if "Descrição" in produtos_df.columns else None
        df_merged = merge_by_prefix(
            produtos_df,
            cst_prefixes,
            description_column=description_col,
            fallback_row=default_rule,
        )
        novos_classificados = df_merged.shape[0]
        total_atual = registrar_classificacao(empresa_id, novos_classificados)
        status_plano = obter_status_plano(empresa_id)
        render_status(status_plano)
        success_msg = (
            f"{novos_classificados} itens contabilizados. Total acumulado do plano: "
            f"{total_atual}/{status_plano['limite']}."
        )
        st.success(success_msg)
        df_display = df_merged[DISPLAY_COLUMNS]
        buffer = BytesIO()
        df_display.to_excel(buffer, index=False)
        buffer.seek(0)

        st.session_state["last_upload_key"] = signature
        st.session_state["last_df"] = df_display
        st.session_state["last_excel"] = buffer.getvalue()
        st.session_state["last_status_msg"] = success_msg
    else:
        df_display = cached_df
        success_msg = st.session_state.get("last_status_msg")
        if success_msg:
            st.info("Este arquivo já foi processado nesta sessão. Use o download abaixo ou envie um novo arquivo.")
            st.success(success_msg)

    df_to_show = st.session_state.get("last_df")
    excel_bytes = st.session_state.get("last_excel")
    if df_to_show is not None and excel_bytes is not None:
        st.write(df_to_show)
        st.download_button(
            label="Baixar Excel",
            data=BytesIO(excel_bytes),
            file_name="df_merged.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
