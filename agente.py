from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from dotenv import load_dotenv
from dependencies import extract_data_excel
import os
from pathlib import Path

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

lei_complementar = Path(r"C:\Users\gcont\OneDrive\Documentos\GitHub\Classificador_IA\Lei 214 NCMs - CBSs .xlsx")
lei_complementar_df = extract_data_excel(lei_complementar)
agent_leitor = Agent(model=OpenAIResponses(id="gpt-4o-mini",name="Agente Leitor de Dados",api_key=api_key),
                     markdown=True, stream=True)

pergunta = f"Extraia os dados deste arquivo: {lei_complementar_df}"

agent_leitor.response(pergunta)