import pandas as pd
from pathlib import Path
import requests
import os
import base64
from requests_pkcs12 import Pkcs12Adapter
from pprint import pprint
from dotenv import load_dotenv
import json

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

