import streamlit as st
from home import nav_bar

import plotly.express as px # https://dash.plotly.com/minimal-app
import pandas as pd
import numpy as np
import datetime

import fastf1.plotting
fastf1.Cache.set_disabled() # aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

# @st.cache_data
def load_session(year, location, session):
    print(year, location, session)
    data = fastf1.get_session(year, location, session)
    data.load(laps=True, telemetry=True, weather=False, messages=False, livedata=None)
    return data

def graph_drivers_qualifying(session):
    return fig

def graph_drivers_posistion(session):
    colors = []
    laps = session.laps.set_index("DriverNumber")
    laps = laps.loc[session.drivers] # not needed?
    for driver in laps["Driver"].unique():
        try: colors.append(fastf1.plotting.driver_color(driver))
        except: colors.append("gray")

    laps["Compound"] = laps["Compound"].apply(str.capitalize)

    fig = px.line(
        laps,
        x = "LapNumber",
        y = "Position",
        color = "Driver",
        color_discrete_sequence = colors,
        markers = True,
        hover_data = ["Team", "Compound", "Stint"] # ["Driver", "Position", "LapNumber"]
        )

    fig.update_layout(
        title={"text": "Posistion throughout the Race", "font": {"size": 30, "family":"Arial", "color": "#F1F1F3"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        width = 1000,
        height = 500,
        xaxis = {"title": "Lap №", "showgrid": False, "zeroline": False, "color": "#F1F1F3"},
        yaxis = {"title": "Position", "autorange": "reversed", "showgrid": False, "zeroline": False, "tickvals": [1, 5, 10, 15, 20], "color": "#F1F1F3"},
        legend = {"title": "Driver", "font": {"color": "#F1F1F3"}}, # "bgcolor": "#1e1c1b"
        # paper_bgcolor = "#292625",
        # plot_bgcolor = "#1e1c1b"
    )

    fig.update_traces(marker={"size": 4, "line": {"width": .2, "color": "DarkSlateGrey"}})
    
    return fig

def graph_teams_boxplot(session):
    laps = session.laps.pick_quicklaps()
    transformed_laps = laps.copy()
    transformed_laps["LapTime (s)"] = transformed_laps["LapTime"].dt.total_seconds()
    team_order = (
        transformed_laps[["Team", "LapTime (s)"]]
        .groupby("Team")
        .median()["LapTime (s)"]
        .sort_values()
        .index
    )

    colors = []
    for team in team_order:
        try: colors.append(fastf1.plotting.team_color(team))
        except: colors.append("gray")

    transformed_laps = transformed_laps.set_index("Team")
    transformed_laps = transformed_laps.loc[team_order]

    fig = px.box(transformed_laps, x=transformed_laps.index, y="LapTime (s)", color=transformed_laps.index, color_discrete_sequence=colors)

    fig.update_layout(
        title={"text": "Lap Time Distribution by Team", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Teams", "color": "#F1F1F3"},
        yaxis = {"title": "Lap Time (s)", "color": "#F1F1F3"},
        legend = {"title": "Team", "font": {"color": "#F1F1F3"}},
    )
    return fig

def load_graphs(session):
    cols = st.columns(2)
    if session.session_info["Type"] == "Race": cols[0].plotly_chart(graph_drivers_posistion(session))
    else: cols[0].plotly_chart(graph_drivers_qualifying)

    cols[1].plotly_chart(graph_teams_boxplot(session))

def main():
    nav_bar()

    with st.sidebar:
        year = st.selectbox("Year", range(datetime.date.today().year, 2018 - 1, -1))
        data = fastf1.events.get_event_schedule(year).query("EventFormat != 'testing'")
        data.set_index("EventName", inplace=True)
        data = data[data["EventDate"] < np.datetime64("today") - 4] # too much time formats
        location = st.selectbox("Event", data.index[::-1])
        data = data.loc[location]
        session = st.selectbox("Session", [data.get_session_name(i) for i in range(5, 0, -1)])

    if st.sidebar.button("Load", use_container_width=True):
        placeholder = st.sidebar.empty()
        with placeholder, st.spinner("Loading..."):
            st.cache_data.clear() # aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
            fastf1.Cache.clear_cache() # deep=True aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
            data = load_session(year, location, session)
        st.sidebar.success("Success!")

        st.header(f"{year} - {location} | {session}")
        load_graphs(data)

    else:
        st.header("<--- Select date from sidebar")

main()