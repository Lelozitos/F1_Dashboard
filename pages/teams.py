import streamlit as st
from home import nav_bar, credits

import fastf1
from fastf1.ergast import Ergast

import plotly.express as px # https://dash.plotly.com/minimal-app
import pandas as pd
import numpy as np
import datetime

def load_standings(standings, year):
    # Team name mapping for logo URLs
    team_name_map = {
        "Red-Bull": "Red-Bull-Racing",
        "Sauber": "Kick-Sauber",
        "Alfa-Romeo": "Alfa-Romeo-Racing",
    }
    for i in range(0, 12, 2):
        cols = st.columns(2)
        for j in range(2):
            with cols[j].container(border=True):
                team = standings.iloc[i+j]
                name = team['constructorName'].replace(" ", "-")
                name = name.replace("-F1-Team", "")
                name = team_name_map.get(name, name)

                st.markdown(f"{int(team['position'])} | {name} - {int(team['points'])}")
                if name == "RB": st.markdown(f"![{name}](https://media.formula1.com/content/dam/fom-website/teams/{year}/{name}.png) ![{name}](https://media.formula1.com/content/dam/fom-website/teams/{year}/Racing-Bulls-logo.png)")
                else: st.markdown(f"![{name}](https://media.formula1.com/content/dam/fom-website/teams/{year}/{name}.png) ![{name}](https://media.formula1.com/content/dam/fom-website/teams/{year}/{name}-logo.png)")

def load_graphs(standings):
    pass

def main():
    ergast = Ergast()
    nav_bar()

    with st.sidebar:
        year = st.selectbox("Year", range(datetime.date.today().year, 2018-1, -1))
        data = fastf1.events.get_event_schedule(year).query("EventFormat != 'testing'")
        data.set_index("EventName", inplace=True)
        data = data[data["Session5DateUtc"] < (pd.Timestamp.utcnow() - pd.Timedelta("4h")).to_datetime64()]
        location = st.selectbox("Event", data.index[::-1])

        with st.spinner("Loading..."):
            try: standings = ergast.get_constructor_standings(season=year, round=data.loc[location]["RoundNumber"]).content[0]
            except:
                st.error("Failed to load data.")
                return
        st.success("Success!")

        for _ in range(15): st.write("")
        credits()

    st.title(f"{year} Constructors Championship | {location}")
    tabs = st.tabs(["👨‍👨‍👧‍👦 :orange[Standings]", ":orange[📈 Graph]"])
    with tabs[0]:
        load_standings(standings, year)
    with tabs[1]:
        st.write("aaaaaaaaaaaaaa")
        load_graphs(standings)

main()