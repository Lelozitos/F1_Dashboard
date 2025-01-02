import streamlit as st
from home import nav_bar

import fastf1.ergast
import plotly.express as px # https://dash.plotly.com/minimal-app
import pandas as pd
import numpy as np
import datetime

def load_graphs(standings):
    for i in range(0, 10, 2):
        cols = st.columns(2)
        for j in range(2):
            team = standings.iloc[i+j]
            cols[j].text(f"{team['constructorName']} - {int(team['points'])}")

    st.dataframe(standings)

def main():
    ergast = fastf1.ergast.Ergast()
    nav_bar()

    with st.sidebar:
        year = st.selectbox("Year", range(datetime.date.today().year, 2018-1, -1))
        data = fastf1.events.get_event_schedule(year).query("EventFormat != 'testing'")
        data.set_index("EventName", inplace=True)
        # print("a\n"*50)
        # print(type(datetime.timedelta(hours=4)))
        data = data[data["Session5DateUtc"] < (pd.Timestamp.utcnow() - pd.Timedelta("4h")).to_datetime64()]
        location = st.selectbox("Event", data.index[::-1])

        with st.spinner("Loading..."):
            standings = ergast.get_constructor_standings(season=year, round=data.loc[location]["RoundNumber"]).content[0]
        st.success("Success!")

    st.title(f"{year} Constructors Championship | {location}")
    tabs = st.tabs(["👨‍👨‍👧‍👦 :orange[Standings]", ":orange[📈 Graph]"])
    with tabs[0]:
        load_graphs(standings)
    with tabs[1]:
        st.write("aaaaaaaaaaaaaa")

main()