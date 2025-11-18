import streamlit as st
from decimal import Decimal
from dependencies import (
    require_login,
    listar_planos,
    obter_status_plano,
    criar_credito_limite,
    listar_creditos_limite,
    confirmar_pagamento_credito,
)
from config_pag import set_background, get_logo, get_ico
PLAN_PRICES = {
    "Plano Free": Decimal("0.00"),
    "Starter 5K": Decimal("199.90"),
    "Growth 15K": Decimal("499.90"),
    "Pro 30K": Decimal("799.90"),
    "Elite 60K": Decimal("1299.90"),
    "Enterprise Flex": Decimal("1500.00"),
}
EXTRA_PRICE = Decimal("0.20")



st.set_page_config(layout="wide", page_icon=get_ico())

get_logo()
set_background()
require_login()

empresa_id = st.session_state.get("empresa_codigo")
if not empresa_id:
    st.error("Não foi possível identificar sua empresa. Faça login novamente.")
    st.stop()

status_plano = obter_status_plano(empresa_id)
if not status_plano:
    st.error("Plano não configurado. Contate o suporte.")
    st.stop()

success_msg = st.session_state.pop("limite_success", None)
error_msg = st.session_state.pop("limite_error", None)
if success_msg:
    st.success(success_msg)
if error_msg:
    st.error(error_msg)

pendencias = status_plano.get("pendencias", [])

st.title("Planos e Limites")
st.caption("Controle seu saldo, gere créditos e acompanhe pagamentos pendentes.")

col1, col2, col3 = st.columns(3)
col1.metric("Limite do plano", status_plano["limite"])
col2.metric("Itens classificados", status_plano["usados"])
col3.metric("Disponíveis", status_plano["restantes"])

if pendencias:
    st.warning("Há créditos pendentes aguardando pagamento.")

st.divider()
st.subheader("Pendências e pagamentos")
if not pendencias:
    st.caption("Nenhum crédito aguardando pagamento.")
else:
    for credito in pendencias:
        with st.expander(
            f"{credito['tipo'].capitalize()} — {credito['quantidade']} itens — "
            f"R$ {credito['valor_total']:,.2f}"
        ):
            st.write(f"Criado em: {credito['criado_em']:%d/%m/%Y %H:%M}")
            if credito.get("descricao"):
                st.write(f"Descrição: {credito['descricao']}")

st.divider()
st.subheader("Gerar créditos")

preco_plano = PLAN_PRICES.get(status_plano["plano"])
if st.button(
    f"Recarregar plano (+{status_plano['limite']} itens)",
    use_container_width=True,
):
    if preco_plano is None:
        st.session_state["limite_error"] = "Defina o preço do plano antes de recarregar."
    else:
        descricao = f"Recarregar plano {status_plano['plano']}"
        criar_credito_limite(
            empresa_id,
            status_plano["limite"],
            "pacote",
            float(preco_plano),
            descricao,
        )
        st.session_state["limite_success"] = (
            "Crédito criado! Efetue o pagamento e registre acima para liberar o saldo."
        )
    st.rerun()

st.caption("Limite extra custa R$ 0,20 por item liberado.")
quantidade_extra = st.number_input(
    "Quantidade extra desejada",
    min_value=100,
    step=100,
    value=1000,
    help="Informe o volume que deseja adicionar ao saldo disponível.",
)
if st.button(f"Gerar crédito de +{quantidade_extra:,.0f} itens", use_container_width=True):
    valor_total = Decimal(quantidade_extra) * EXTRA_PRICE
    descricao = f"Limite extra de {quantidade_extra} itens"
    criar_credito_limite(
        empresa_id,
        int(quantidade_extra),
        "extra",
        float(valor_total),
        descricao,
    )
    st.session_state["limite_success"] = (
        "Crédito extra registrado! Assim que o pagamento for confirmado, o saldo será liberado."
    )
    st.rerun()

st.divider()
st.subheader("Planos disponíveis")

planos = listar_planos()

if not planos:
    st.warning("Nenhum plano cadastrado. Fale com o suporte para configurar opções.")
else:
    cols = st.columns(min(len(planos), 3))
    for idx, plano in enumerate(planos):
        col = cols[idx % len(cols)]
        with col:
            limite = plano["limite"]
            preco = PLAN_PRICES.get(plano["nome"], None)
            custo_unit = None
            if preco is not None and limite:
                custo_unit = preco / limite if preco else Decimal("0")
            st.metric(plano["nome"], f"{limite}")
            if preco is None:
                st.write("Investimento: Teste")
            else:
                valor = "Gratuito" if preco == 0 else f"R$ {preco:,.2f}"
                st.write(f"Investimento por recarga: {valor}")
            if custo_unit is not None:
                if custo_unit == 0:
                    st.caption("Custo por item: sem cobrança.")
                else:
                    st.caption(f"Custo por item: R$ {custo_unit:,.2f}")
