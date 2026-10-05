import os
import sys
from dotenv import load_dotenv
load_dotenv()


import os
print("AIRFLOW_API_PASSWORD loaded:", bool(os.environ.get("AIRFLOW_API_PASSWORD")))

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["ANONYMIZED_TELEMETRY"] = "False"

import streamlit as st
from src.fabrilec.agent.agent import ask

st.set_page_config(page_title="Fabrilec - Assistant Appels d'Offres", page_icon="⚡")
st.title("Assistant Appels d'Offres Fabrilec")
st.caption("Posez une question sur les dossiers de consultation (CCTP, CPS, RC, bordereaux de prix...)")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if question := st.chat_input("Ex: Que dit le CCTP à propos des câbles BT armés ?"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Recherche en cours..."):
            answer = ask(question)
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})