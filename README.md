# Classificador Tributário de Produtos – Gcont

Aplicação Streamlit para classificar em massa produtos por NCM/CST, controlar limites de planos corporativos e gerar planilhas com os resultados tributários. O sistema inclui autenticação de empresas, download de planilha modelo, upload processado com regras pré-configuradas e um painel para gestão de créditos extras.

## Índice
- [Principais funcionalidades](#principais-funcionalidades)
- [Arquitetura](#arquitetura)
- [Estrutura de pastas](#estrutura-de-pastas)
- [Pré-requisitos](#pré-requisitos)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Instalação e execução](#instalação-e-execução)
- [Uso do aplicativo](#uso-do-aplicativo)
- [Banco de dados esperado](#banco-de-dados-esperado)
- [Bases auxiliares](#bases-auxiliares)
- [Personalização visual](#personalização-visual)
- [Resolução de problemas](#resolução-de-problemas)
- [Próximos passos sugeridos](#próximos-passos-sugeridos)

## Principais funcionalidades
- **Autenticação com Streamlit** – Login/logout com `streamlit-authenticator`, cookies persistentes e formulário guiado de cadastro de novas empresas (documentos validados via `validate-docbr`).
- **Classificação tributária automática** – Upload de Excel, normalização de NCM, cruzamento com `CST_cclass.xlsx` e fallback inteligente para regras genéricas.
- **Controle de consumo de plano** – Exibição do status (usados, limite e saldo), progress bar e bloqueio quando não há itens restantes.
- **Gestão de créditos** – Tela “Planos” gera recargas do plano atual, créditos extras, lista pendências e confirma pagamentos que liberam novos itens.
- **Banco PostgreSQL** – Persistência para empresas, planos, consumo e créditos com funções utilitárias em `dependencies.py`.
- **Modelo pronto para clientes** – Planilha base em `database/Planilha Modelo.xlsx` e download dentro do app principal.

## Arquitetura
### Páginas Streamlit
- `login.py`: página inicial (landing) que alterna entre login e cadastro.
- `pages/app.py`: módulo “Classificador Tributário”, protegido por sessão. Processa Excel e contabiliza uso de créditos.
- `pages/planos.py`: painel “Planos e Limites” com métricas, geração e confirmação de créditos.

### Lógica de negócio
- `dependencies.py`: núcleo da aplicação. Concentra rotinas de:
  - upload e parsing de Excel (`extract_data_excel`);
  - normalização de NCM e construção de prefixos para CST;
  - merge entre produtos e regras tributárias com filtros por palavras-chave;
  - acesso ao banco (`conectar_bd` e demais consultas/updates);
  - contagem e ajuste de limites (registro de classificações, créditos extras, confirmação de pagamento);
  - funções utilitárias de autenticação (hash de senha) e fluxo de sessão (`require_login`).
- `config_pag.py`: funções para aplicar fundo customizado, inserir logotipo e definir ícone.

## Estrutura de pastas
```
Classificador_IA/
├── login.py
├── dependencies.py
├── config_pag.py
├── pages/
│   ├── app.py
│   └── planos.py
├── database/
│   ├── Planilha Modelo.xlsx
│   ├── CST_cclass.xlsx
│   └── Lei 214 NCMs - CBSs .xlsx
├── requirements.txt
└── Dockerfile
```

## Pré-requisitos
- Python 3.11+ (a imagem Docker usa `python:3.11-slim`).
- PostgreSQL acessível a partir do ambiente de execução.
- Certificado digital PFX se a função `get_api_conformidade_facil` for integrada.
- Bibliotecas listadas em `requirements.txt`.

## Variáveis de ambiente
Defina-as em um arquivo `.env` na raiz do projeto:

```dotenv
# Opção 1: string única
DATABASE_URL=postgresql://usuario:senha@host:5432/base
DB_SSLMODE=require

# Opção 2: parâmetros separados
DB_HOST=localhost
DB_PORT=5432
DB_NAME=Classificador_produtos
DB_USER=postgres
DB_PASSWORD=0176
DB_SSLMODE=require        # prefer/disable conforme servidor

# Certificado (se aplicável)
API_CERT_PATH=/caminho/certificado.p12
API_CERT_PASSWORD=senha
```

`conectar_bd` usa `DATABASE_URL` quando presente e aplica `sslmode=require` automaticamente para provedores como Supabase.

## Instalação e execução
### Ambiente local
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
streamlit run login.py
```
O servidor inicia em `http://localhost:8501`.

### Via Docker
```bash
docker build -t classificador-tributario .
docker run -p 8501:8501 \
  --env-file .env \
  -v $(pwd)/database:/app/database \
  classificador-tributario
```
Monte volumes conforme necessário (planilhas podem ser atualizadas sem rebuild).

## Uso do aplicativo
1. **Cadastro/Login**: acesse `login.py`. Escolha “Cadastrar” para criar uma empresa e selecionar o plano inicial; valide CNPJ/CPF; defina usuário e senha. Depois retorne ao modo login.
2. **Sessão autenticada**: o login guarda `st.session_state["empresa_codigo"]`, obrigatório para `pages/app.py` e `pages/planos.py`. Se não existir, o sistema bloqueia o acesso.
3. **Classificador (pages/app.py)**:
   - Baixe `Planilha Modelo.xlsx` para garantir o layout correto.
   - Faça upload de um Excel com ao menos `NCM` e `Descrição`.
   - O app confere se a quantidade cabe no saldo disponível, normaliza NCM (8 dígitos), combina com `CST_cclass.xlsx` e aplica fallback quando necessário.
   - Os itens classificados são contabilizados em `consumo_planos`. O resultado é exibido em tabela e pode ser baixado.
4. **Planos e créditos (pages/planos.py)**:
   - Visualize métricas de limite, uso e saldo.
   - Gere crédito para recarregar o plano atual (preços definidos em `PLAN_PRICES`) ou solicitar limite extra (custo padrão R$ 0,20/item).
   - Cada crédito gera pendência em `creditos_limite`. Após pagamento externo, clique em “Registrar pagamento” para liberar o saldo (chamadas `confirmar_pagamento_credito` e `adicionar_limite_extra`).

## Banco de dados esperado
As tabelas utilizadas pelas consultas:
- `planos (id, nome, limite_itens)`
- `cadastro_empresas (id, nome_empresa, cnpj, e_mail, responsavel, cpf_responsavel, username, senha, plano_id)`
- `consumo_planos (empresa_id PRIMARY KEY, classificados numeric, atualizado_em timestamp)`
- `creditos_limite (id, empresa_id, tipo, quantidade, valor_total, pago boolean, criado_em, descricao)`

O campo `senha` deve conter hashes gerados no formato do `streamlit-authenticator`. Utilize o fluxo de cadastro ou `_hash_password` para gerar valores compatíveis.

## Bases auxiliares
- **Planilha Modelo.xlsx**: exemplo que os clientes utilizam como template; mantenha em `database/`.
- **CST_cclass.xlsx**: precisa conter colunas como `allowed_ncmlist`, `required_keywords`, `priority`, `DescricaoClassTrib`, `pRedIBS`, `pRedCBS`. As listas de NCM devem usar `;` como separador. Atualize para refletir novas legislações.
- **Lei 214 NCMs - CBSs .xlsx**: base adicional utilizada durante o processamento.

## Personalização visual
`config_pag.py` provê:
- `set_background()`: aplica `fundo.png` com overlay sobre todo o app.
- `get_logo()`: insere `horizontal4.png` no topo.
- `get_ico()`: retorna `icone.ico` para definir o favicon (`st.set_page_config(page_icon=get_ico())`).

Certifique-se de que os arquivos existam na raiz ou ajuste os caminhos.

## Resolução de problemas
- **“Plano não configurado”** – Verifique se `cadastro_empresas.plano_id` referencia um plano válido e se `planos` contém registros.
- **Saldo não atualiza** – Confirme se `consumo_planos` possui linha para a empresa. `registrar_classificacao` usa `ON CONFLICT` para criar/atualizar.
- **Upload excede saldo** – O app bloqueia quando o total de itens do Excel é maior que `restantes`. Gere crédito antes do upload.
- **Colunas faltantes** – O app informa colunas ausentes em `DISPLAY_COLUMNS`. Ajuste a planilha de entrada ou o array no código.
- **Crédito não libera itens** – Certifique-se de clicar em “Registrar pagamento”; só após `confirmar_pagamento_credito` o valor é abatido de `creditos_limite` e somado ao saldo.
- **Conexão recusada** – Revise as variáveis `.env`, permissões de rede/SSL do banco e se o container tem acesso ao host.

## Próximos passos sugeridos
1. **Histórico de uploads e reprocessamento** sem debitar o plano novamente.
2. **Dashboard administrativo** para visualizar empresas, consumo e créditos pendentes em tempo real.
3. **Notificações automáticas** (e-mail/WhatsApp) quando o saldo estiver baixo ou créditos aguardarem pagamento.
4. **Testes automatizados** (`pytest`) para as funções de merge de DataFrame e operações de banco.
5. **Integração direta com APIs fiscais** via `get_api_conformidade_facil` para atualizar automaticamente a base de CST/CClass.

---
Com esse README você possui um guia completo para configurar, executar e evoluir o Classificador Tributário de Produtos – Gcont. Ajuste as seções conforme seu fluxo interno ou requisitos de compliance.

