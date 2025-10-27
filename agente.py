from agno.agent.agent import Agent, RunOutput
from agno.models.openai import OpenAIResponses
from agno.knowledge.reader.text_reader import TextReader
from agno.knowledge.knowledge import Knowledge
from dotenv import load_dotenv
import json

load_dotenv()


def extrair_dados_txt(txt):
    try:
        with open(txt, "r", encoding="utf-8") as arquivo:
            conteudo = arquivo.read()
            return conteudo
    except FileNotFoundError:
        return "Erro: O arquivo nao foi encontrado"


def normalizar_json_bruto(conteudo):
    """Remove cercas de codigo e converte o JSON retornado pelo modelo em dict."""
    if isinstance(conteudo, (dict, list)):
        return conteudo

    if not isinstance(conteudo, str):
        return conteudo

    texto = conteudo.strip()
    if texto.startswith("```"):
        linhas = texto.splitlines()
        if linhas and linhas[0].startswith("```"):
            linhas = linhas[1:]
        if linhas and linhas[-1].startswith("```"):
            linhas = linhas[:-1]
        texto = "\n".join(linhas).strip()

    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return conteudo


arquivo_txt = "CclassTrib.txt"
arquivo_txt_parsed = extrair_dados_txt(arquivo_txt)
caminho_instructions = "instructions.txt"
instructions = extrair_dados_txt(caminho_instructions)
knowledge_cclass = Knowledge(readers=TextReader(file="CclassTrib.txt",chunking_strategy=1000))
agent = Agent(
    model=OpenAIResponses(id="gpt-4o-mini"),
    instructions=instructions,
    knowledge=knowledge_cclass,
    search_knowledge=True,
    use_json_mode=True,
    id=1,
)


def get_response(pergunta: str):
    response: RunOutput = agent.run(pergunta)
    return normalizar_json_bruto(response.content)


pergunta = "Qual seria a CST, e cClassTrib do Arroz quando integra a cesta básica?."

resposta_json = get_response(pergunta)
if isinstance(resposta_json, (dict, list)):
    print(json.dumps(resposta_json, ensure_ascii=False, indent=4))
else:
    print(resposta_json)
