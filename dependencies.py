import pandas as pd
from pathlib import Path
import requests
import os
import base64
from requests_pkcs12 import Pkcs12Adapter
from pprint import pprint
from dotenv import load_dotenv
import json
from typing import List, Optional
import psycopg2
import streamlit as st
from time import sleep
import streamlit_authenticator as stauth
from functools import lru_cache

def extract_data_excel(data):
    """Extract data from excel"""
    data_excel = pd.read_excel(data)
    data_df = pd.DataFrame(data_excel)

    return data_df

def get_api_conformidade_facil(certificado,senha):
    session = requests.Session()  
    session.mount("https://",Pkcs12Adapter(pkcs12_filename=certificado,pkcs12_password=senha))
    url = "https://cff.svrs.rs.gov.br/api/v1/consultas/classTrib"
    #Parametros aceitos cst ou NomeCst
    response = session.get(url)
    #Utilizado pprint para uma visualização encadeada
    return response

def _hash_password(password: str) -> str:
    """Gera hash compatível com streamlit-authenticator, independente da versão."""
    try:
        return stauth.Hasher([password]).generate()[0]
    except Exception:
        hasher = getattr(stauth, "Hasher")()
        return hasher.hash(password)

def normalize_ncm(series: pd.Series, length: int = 8) -> pd.Series:
    """Keep only digits and left-pad with zeros."""
    clean = (
        series.fillna("")
        .astype(str)
        .str.replace(r"\D", "", regex=True)
        .str.strip()
    )
    clean = clean.replace("", pd.NA)
    return clean.str.zfill(length)

def _parse_required_keywords(value: object) -> List[str]:
    if not isinstance(value, str):
        return []
    return [token.strip().lower() for token in value.split(";") if token.strip()]

def build_cst_prefixes(cst_df: pd.DataFrame) -> pd.DataFrame:
    """Explode allowed_ncmlist into normalized prefixes."""
    exploded = (
        cst_df.copy()
        .assign(ncm_prefix=cst_df["allowed_ncmlist"].fillna("").astype(str).str.split(";"))
        .explode("ncm_prefix", ignore_index=True)
    )

    exploded["ncm_prefix"] = (
        exploded["ncm_prefix"].astype(str)
        .str.replace(r"\D", "", regex=True)
        .str.strip()
    )

    exploded = exploded[exploded["ncm_prefix"] != ""].copy()
    exploded["prefix_len"] = exploded["ncm_prefix"].str.len()
    exploded["required_keywords_list"] = exploded["required_keywords"].apply(_parse_required_keywords)
    return exploded

def _keyword_match(description: str, keywords: List[str]) -> bool:
    if not keywords:
        return True
    if not isinstance(description, str) or not description:
        return False
    return any(token in description for token in keywords)

def _apply_fallback(df: pd.DataFrame, fallback_row: Optional[pd.Series]) -> pd.DataFrame:
    if fallback_row is None or df.empty:
        return df

    if "CST" in df.columns:
        needs_fallback = df["CST"].isna()
    elif "cClassTrib" in df.columns:
        needs_fallback = df["cClassTrib"].isna()
    else:
        needs_fallback = pd.Series(True, index=df.index)

    if not needs_fallback.any():
        return df

    fallback_data = fallback_row.drop(labels=["allowed_ncmlist", "required_keywords"], errors="ignore")
    for col, value in fallback_data.items():
        if col not in df.columns:
            df[col] = pd.NA
        df.loc[needs_fallback, col] = value

    return df

