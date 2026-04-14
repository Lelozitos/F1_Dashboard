import streamlit as st
from home import nav_bar, credits

from graphs.graphs_session import *
import fastf1

import pandas as pd
import datetime

@st.cache_data(persist=True)
def load_season(year):
    season = fastf1.get(year)
    return season

def load_graphs(data):
    st.dataframe(data)

def main():
    nav_bar()



    with st.sidebar:
        for _ in range(8): st.write("")
        credits()

main()