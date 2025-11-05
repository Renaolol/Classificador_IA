import pandas as pd
from pathlib import Path

def extract_data_excel(data):
    """Extract data from excel"""
    data_excel = pd.read_excel(data)
    data_df = pd.DataFrame(data_excel)

    return data_df


