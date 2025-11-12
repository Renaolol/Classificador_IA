import pandas as pd
from time import sleep
from pathlib import Path
from dependencies import extract_data_excel, get_api_conformidade_facil
import os
from dotenv import load_dotenv
import json
from pathlib import Path
from pprint import pprint
from agente import make_agente_interpretativo, classificar_descricao, classificar_df_por_interpretacao
load_dotenv()
# -----------------------
# Planilhas Excel
excel = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\Produtos.xlsx")
lei_complementar = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\Lei 214 NCMs - CBSs .xlsx")
cst_cclass_excel = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\CST_CclassTrib_Resumo.xlsx")
# -----------------------
# Criação e manipulação dos DataFrames
excel_df = extract_data_excel(excel)
lei_df = extract_data_excel(lei_complementar)
cst_class_df = pd.read_excel(cst_cclass_excel, dtype={'CST':'string','cClassTrib':'string'})
cst_class_df["CST"]=cst_class_df["CST"].astype(str)
cst_class_df["cClassTrib"]=cst_class_df["cClassTrib"].astype(str)
classificacao = pd.merge(excel_df,lei_df,"left",on="NCM")
classificados_limpo = classificacao.fillna("Não compreendido pela LC 214/2025")

#------------------------
# Caminho do certificado e senha para a busca na API do conformidade fácil
certificado = r"C:\Users\gcont\OneDrive\Desktop\GCONT.pfx"
senha = os.getenv("SENHA_CERTIFICADO")
caminhos = Path(".")
