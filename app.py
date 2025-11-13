import pandas as pd
from time import sleep
from pathlib import Path
from dependencies import extract_data_excel, get_api_conformidade_facil
import os
from dotenv import load_dotenv
import json
from pathlib import Path
from pprint import pprint
load_dotenv()
# -----------------------
# Planilhas Excel
produtos = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\database\Produtos.xlsx")
lei_complementar = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\database\Lei 214 NCMs - CBSs .xlsx")
cst_cclass_excel = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\database\CST_cclass.xlsx")
# -----------------------
# Criação e manipulação dos DataFrames
#produtos_df = extract_data_excel(produtos)
lei_df = extract_data_excel(lei_complementar)
cst_cclass_excel_df = extract_data_excel(cst_cclass_excel)
produto = {'descricao':['CARNE MOIDA CONG.MARCON 1KG'],'NCM':['0202.30.00']}

df_teste = pd.DataFrame(produto)
df_teste["NCM"] = df_teste["NCM"].str.replace(".","")
df_merged = pd.merge(df_teste,cst_cclass_excel_df,left_on="NCM",right_on="allowed_ncmlist")
print (df_merged)
# print (df_teste)
# print (cst_cclass_excel_df["allowed_ncmlist"].head(20))

for x in cst_cclass_excel_df['allowed_ncmlist']:
    if isinstance(x, str):
        if df_teste['NCM'] in x:
            print(x)
    else:
        continue




# #------------------------
# # Caminho do certificado e senha para a busca na API do conformidade fácil
# certificado = r"C:\Users\gcont\OneDrive\Desktop\GCONT.pfx"
# senha = os.getenv("SENHA_CERTIFICADO")
# caminhos = Path(".")