def merge_by_prefix(
    items_df: pd.DataFrame,
    cst_prefix_df: pd.DataFrame,
    description_column: Optional[str] = None,
    fallback_row: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Attach each item to the most specific CST prefix available."""
    if cst_prefix_df.empty:
        return _apply_fallback(items_df.copy(), fallback_row)

    lens = sorted(cst_prefix_df["prefix_len"].unique())
    if not lens:
        return _apply_fallback(items_df.copy(), fallback_row)

    if description_column is None:
        description_column = next((col for col in items_df.columns if "desc" in col.lower()), None)

    items_with_ids = items_df.assign(row_id=lambda d: d.index)

    desc_lookup = None
    if description_column and description_column in items_df.columns:
        desc_lookup = (
            items_with_ids[["row_id", description_column]]
            .rename(columns={description_column: "_description"})
        )
        desc_lookup["_description"] = (
            desc_lookup["_description"].fillna("").astype(str).str.lower()
        )

    def _prefixes(ncm: str) -> List[str]:
        if not isinstance(ncm, str) or not ncm:
            return []
        return [ncm[:L] for L in lens if L <= len(ncm)]

    expanded = (
        items_with_ids
        .assign(ncm_prefix=lambda d: d["NCM"].apply(_prefixes))
        .explode("ncm_prefix", ignore_index=False)
    )

    if expanded.empty:
        return _apply_fallback(items_df.copy(), fallback_row)

    expanded["prefix_len"] = expanded["ncm_prefix"].str.len()

    merged = expanded.merge(
        cst_prefix_df.drop(columns=["allowed_ncmlist"]),
        on=["ncm_prefix", "prefix_len"],
        how="left",
    )

    if desc_lookup is not None:
        merged = merged.merge(desc_lookup, on="row_id", how="left")
    else:
        merged["_description"] = ""

    merged["_description"] = merged["_description"].fillna("").astype(str).str.lower()

    if "required_keywords_list" not in merged.columns:
        merged["required_keywords_list"] = [[] for _ in range(len(merged))]
    else:
        merged["required_keywords_list"] = merged["required_keywords_list"].apply(
            lambda value: value if isinstance(value, list) else []
        )

    merged["keyword_ok"] = merged.apply(
        lambda row: _keyword_match(row.get("_description", ""), row.get("required_keywords_list", [])),
        axis=1,
    )

    merged = merged[merged["keyword_ok"]]

    if merged.empty:
        return _apply_fallback(items_with_ids.drop(columns=["row_id"]), fallback_row)

    best = (
        merged.sort_values(["row_id", "prefix_len", "priority"], ascending=[True, False, True])
        .groupby("row_id", as_index=False)
        .first()
    )

    result = (
        items_with_ids
        .merge(
            best.drop(
                columns=["ncm_prefix", "prefix_len", "_description", "keyword_ok"],
                errors="ignore",
            ),
            on="row_id",
            how="left",
        )
        .drop(columns=["row_id"])
    )

    return _apply_fallback(result, fallback_row)

def get_default_rule(cst_df: pd.DataFrame) -> Optional[pd.Series]:
    if "DescricaoClassTrib" not in cst_df.columns:
        return None

    desc = cst_df["DescricaoClassTrib"].astype(str)
    mask = desc.str.contains("tribut", case=False, na=False) & desc.str.contains("integral", case=False, na=False)
    candidates = cst_df[mask]

    if candidates.empty:
        candidates = cst_df

    if "priority" in candidates.columns:
        candidates = candidates.sort_values("priority", ascending=True)

    return candidates.iloc[0]

def conectar_bd():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    sslmode_env = os.getenv("DB_SSLMODE")
    if database_url:
        sslmode = sslmode_env or ("require" if "supabase" in database_url else None)
        connect_args = {"dsn": database_url}
        if sslmode and "sslmode" not in database_url.lower():
            connect_args["sslmode"] = sslmode
        connect_args["options"] = "-c search_path=public"
        return psycopg2.connect(**connect_args)

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "Classificador_produtos"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "0176"),
        port=os.getenv("DB_PORT", "5432"),
        sslmode=sslmode_env,
        options="-c search_path=public",
    )

def consulta_geral():
    conn = conectar_bd()
    cursor = conn.cursor()
    query=("""
            SELECT nome_empresa, id, username,senha
            FROM public.cadastro_empresas
            ORDER BY nome_empresa;
        """)
    cursor.execute(query, )
    return cursor.fetchall()

def obter_empresa_codigo(user:str):
    conn = conectar_bd()
    cursor = conn.cursor()
    query=("""
            SELECT id
            FROM cadastro_empresas 
            WHERE username = %s"""
)
    cursor.execute(query, (user,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row and row[0] else None

def listar_planos() -> List[dict]:
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, nome, limite_itens
        FROM planos
        ORDER BY limite_itens
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [
        {"id": row[0], "nome": row[1], "limite": row[2]}
        for row in rows
    ]

def username_disponivel(username: str) -> bool:
    if not username:
        return False
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM cadastro_empresas
        WHERE username = %s
        """,
        (username,),
    )
    exists = cursor.fetchone() is None
    cursor.close()
    conn.close()
    return exists

