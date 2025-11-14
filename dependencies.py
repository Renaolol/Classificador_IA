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
