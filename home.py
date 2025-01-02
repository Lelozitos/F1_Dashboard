# python -m streamlit run ./home.py

import streamlit as st

def set_streamlit_page_config_once():
    try:
        st.set_page_config(page_title="F1", page_icon="🏎", layout="wide")
    except st.errors.StreamlitAPIException as e:
        if "can only be called once per app" in e.__str__(): return
        raise e

def nav_bar():
    set_streamlit_page_config_once()
    st.header("F1 CONSULTING", divider="rainbow")
    cols = st.columns(5)
    cols[0].page_link("home.py", label="**Home**", icon="🏡")
    cols[1].page_link("pages/sessions.py", label="**Sessions**", icon="🏎")
    cols[2].page_link("pages/teams.py", label="**Teams**", icon="👨‍👨‍👧‍👦")
    cols[3].page_link("pages/drivers.py", label="**Drivers**", icon="🙍‍♂️")
    cols[4].page_link("pages/contact.py", label="**Contact**", icon="📞")

def main():
    nav_bar()

main()

# https://public.tableau.com/app/profile/mateusz.karmalski/viz/F1ResultsTracker/Results 