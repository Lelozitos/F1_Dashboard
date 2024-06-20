# streamlit run ./home.py

import streamlit as st

def set_streamlit_page_config_once():
    try:
        st.set_page_config(page_title="F1", page_icon="🏎", layout="wide")
    except st.errors.StreamlitAPIException as e:
        if "can only be called once per app" in e.__str__():
            # ignore this error
            return
        raise e

def nav_bar():
    set_streamlit_page_config_once()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.page_link("home.py", label="Home", icon="🏡")
    col2.page_link("pages/sessions.py", label="Sessions", icon="🏎")
    col3.page_link("pages/teams.py", label="Teams", icon="👨‍👨‍👧‍👦")
    col4.page_link("pages/drivers.py", label="Drivers", icon="🙍‍♂️")
    col5.page_link("pages/contact.py", label="Contact", icon="📞")
    st.write("---")

def main():
    nav_bar()
    st.header("F1 CONSULTING", divider="rainbow")

main()