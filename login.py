import streamlit as st
import streamlit_authenticator as stauth
from dependencies import consulta_geral, cria_tabela, obter_empresa_codigo
from time import sleep
from config_pag import set_background, get_logo, get_ico

st.set_page_config(layout="wide", page_icon=get_ico())

get_logo()
set_background()
COOKIE_EXPIRY_DAYS = 30

def main():
    try:
        consulta_geral()
    except:
        cria_tabela()    

    db_query = consulta_geral()

    registros = {'usernames':{}}
    for data in db_query:
       registros['usernames'][data[1]] = {'name':data[0], "password":data[2]}
    authenticator = stauth.Authenticate(
        registros,
        'random_cookie_name',
        'randon_signature_key',

        COOKIE_EXPIRY_DAYS,
    )
    if 'clicou_registrar' not in st.session_state:
        st.session_state['clicou_registrar']=False

    if st.session_state['clicou_registrar'] == False:
        login_form(authenticator)   

def login_form(authenticator):
    # Renderiza o formulário de login
    authenticator.login(location='main', key='Login')

    # Leia o estado atualizado pelo streamlit-authenticator
    authentication_status = st.session_state.get('authentication_status')
    name = st.session_state.get('name')
    username = st.session_state.get('username')
    

    if authentication_status:
        # carrega e guarda o código da empresa do usuário logado
        emp = obter_empresa_codigo(username)
        st.session_state['empresa_codigo'] = emp
        authenticator.logout(location='main', key='Logout')
        st.title("Login efetuado com sucesso!")
        st.caption(f"Logado como: {name or '—'}, {emp or "Administrador"}")
    elif authentication_status is False:
        st.error('Usuario/Senha incorretos')
    else:
        st.error("Por favor informe um usuário e senha")
            

if __name__ =='__main__':
    main()