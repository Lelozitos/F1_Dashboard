import streamlit as st
from home import nav_bar, credits

from graphs.graphs_session import *
import fastf1

import pandas as pd
import datetime

@st.cache_data(persist=True)
def load_data(year):
    season = fastf1.get_event_schedule(year).query("EventFormat != 'testing'")
    for idx, event in season.iterrows():
        event.get_race().load()



        pass

    return event

def load_graphs(data):
    st.dataframe(data)

def main():
    nav_bar()

    with st.sidebar:
        year = st.selectbox("Year", range(datetime.date.today().year, 2018 - 1, -1)) # Data only goes back to 2018

    if st.sidebar.button("Load", width="stretch"):
        placeholder = st.sidebar.empty()
        with placeholder, st.spinner("Loading..."):
            data = load_data(year)
        st.sidebar.success("Success!")

        st.title(f"{year} | Season Overview")
        st.write("Season summary and statistics will be displayed here.")

        load_graphs(data)

    else:
        st.header("<--- Select date from sidebar")

    with st.sidebar:
        for _ in range(8): st.write("")
        credits()

main()