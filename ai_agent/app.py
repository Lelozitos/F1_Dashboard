import anthropic
import streamlit as st

from agent import get_client, run_turn

st.set_page_config(page_title="F1 AI Analyst", page_icon="🏎️", layout="centered")
st.title("🏎️ F1 AI Analyst")
st.caption(
    "Pergunte qualquer coisa sobre sessões, standings, tempos de volta ou pit stops. "
    "As respostas usam dados reais buscados ao vivo via FastF1, Ergast e OpenF1."
)

if "client" not in st.session_state:
    try:
        st.session_state.client = get_client()
    except Exception as e:
        st.error(f"Failed to initialize Claude client: {e}")
        st.stop()

if "display_messages" not in st.session_state:
    st.session_state.display_messages = []
if "api_messages" not in st.session_state:
    st.session_state.api_messages = []

for msg in st.session_state.display_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input(
    "Ex: Quem venceu o GP de Mônaco 2023? Compare a volta mais rápida de VER e LEC na Q de Monza 2024."
)

if prompt:
    st.session_state.display_messages.append({"role": "user", "content": prompt})
    st.session_state.api_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("🔧 _Buscando dados..._")
        try:
            final_text, updated_messages, tool_calls = run_turn(
                st.session_state.client, st.session_state.api_messages
            )
            st.session_state.api_messages = updated_messages

            if tool_calls:
                with st.expander(f"🔧 Tools usadas ({len(tool_calls)})"):
                    for name in tool_calls:
                        st.write(f"- `{name}`")

            placeholder.markdown(final_text or "_Sem resposta do modelo._")
            st.session_state.display_messages.append(
                {"role": "assistant", "content": final_text or "_Sem resposta do modelo._"}
            )
        except anthropic.AuthenticationError:
            placeholder.error("Chave de API inválida. Configure ANTHROPIC_API_KEY ou rode `ant auth login`.")
        except anthropic.APIStatusError as e:
            placeholder.error(f"Erro da API Claude ({e.status_code}): {e.message}")
        except Exception as e:
            placeholder.error(f"Erro: {e}")

with st.sidebar:
    st.markdown("### 🏎️ F1 AI Analyst")
    st.markdown(
        "Agente com tool use sobre:\n"
        "- FastF1 (sessões, voltas, resultados, clima)\n"
        "- Ergast (standings, calendário)\n"
        "- OpenF1 (pit stops)"
    )
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.display_messages = []
        st.session_state.api_messages = []
        st.rerun()
