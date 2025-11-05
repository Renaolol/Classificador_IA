import pandas as pd
from time import sleep
from pathlib import Path
from dependencies import extract_data_excel, get_api_conformidade_facil
import os
from dotenv import load_dotenv
import json
from pathlib import Path

load_dotenv()
# -----------------------
# Planilhas Excel
excel = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\Produtos.xlsx")
lei_complementar = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\Lei 214 NCMs - CBSs .xlsx")

# -----------------------
# Criação e manipulação dos DataFrames
excel_df = extract_data_excel(excel)
lei_df = extract_data_excel(lei_complementar)
classificacao = pd.merge(excel_df,lei_df,"left",on="NCM")
classificados_limpo = classificacao.fillna("Não compreendido pela LC 214/2025")

#------------------------
# Caminho do certificado e senha para a busca na API do conformidade fácil
certificado = r"C:\Users\gcont\OneDrive\Desktop\GCONT.pfx"
senha = os.getenv("SENHA_CERTIFICADO")
caminhos = Path(".")
for arquivo in caminhos.glob("*"):
    existe = True
    if arquivo.is_file() and 'CclassTrib.txt' in arquivo.name:
        existe = False
        print ("arquivo CclassTrib.txt encontrado")
if existe:
    cclass = get_api_conformidade_facil(certificado,senha)
    # -----------------------
    # Transformação do Json em um txt contendo o Json
    with open("CclassTrib.txt", "w", encoding="utf-8") as arquivo:
        json.dump(cclass.json(),arquivo,indent=4,ensure_ascii=False)


#classificados_limpo[["Descrição","NCM","PRODUTO","Tributação"]].to_excel("classificados_limpo.xlsx")