def criar_empresa(
    nome_empresa: str,
    cnpj: str,
    email: str,
    responsavel: str,
    cpf_responsavel: str,
    username: str,
    senha: str,
    plano_id: int,
) -> Optional[int]:
    hashed_password = _hash_password(senha)
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO cadastro_empresas (
                nome_empresa, cnpj, e_mail, responsavel, cpf_responsavel,
                username, senha, plano_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                nome_empresa,
                cnpj,
                email,
                responsavel,
                cpf_responsavel,
                username,
                hashed_password,
                plano_id,
            ),
        )
        empresa_id = cursor.fetchone()[0]
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
    return empresa_id

def require_login():
    auth = st.session_state.get("authentication_status", None)
    if auth is True:
        return
    # Não logado ou falhou: manda para a página inicial (login) e para a execução
    st.info("Área restrita. Faça login para continuar.")
    try:
        # Disponível em versões recentes do Streamlit
        sleep(3)
        st.switch_page("Login.py") # ou o nome exato da sua página principal
    except Exception:
        # Se sua versão não tiver switch_page, pelo menos interrompe
        st.stop()

def obter_status_plano(empresa_id: int) -> Optional[dict]:
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.nome, p.limite_itens, COALESCE(c.classificados::numeric, 0) AS usados
        FROM cadastro_empresas e
        JOIN planos p ON p.id = e.plano_id
        LEFT JOIN consumo_planos c ON c.empresa_id = e.id
        WHERE e.id = %s
        """,
        (empresa_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return None
    nome, limite, usados = row
    pendencias = listar_creditos_limite(empresa_id, somente_pendentes=True)
    return {
        "plano": nome,
        "limite": int(limite),
        "usados": int(usados),
        "restantes": max(int(limite) - int(usados), 0),
        "pendencias": pendencias,
    }

def registrar_classificacao(empresa_id: int, quantidade: int) -> int:
    if quantidade <= 0:
        return 0
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO consumo_planos (empresa_id, classificados)
        VALUES (%s, %s)
        ON CONFLICT (empresa_id)
        DO UPDATE SET classificados = consumo_planos.classificados::numeric + EXCLUDED.classificados,
                      atualizado_em = NOW()
        RETURNING classificados
        """,
        (empresa_id, quantidade),
    )
    total = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return total

def adicionar_limite_extra(empresa_id: int, quantidade: int) -> Optional[int]:
    if quantidade <= 0:
        return None

    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO consumo_planos (empresa_id, classificados)
            VALUES (%s, 0)
            ON CONFLICT (empresa_id) DO NOTHING
            """,
            (empresa_id,),
        )
        cursor.execute(
            """
            UPDATE consumo_planos
            SET classificados = GREATEST(classificados - %s, 0),
                atualizado_em = NOW()
            WHERE empresa_id = %s
            RETURNING classificados
            """,
            (quantidade, empresa_id),
        )
        row = cursor.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    return row[0] if row else None

def criar_credito_limite(
    empresa_id: int,
    quantidade: int,
    tipo: str,
    valor_total: float,
    descricao: Optional[str] = None,
) -> Optional[int]:
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO creditos_limite (
                empresa_id, tipo, quantidade, valor_total, descricao
            )
            VALUES (
                %s, %s, %s, %s, %s
            )
            RETURNING id
            """,
            (empresa_id, tipo, quantidade, valor_total, descricao),
        )
        credito_id = cursor.fetchone()[0]
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
    return credito_id

def listar_creditos_limite(empresa_id: int, somente_pendentes: bool = True) -> List[dict]:
    conn = conectar_bd()
    cursor = conn.cursor()
    query = """
        SELECT id, tipo, quantidade, valor_total, pago, criado_em, descricao
        FROM creditos_limite
        WHERE empresa_id = %s
    """
    params = [empresa_id]
    if somente_pendentes:
        query += " AND pago::boolean = FALSE"
    query += " ORDER BY criado_em DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [
        {
            "id": row[0],
            "tipo": row[1],
            "quantidade": row[2],
            "valor_total": row[3],
            "pago": row[4],
            "criado_em": row[5],
            "descricao": row[6],
        }
        for row in rows
    ]

def confirmar_pagamento_credito(empresa_id: int, credito_id: int) -> Optional[int]:
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE creditos_limite
            SET pago = TRUE
            WHERE id = %s AND empresa_id = %s AND pago::boolean = FALSE
            RETURNING quantidade
            """,
            (credito_id, empresa_id),
        )
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return None
        quantidade = row[0]
        adicionar_limite_extra(empresa_id, quantidade)
        conn.commit()
        return quantidade
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
