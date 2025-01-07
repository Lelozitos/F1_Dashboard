import streamlit as st
from home import nav_bar, credits

import fastf1.ergast
import plotly.express as px # https://dash.plotly.com/minimal-app
import pandas as pd
import numpy as np
import datetime

def load_standings(standings, year):
    for i in range(0, 10, 2):
        cols = st.columns(2)
        for j in range(2):
            with cols[j].container(border=True):
                # TODO 2018 not supported
                team = standings.iloc[i+j]
                team['constructorName'] = team['constructorName'].replace(" ", "-")
                
                # TODO very instable, better to solve with own api
                if team['constructorName'] != "Haas-F1-Team": team['constructorName'] = team['constructorName'].replace("-F1-Team", "")
                if team['constructorName'] == "Red-Bull": team['constructorName'] = "Red-Bull-Racing"
                if team['constructorName'] == "Sauber": team['constructorName'] = "Kick-Sauber"
                if team['constructorName'] == "Alfa-Romeo": team['constructorName'] = "Alfa-Romeo-Racing"

                st.markdown(f"{int(team['position'])} | {team['constructorName']} - {int(team['points'])}")
                st.markdown(f"![{team['constructorName']}](https://media.formula1.com/content/dam/fom-website/teams/{year}/{team['constructorName']}.png) ![{team['constructorName']}](https://media.formula1.com/content/dam/fom-website/teams/{year}/{team['constructorName']}-logo.png)")

def load_graphs(standings):
    pass

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