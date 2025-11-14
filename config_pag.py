import streamlit as st
from base64 import b64encode
from pathlib import Path

def set_background():
    image_path = Path("fundo.png")
    if not image_path.exists():
        st.warning(f"Imagem não encontrada: {image_path}")
        return

    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    data = b64encode(image_path.read_bytes()).decode()

    st.markdown(
        f"""
        <style>
        /* Fundo geral do app */
        .stApp {{
            background: url("data:{mime};base64,{data}") no-repeat center center fixed;
            background-size: cover;
            position: relative;
        }}

        /* Overlay para deixar a imagem mais opaca */
        .stApp::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0,0,0,0.50);
            z-index: 0;
        }}

        /* Garante que o conteúdo fique acima do overlay */
        .stApp > div {{
            position: relative;
            z-index: 1;
        }}

        /* Fundo translúcido dos blocos de conteúdo */
        [data-testid="stAppViewContainer"] > .main .block-container {{
            background: rgba(255,255,255,0.30);
            border-radius: 25px;
            padding: 1rem 1.25rem;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def get_logo():
    logo = "horizontal4.png"
    st.logo(logo,size="Large")

def get_ico():
    return "icone.ico"
    