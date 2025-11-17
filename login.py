import streamlit as st
import streamlit_authenticator as stauth
from dependencies import (
    consulta_geral,
    obter_empresa_codigo,
    listar_planos,
    username_disponivel,
    criar_empresa,
)
from config_pag import set_background, get_logo, get_ico

#st.set_page_config(layout="wide", page_icon=get_ico())

#get_logo()
#set_background()
COOKIE_EXPIRY_DAYS = 30

def main():
    db_query = consulta_geral()

    registros = {'usernames':{}}
    for data in db_query:
       registros['usernames'][data[2]] = {'name':data[0], "password":data[3]}
    authenticator = stauth.Authenticate(
        registros,
        'random_cookie_name',
        'randon_signature_key',

        COOKIE_EXPIRY_DAYS,
    )
    if "view_mode" not in st.session_state:
        st.session_state["view_mode"] = None

    sucesso = st.session_state.pop("cadastro_sucesso", None)
    if sucesso:
        st.success(f"Empresa {sucesso['empresa']} criada com sucesso! Faça login com o usuário definido.")
        st.session_state["view_mode"] = "login"

    mode = st.session_state["view_mode"]

    if mode is None:
        st.title("Bem-vindo ao Classificador")
        st.caption("Selecione como deseja acessar:")
        col1, col2 = st.columns(2)
        if col1.button("Entrar", use_container_width=True):
            st.session_state["view_mode"] = "login"
            st.rerun()
        if col2.button("Cadastrar", use_container_width=True):
            st.session_state["view_mode"] = "cadastro"
            st.rerun()
        return

    if mode == "login":
        if st.button("Voltar"):
            st.session_state["view_mode"] = None
            st.rerun()
        login_form(authenticator)
    elif mode == "cadastro":
        if st.button("Voltar"):
            st.session_state["view_mode"] = None
            st.rerun()
        render_cadastro()

def login_form(authenticator):
    # Renderiza o formulário de login
    authenticator.login(
        fields={
            "form_name": "Login",
            "username": "Usuário",
            "password": "Senha",
            "submit": "Entrar",
        },
        location='main',
    )

    # Leia o estado atualizado pelo streamlit-authenticator
    authentication_status = st.session_state.get('authentication_status')
    name = st.session_state.get('name')
    username = st.session_state.get('username')
    

    if authentication_status:
        # carrega e guarda o código da empresa do usuário logado
        emp = obter_empresa_codigo(username)
        st.session_state['empresa_codigo'] = emp
        authenticator.logout('Logout', 'main')
        st.title("Login efetuado com sucesso!")
        st.caption(f"Bem-vindo {name or '—'}")
    elif authentication_status is False:
        st.error('Usuario/Senha incorretos')
    else:
        st.error("Por favor informe um usuário e senha")

def render_cadastro():
    st.subheader("Cadastro de nova empresa")
    planos = listar_planos()
    if not planos:
        st.error("Nenhum plano disponível no momento. Contate o suporte para concluir o cadastro.")
        return

    planos_opcoes = {
        f"{plano['nome']} — até {plano['limite']} itens": plano["id"]
        for plano in planos
    }

    with st.form("cadastro_form"):
        nome_empresa = st.text_input("Nome da empresa")
        cnpj = st.text_input("CNPJ (somente números)")
        email = st.text_input("E-mail de contato")
        responsavel = st.text_input("Responsável")
        cpf_responsavel = st.text_input("CPF do responsável (somente números)")
        username = st.text_input("Usuário para login",help="Apenas letras minusculas e sem acento")
        col1, col2 = st.columns(2)
        senha = col1.text_input("Senha", type="password")
        confirma = col2.text_input("Confirme a senha", type="password")
        plano_label = st.selectbox("Plano", list(planos_opcoes.keys()))
        submit = st.form_submit_button("Cadastrar", use_container_width=True)

    if not submit:
        return

    erros = []
    nome_empresa = nome_empresa.strip()
    cnpj = "".join(filter(str.isdigit, cnpj))
    email = email.strip()
    responsavel = responsavel.strip()
    cpf_responsavel = "".join(filter(str.isdigit, cpf_responsavel))
    username = username.strip().lower()

    if not nome_empresa:
        erros.append("Informe o nome da empresa.")
    if len(cnpj) != 14:
        erros.append("Informe um CNPJ válido com 14 dígitos.")
    if not email:
        erros.append("Informe um e-mail para contato.")
    if not responsavel:
        erros.append("Informe o responsável.")
    if len(cpf_responsavel) != 11:
        erros.append("Informe um CPF válido com 11 dígitos.")
    if not username:
        erros.append("Informe o usuário.")
    if len(senha) < 6:
        erros.append("A senha deve ter ao menos 6 caracteres.")
    if senha != confirma:
        erros.append("As senhas não conferem.")
    if username and not username_disponivel(username):
        erros.append("Usuário já cadastrado. Escolha outro.")

    if erros:
        for erro in erros:
            st.error(erro)
        return

    try:
        criar_empresa(
            nome_empresa,
            cnpj,
            email,
            responsavel,
            cpf_responsavel,
            username,
            senha,
            planos_opcoes[plano_label],
        )
    except Exception as exc:
        st.error(f"Não foi possível concluir o cadastro: {exc}")
        return

    st.session_state["cadastro_sucesso"] = {"empresa": nome_empresa}
    st.session_state["view_mode"] = "login"
    st.rerun()
            

if __name__ =='__main__':
    main()
