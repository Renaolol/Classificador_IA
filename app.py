import pandas as pd
from time import sleep
from pathlib import Path
from dependencies import extract_data_excel
excel = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\Pasta1.xlsx")
lei_complementar = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\Lei 214 NCMs - CBSs .xlsx")
excel_df = extract_data_excel(excel)
lei_df = extract_data_excel(lei_complementar)
classificacao = pd.merge(excel_df,lei_df,"left",on="NCM")
print(classificacao[["Nome Produto","NCM","PRODUTO","Tributação"]])
