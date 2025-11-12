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

def processa_df(df:pd.DataFrame):
    pass