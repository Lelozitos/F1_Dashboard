"""AI chat page - wraps the Gemini tool-use agent (agent.py/tools.py at repo
root) as an app tab. Only reachable when GEMINI_API_KEY is set; the nav bar
disables this tab's link otherwise (see app.py)."""
import os

import streamlit as st
from google.genai import errors

from app import nav_bar, credits
from agent import get_client, new_chat, run_turn


def main():
    nav_bar()
    st.header("🏎️ F1 Chat")
    st.caption("Ask about a session, standing, lap time or pit stop. Real data, not a guess.")

    if not os.environ.get("GEMINI_API_KEY"):
        st.warning(
            "Needs a `GEMINI_API_KEY`. Add it to `.env` at the repo root "
            "(see `.env.example`), then reload."
        )
        st.stop()

    if "ai_client" not in st.session_state:
        try:
            st.session_state.ai_client = get_client()
        except Exception as e:
            st.error(f"Failed to initialize Gemini client: {e}")
            st.stop()

    if "ai_chat" not in st.session_state:
        st.session_state.ai_chat = new_chat(st.session_state.ai_client)

    if "ai_display_messages" not in st.session_state:
        st.session_state.ai_display_messages = []

    for msg in st.session_state.ai_display_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("E.g.: Who won the 2023 Monaco GP?")

    if prompt:
        st.session_state.ai_display_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("🔧 _Fetching data..._")
            try:
                final_text, tool_calls = run_turn(st.session_state.ai_chat, prompt)

                if tool_calls:
                    with st.expander(f"🔧 Tools used ({len(tool_calls)})"):
                        for name in tool_calls:
                            st.write(f"- `{name}`")

                placeholder.markdown(final_text or "_No answer._")
                st.session_state.ai_display_messages.append(
                    {"role": "assistant", "content": final_text or "_No answer._"}
                )
            except errors.ClientError as e:
                placeholder.error(f"Request failed ({e}). Check your GEMINI_API_KEY.")
            except errors.ServerError as e:
                placeholder.error(f"Gemini is down right now: {e}")
            except Exception as e:
                placeholder.error(f"Error: {e}")

    with st.sidebar:
        if st.button("🗑️ Clear conversation", use_container_width=True):
            st.session_state.ai_chat = new_chat(st.session_state.ai_client)
            st.session_state.ai_display_messages = []
            st.rerun()
        credits()


if __name__ == "__main__":
    main()
