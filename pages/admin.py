import streamlit as st
from dependencies import (
    require_login,
    listar_empresas_detalhes,
    atualizar_status_empresa,
    listar_creditos_pendentes_admin,
    confirmar_pagamento_credito,
    listar_planos,
)

def _descricao_visivel(descricao: str) -> str:
    if not descricao:
        return ""
    return descricao.split("##PLANO_ID=")[0].strip()

# Defina aqui os usernames autorizados a acessar o painel administrativo.
ADMIN_USERS = {"admin","teste"}

st.set_page_config(page_title="Painel Administrativo", layout="wide")
require_login()

username = st.session_state.get("username")
if username not in ADMIN_USERS:
    st.error("Área restrita. Somente administradores podem acessar este painel.")
    st.stop()

st.title("Painel Administrativo")
st.caption("Gerencie empresas, libere acessos e acompanhe créditos pendentes.")

empresas = listar_empresas_detalhes()
pendencias_credito = listar_creditos_pendentes_admin()
planos = listar_planos()

totais = st.columns(3)
totais[0].metric("Empresas cadastradas", len(empresas))
totais[1].metric(
    "Pendentes de liberação",
    sum(1 for empresa in empresas if not empresa["ativo"]),
)
totais[2].metric("Créditos pendentes", len(pendencias_credito))

st.divider()
st.subheader("Pendências de crédito")
if not pendencias_credito:
    st.caption("Nenhum crédito aguardando confirmação.")
else:
    for credito in pendencias_credito:
        with st.expander(
            f"#{credito['id']} — {credito['empresa']} — "
            f"{credito['quantidade']} itens — R$ {credito['valor_total']:,.2f}"
        ):
            st.write(f"Tipo: {credito['tipo']}")
            criado_em = credito.get("criado_em")
            if criado_em:
                st.write(f"Criado em: {criado_em:%d/%m/%Y %H:%M}")
            else:
                st.write("Criado em: —")
            descricao_visivel = _descricao_visivel(credito.get("descricao") or "")
            if descricao_visivel:
                st.write(f"Descrição: {descricao_visivel}")
            if st.button(
                "Confirmar pagamento",
                key=f"confirm_credit_{credito['id']}",
            ):
                quantidade = confirmar_pagamento_credito(
                    credito["empresa_id"],
                    credito["id"],
                )
                if quantidade is None:
                    st.error("Não foi possível confirmar o pagamento.")
                elif credito["tipo"] == "mudanca":
                    st.success(
                        f"Plano de {credito['empresa']} atualizado conforme solicitação."
                    )
                else:
                    st.success(
                        f"Pagamento confirmado. {quantidade} itens liberados para "
                        f"{credito['empresa']}."
                    )
                st.rerun()

st.divider()
st.subheader("Empresas cadastradas")
if not empresas:
    st.caption("Nenhuma empresa cadastrada.")
else:
    for empresa in empresas:
        status_label = "Liberar acesso" if not empresa["ativo"] else "Bloquear acesso"
        with st.expander(
            f"{empresa['nome']} ({empresa['username']}) — "
            f"{'Ativa' if empresa['ativo'] else 'Pendente'}"
        ):
            col1, col2, col3 = st.columns(3)
            col1.metric("Plano", empresa["plano"] or "—")
            col2.metric("Limite", empresa["limite"] or 0)
            col3.metric("Usados", empresa["usados"])
            st.write(f"CNPJ: {empresa['cnpj'] or '—'}")
            st.write(f"Responsável: {empresa['responsavel'] or '—'}")
            st.write(f"E-mail: {empresa['email'] or '—'}")
            st.write(f"Itens disponíveis: {empresa['restantes']}")
            if st.button(
                status_label,
                key=f"toggle_{empresa['id']}",
            ):
                atualizar_status_empresa(empresa["id"], not empresa["ativo"])
                st.rerun()

st.divider()
st.subheader("Planos cadastrados")
if not planos:
    st.caption("Nenhum plano disponível.")
else:
    st.table(
        {
            "Plano": [plano["nome"] for plano in planos],
            "Limite de itens": [plano["limite"] for plano in planos],
        }
    )
