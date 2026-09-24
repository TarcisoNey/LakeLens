import json
import time

import streamlit as st

try:
    from src.rag_engine import RAGEngine
except ImportError:
    from rag_engine import RAGEngine

# Configuracao da pagina
st.set_page_config(
    page_title="LakeLens",
    layout="wide"
)

# Cores vem do .streamlit/config.toml (edite la e recarregue a pagina):
#   PALETA     <- theme.chartCategoricalColors (5 cores)
#   COR_TITULO <- theme.linkColor
#   COR_TEXTO  <- theme.textColor
#   COR_TITULO_SIDEBAR <- theme.sidebar.linkColor
# O tema do Streamlit so aplica sozinho a cor primaria, o fundo e o texto; o resto da
# paleta e aplicado pelo CSS abaixo. Os valores padrao valem se o config nao os definir.
PALETA_PADRAO = ["#64378C", "#48378C", "#80378C", "#37418C", "#8C376F"]


def _cor(chave, padrao):
    valor = st.get_option(chave)
    return valor if isinstance(valor, str) and valor else padrao


_paleta = st.get_option("theme.chartCategoricalColors") or PALETA_PADRAO
PALETA = [_paleta[i % len(_paleta)] for i in range(5)]  # garante 5 cores, mesmo com lista menor
COR_TITULO = _cor("theme.linkColor", "#C99AD4")
COR_TEXTO = _cor("theme.textColor", "#E6EDF7")
COR_TITULO_SIDEBAR = _cor("theme.sidebar.linkColor", COR_TITULO)

st.markdown(
    f"""
<style>
h1, h2, h3 {{ color: {COR_TITULO} !important; }}
[data-testid="stMain"] h1 {{
    padding-bottom: 0.4rem;
    border-bottom: 4px solid;
    border-image: linear-gradient(90deg, {", ".join(PALETA)}) 1;
}}
[data-testid="stSidebarUserContent"] {{ padding-top: 1rem !important; }}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 0.6rem; }}
[data-testid="stSidebar"] hr {{ margin: 0.4rem 0 !important; }}
[data-testid="stSidebar"] .stButton button,
[data-testid="stSidebar"] .stDownloadButton button {{
    background: {PALETA[0]};
    color: #FFFFFF;
    border: 1px solid {PALETA[2]};
}}
[data-testid="stSidebar"] .stButton button:hover,
[data-testid="stSidebar"] .stDownloadButton button:hover {{
    background: {PALETA[4]};
    border-color: {PALETA[4]};
    color: #FFFFFF;
}}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color: {COR_TEXTO}; opacity: 0.85; }}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
    color: {COR_TITULO_SIDEBAR} !important;
}}
[data-testid="stChatMessage"] {{
    background: {PALETA[0]}33;
    border-left: 4px solid {PALETA[2]};
    border-radius: 0.5rem;
}}
[data-testid="stAlert"] {{
    background: {PALETA[3]}33;
    border-left: 4px solid {PALETA[4]};
    color: {COR_TEXTO};
}}
</style>
""",
    unsafe_allow_html=True
)

MENSAGEM_BOAS_VINDAS = "Olá! Sou o LakeLens. Como posso ajudar com base nos documentos técnicos sobre Lakehouse, Delta Lake e arquiteturas centradas em dados?"

# Avatares do chat (emoji, imagem ou ":material/icone:"). O padrao do Streamlit e o robozinho.
AVATARES = {"user": "🧑‍💻", "assistant": "🔎"}

PERGUNTAS_EXEMPLO = [
    "O que é uma arquitetura Lakehouse?",
    "Quais recursos o Delta Lake oferece sobre o armazenamento de objetos em nuvem?",
    "Quais são as boas práticas para projetar uma arquitetura moderna centrada em dados?",
]


# Inicializar o motor RAG em cache para evitar recriacao desnecessaria
@st.cache_resource
def get_rag_engine():
    return RAGEngine()


def render_fontes(fontes):
    """Painel de explicabilidade: chunks recuperados com pagina e similaridade."""
    if not fontes:
        return
    with st.expander("Ver Fontes e Chunks Recuperados"):
        for idx, f in enumerate(fontes, 1):
            st.markdown(f"**Fonte {idx}:** `{f['arquivo']}` (Pág. {f['pagina']}) — *Similaridade: {f['similaridade']:.2%}*")
            st.info(f["texto"])


