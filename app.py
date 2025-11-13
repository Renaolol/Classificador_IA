import pandas as pd
from pathlib import Path
from typing import List, Optional
from dependencies import extract_data_excel, get_api_conformidade_facil
from dotenv import load_dotenv

load_dotenv()

# -----------------------
# Planilhas Excel
produtos = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\database\Produtos.xlsx")
lei_complementar = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\database\Lei 214 NCMs - CBSs .xlsx")
cst_cclass_excel = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\database\CST_cclass.xlsx")
# -----------------------


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


def merge_by_prefix(
    items_df: pd.DataFrame,
    cst_prefix_df: pd.DataFrame,
    description_column: Optional[str] = None,
) -> pd.DataFrame:
    """Attach each item to the most specific CST prefix available."""
    if cst_prefix_df.empty:
        return items_df.copy()

    lens = sorted(cst_prefix_df["prefix_len"].unique())
    if not lens:
        return items_df.copy()

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
        return items_df.copy()

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
        return items_with_ids.drop(columns=["row_id"])

    best = (
        merged.sort_values(["row_id", "prefix_len", "priority"], ascending=[True, False, True])
        .groupby("row_id", as_index=False)
        .first()
    )

    return (
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


def main() -> None:
    # Load spreadsheets
    produtos_df = extract_data_excel(produtos)
    lei_df = extract_data_excel(lei_complementar)
    cst_cclass_excel_df = extract_data_excel(cst_cclass_excel)

    # Placeholder so linting tools know the sheet was loaded intentionally
    _ = lei_df

    # Prepare CST mapping once
    cst_prefixes = build_cst_prefixes(cst_cclass_excel_df)

    # Quick example
    produto = {"descricao": ["CARNE MOIDA CONG.MARCON 1KG"], "NCM": ["0202.30.00"]}
    df_teste = pd.DataFrame(produto)
    df_teste["NCM"] = normalize_ncm(df_teste["NCM"])
    df_teste_merged = merge_by_prefix(df_teste, cst_prefixes, description_column="descricao")
    print(df_teste_merged)

    # Apply merge to the full product list
    produtos_df["NCM"] = normalize_ncm(produtos_df["NCM"])
    df_merged = merge_by_prefix(produtos_df, cst_prefixes)
    df_merged.to_excel("df_merged.xlsx", index=False)


if __name__ == "__main__":
    main()
