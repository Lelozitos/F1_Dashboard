import streamlit as st
from home import nav_bar

import fastf1.ergast
import plotly.express as px # https://dash.plotly.com/minimal-app
import pandas as pd
import numpy as np
import datetime

def calculate_max_points(year, round):
    POINTS_FOR_SPRINT = 8 + 25 + 1
    POINTS_FOR_CONVENTIONAL = 25 + 1

    events = fastf1.events.get_event_schedule(year, backend="ergast")

    events = events[events["RoundNumber"] > round]
    sprint_events = len(events.loc[events["EventFormat"] == "sprint_shootout"])
    conventional_events = len(events.loc[events["EventFormat"] == "conventional"])

    return (sprint_events*POINTS_FOR_SPRINT) + (conventional_events*POINTS_FOR_CONVENTIONAL)

def load_graphs(standings, year, round):
    MAX_POINTS = calculate_max_points(year, round)
    LEADER_POINTS = int(standings.iloc[0]["points"])

    cols = st.columns(3)
    for i in range(3):
        driver = standings.iloc[i]
        with cols[i].container(border=True):
            st.markdown(f"{driver['position']} | {driver['givenName']} {driver['familyName']} - {int(driver['points'])} {'Yes' if driver['points'] + MAX_POINTS >= LEADER_POINTS else 'No'} | {driver['constructorNames'][0]}")
            st.image(f"https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/{driver['givenName'][:1]}/{driver['givenName'][:3].upper()}{driver['familyName'][:3].upper()}01_{driver['givenName']}_{driver['familyName']}/{driver['givenName'][:3].lower()}{driver['familyName'][:3].lower()}01.png") # "https://media.formula1.com/image/upload/f_auto,c_limit,q_75,w_1320/content/dam/fom-website/drivers/{year}Drivers/{driver['familyName'].lower()}"

    for i in range(3, len(standings.index), 4):
        cols = st.columns(4)
        for j in range(4):
            try:
                driver = standings.iloc[i+j]
                with cols[j].container(border=True):
                    st.markdown(f"{driver['position']} | {driver['givenName']} {driver['familyName']} - {int(driver['points'])} {'Yes' if driver['points'] + MAX_POINTS >= LEADER_POINTS else 'No'} | {driver['constructorNames'][0]}")
                    st.image(f"https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/{driver['givenName'][:1]}/{driver['givenName'][:3].upper()}{driver['familyName'][:3].upper()}01_{driver['givenName']}_{driver['familyName']}/{driver['givenName'][:3].lower()}{driver['familyName'][:3].lower()}01.png") # "https://media.formula1.com/image/upload/f_auto,c_limit,q_75,w_1320/content/dam/fom-website/drivers/{year}Drivers/{driver['familyName'].lower()}"
            except: continue

    st.dataframe(standings)

def main():
    ergast = fastf1.ergast.Ergast()
    nav_bar()

    with st.sidebar:
        year = st.selectbox("Year", range(datetime.date.today().year, 2018-1, -1))
        data = fastf1.events.get_event_schedule(year).query("EventFormat != 'testing'")
        data.set_index("EventName", inplace=True)
        data = data[data["EventDate"] < np.datetime64("today") - 4] # too much time formats
        location = st.selectbox("Event", data.index[::-1])

        with st.spinner("Loading..."):
            standings = ergast.get_driver_standings(season=year, round=data.loc[location]["RoundNumber"]).content[0]
        st.success("Success!")

    st.header(f"{year} Drivers Championship | {location}", divider="rainbow")
    tabs = st.tabs(["👨‍👨‍👧‍👦 :orange[Standings]", ":orange[📈 Graph]"]) # not error
    with tabs[0]:
        load_graphs(standings, year, data.loc[location]["RoundNumber"])
    with tabs[1]:
        st.write("aaaaaaaaaaaaaa")

main()