def confianca_media(fontes):
    """Badge de confianca baseado na similaridade media dos chunks recuperados."""
    media = sum(f["similaridade"] for f in fontes) / len(fontes)
    if media >= 0.75:
        return "Alta", "green", media
    if media >= 0.50:
        return "Média", "orange", media
    return "Baixa", "red", media


try:
    engine = get_rag_engine()
except Exception as e:
    st.error(f"Erro ao inicializar o motor RAG: {e}. Verifique sua GEMINI_API_KEY no arquivo .env!")
    st.stop()

# Inicializar historico na sessao
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": MENSAGEM_BOAS_VINDAS, "fontes": []}
    ]
if "pergunta_pendente" not in st.session_state:
    st.session_state.pergunta_pendente = None

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.title("Painel de Controle")
    st.markdown("**AskData - LakeLens** | *DataLakers & Navi Hub*")
    st.markdown("---")

    top_k = st.slider("Quantidade de Chunks (Top-K):", min_value=1, max_value=10, value=6)

    st.markdown("### Perguntas Frequentes")
    for p in PERGUNTAS_EXEMPLO:
        if st.button(p, key=f"btn_{p}"):
            st.session_state.pergunta_pendente = p

    st.markdown("### Sobre a Base Indexada")
    st.caption("Esta aplicação utiliza embeddings do Google (`gemini-embedding-001`), armazenamento vetorial persistente no **ChromaDB** e geração com o **Modelo Gemini**.")

    if st.button("Limpar Histórico de Chat"):
        st.session_state.messages = [
            {"role": "assistant", "content": MENSAGEM_BOAS_VINDAS, "fontes": []}
        ]
        st.session_state.pergunta_pendente = None
        st.rerun()

    historico_json = json.dumps(st.session_state.messages, indent=2, ensure_ascii=False)
    st.download_button(
        label="Exportar Histórico (JSON)",
        data=historico_json,
        file_name="historico_chat.json",
        mime="application/json"
    )

    # Badge de confianca da ultima resposta (sobre a similaridade dos chunks)
    ultimas_fontes = st.session_state.messages[-1].get("fontes", [])
    if ultimas_fontes:
        status, cor, media = confianca_media(ultimas_fontes)
        st.markdown(f"**Confiança da Última Resposta:** :{cor}[{status} ({media:.1%})]")
        st.caption("Baseada na similaridade média dos chunks recuperados, não na correção da resposta.")

# --- AREA PRINCIPAL ---
st.title("LakeLens: Assistente de Documentação Técnica")
st.caption("Faça perguntas sobre a base de conhecimento. Todas as respostas são fundamentadas com citação direta dos documentos.")

# Renderizar historico de mensagens
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=AVATARES[msg["role"]]):
        st.markdown(msg["content"])
        if msg.get("latencia") is not None:
            st.caption(f"Tempo de resposta: {msg['latencia']:.2f}s")
        render_fontes(msg.get("fontes"))

# Input do usuario (digitado no chat ou vindo de um botao de pergunta sugerida)
prompt = st.chat_input("Digite sua pergunta técnica aqui...")
if st.session_state.pergunta_pendente:
    prompt = st.session_state.pergunta_pendente
    st.session_state.pergunta_pendente = None

if prompt:
    # 1. Adicionar mensagem do usuario na tela
    st.session_state.messages.append({"role": "user", "content": prompt, "fontes": []})
    with st.chat_message("user", avatar=AVATARES["user"]):
        st.markdown(prompt)

    # 2. Gerar resposta com o motor RAG
    with st.chat_message("assistant", avatar=AVATARES["assistant"]):
        with st.spinner("Buscando no banco vetorial e formulando resposta..."):
            try:
                inicio = time.perf_counter()
                resultado = engine.responder_pergunta(prompt, top_k=top_k)
                latencia = time.perf_counter() - inicio

                st.markdown(resultado["resposta"])
                st.caption(f"Tempo de resposta: {latencia:.2f}s")
                render_fontes(resultado["fontes"])

                # Salvar no historico da sessao
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": resultado["resposta"],
                    "fontes": resultado["fontes"],
                    "latencia": latencia
                })
                # Recarrega para a sidebar (badge e exportacao) refletir a nova resposta
                st.rerun()
            except Exception as err:
                st.error(f"Erro ao processar a pergunta: {err}")
