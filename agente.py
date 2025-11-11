from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional
import pandas as pd
import os
import json

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

class SaidaMinima(BaseModel):
    CST: str
    cClassTrib: str

def make_agente_interpretativo(df_cst: pd.DataFrame, ramo_padrao: Optional[str] = None,) -> Agent:
    def listar_classificacoes(ramo: Optional[str] = None, termo: Optional[str] = None, limit: int = 300) -> list[dict]:
        df = df_cst.copy()
        cols = ["CST","DescricaoCST","cClassTrib","DescricaoClassTrib"]

        # Filtro por ramo (único contexto permitido)
        ramo = ramo or ramo_padrao
        if ramo:
            # Se houver coluna específica de ramo/segmento, usa-a
            col_ramo = next((c for c in ["Ramo","Segmento","Setor","Categoria"] if c in df.columns), None)
            if col_ramo:
                df = df[df[col_ramo].astype(str).str.contains(ramo, case=False, na=False)]
            else:
                # Caso não haja coluna de ramo, filtra por texto nas descrições
                m1 = df["DescricaoClassTrib"].astype(str).str.contains(ramo, case=False, na=False) if "DescricaoClassTrib" in df.columns else False
                m2 = df["DescricaoCST"].astype(str).str.contains(ramo, case=False, na=False) if "DescricaoCST" in df.columns else False
                df = df[m1 | m2]

        # Termo opcional para guiar a listagem (ex.: "carne", "alimento")
        if termo:
            m1 = df["DescricaoClassTrib"].astype(str).str.contains(termo, case=False, na=False) if "DescricaoClassTrib" in df.columns else False
            m2 = df["DescricaoCST"].astype(str).str.contains(termo, case=False, na=False) if "DescricaoCST" in df.columns else False
            df = df[m1 | m2]

        have = [c for c in cols if c in df.columns]
        return df[have].dropna(how="all").head(limit).to_dict(orient="records")

    system = (
        "Tarefa: ler e interpretar a descrição do produto e selecionar um único par existente {CST, cClassTrib}.\n"
        "- O único contexto permitido é o ramo da empresa (ex.: 'Super Mercado').\n"
        "- Para decidir, chame listar_classificacoes(ramo, termo) e utilize as descrições (DescricaoClassTrib/DescricaoCST) como base.\n"
        "- Não use métricas de similaridade; decida por interpretação de texto e regras. "
        "Ex.: 'MAMINHA ANGUS' → alimento/carne; pesquise candidatos com termo 'carne' ou 'alimento' e escolha o par correto se existir.\n"
        "- Saída obrigatória: SOMENTE JSON {'CST':'...','cClassTrib':'...'}."
    )

    return Agent(
        name="classificador-interpretativo",
        system_message=system,
        tools=[listar_classificacoes],
        model=OpenAIResponses(
            id="gpt-4o-mini",
            api_key=api_key
        ),
    )

def classificar_descricao(
    descricao: str,
    agente: Agent,
    ramo: Optional[str] = None,
    termo_inicial: Optional[str] = None
) -> dict:
    prompt = (
        "Classifique o produto a seguir por leitura/interpretação. "
        "Para decidir, chame listar_classificacoes(ramo, termo) para inspecionar candidatos relevantes. "
        "Retorne SOMENTE JSON com CST e cClassTrib.\n\n"
        f"Produto: {json.dumps(descricao, ensure_ascii=False)}\n"
        f"Ramo: {json.dumps(ramo, ensure_ascii=False)}\n"
        f"TermoSugestao: {json.dumps(termo_inicial, ensure_ascii=False)}"
    )
    resp = agente.run(prompt)
    if isinstance(resp, dict):
        return resp
    try:
        return json.loads(str(resp))
    except:
        # Algumas versões retornam um objeto pydantic; tenta extrair
        try:
            return resp.dict()  # type: ignore[attr-defined]
        except:
            return {"CST": "", "cClassTrib": ""}

def classificar_df_por_interpretacao(
    df_produtos: pd.DataFrame,
    agente: Agent,
    descricao_col: str,
    ramo: Optional[str] = None,
    termo_inicial: Optional[str] = None,
    max_linhas: Optional[int] = None,
) -> pd.DataFrame:
    base = df_produtos if max_linhas is None else df_produtos.head(max_linhas)
    registros = []
    for _, row in base.iterrows():
        descricao = str(row.get(descricao_col, "")).strip()
        registros.append(classificar_descricao(descricao, agente, ramo=ramo, termo_inicial=termo_inicial))
    return base.reset_index(drop=True).join(pd.DataFrame(registros))
