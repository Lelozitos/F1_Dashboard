import streamlit as st
from home import nav_bar, credits

from graphs.graphs_session import *

import pandas as pd
import datetime

@st.cache_data(persist=True)
def load_session(year, location, session):
    print(year, location, session)
    data = fastf1.get_session(year, location, session)
    data.load(laps=True, telemetry=True, weather=True, messages=False, livedata=None)
    return data

def graph_results(session):
    results = session.results
    results = results.sort_values(by="Position")
    results = results.reset_index(drop=True)

    if session.session_info["Type"] == "Race":
        results["Display"] = results["Time"].dt.total_seconds()
        results["Display"] = results["Display"].fillna(results["Status"].str.replace("+", ""))
    elif session.session_info["Type"] == "Qualifying":
        results["Display"] = results["Q3"].dt.total_seconds()
        results["Display"] = results["Display"].fillna(results["Q2"].dt.total_seconds())
        results["Display"] = results["Display"].fillna(results["Q1"].dt.total_seconds())
        results["Display"] = results["Display"].fillna(results["Status"].str.replace("+", ""))
    # There is no session results for practice by this API

    # TODO format time race is entire race, qualifying is just one lap
    # results["Display"] = results["Display"].apply(lambda x: f"{int(x // 60)}.{x % 60:.3f}" if isinstance(x, (int, float)) else x)

    # TODO HeadshotURL awful quality
    # TODO old photos does not work
    cols = st.columns(3)
    for i in range(3):
        driver = results.iloc[i]
        with cols[i].container(border=True):
            if session.session_info["Type"] == "Race": st.markdown(f"{int(driver['Position'])} | {driver['FullName']} - {int(driver['Points'])} | {driver['TeamName']} | +{driver['Display']}")
            else: st.markdown(f"{int(driver['Position'])} | {driver['FullName']} | {driver['TeamName']} | +{driver['Display']}")
            st.image(driver['HeadshotUrl'], use_container_width=True)

    with st.expander("more..."):
        for i in range(3, len(results.index), 4):
            cols = st.columns(4)
            for j in range(4):
                try:
                    driver = results.iloc[i+j]
                    with cols[j].container(border=True):
                        if session.session_info["Type"] == "Race": st.markdown(f"{int(driver['Position'])} | {driver['FullName']} - {int(driver['Points'])} | {driver['TeamName']} | +{driver['Display']}")
                        else: st.markdown(f"{int(driver['Position'])} | {driver['FullName']} | {driver['TeamName']} | +{driver['Display']}")
                        st.image(driver['HeadshotUrl'], use_container_width=True)
                except: continue



def load_graphs(session):
    if session.session_info["Type"] != "Practice": graph_results(session)

    cols = st.columns(2)
    if session.session_info["Type"] == "Race": cols[0].plotly_chart(graph_drivers_posistion(session))
    else: cols[0].plotly_chart(graph_drivers_fastest_laps_time(session))
    cols[1].plotly_chart(graph_drivers_consistency(session))

    cols = st.columns(2)
    cols[0].plotly_chart(graph_teams_boxplot(session))
    cols[1].plotly_chart(graph_drivers_boxplot(session))

    cols = st.columns(2)
    cols[0].plotly_chart(graph_drivers_stints(session))
    cols[1].plotly_chart(graph_overall_tyre(session))

    cols = st.columns(2) # TODO maybe join these two graphs and make another for car style
    cols[0].plotly_chart(graph_drivers_top_speed(session))
    cols[1].plotly_chart(graph_car_style(session))

    cols = st.columns(2)
    cols[0].plotly_chart(graph_drivers_fastest_lap_telemetry(session))

    if session.session_info["Type"] == "Race":
        cols = st.columns([2,2,1])
        graph1, graph2, graph3 = graph_drivers_start(session)
        cols[0].plotly_chart(graph1)
        cols[1].plotly_chart(graph2)
        cols[2].plotly_chart(graph3)
        # cols[1].plotly_chart(graph_teams_pitstop(session)) # TODO API too broken to be reliable
    
        cols = st.columns(2)
        cols[0].plotly_chart(graph_weather(session))
        cols[1].plotly_chart(graph_wind(session))

def main():
    nav_bar()

    with st.sidebar:
        year = st.selectbox("Year", range(datetime.date.today().year, 2018 - 1, -1)) # Data only goes back to 2018
        data = fastf1.events.get_event_schedule(year).query("EventFormat != 'testing'")
        data.set_index("EventName", inplace=True)
        data = data[data["Session5DateUtc"] < (pd.Timestamp.utcnow() - pd.Timedelta("4h")).to_datetime64()]
        location = st.selectbox("Event", data.index[::-1])
        try: data = data.loc[location]
        except:
            st.error("Failed to load data.")
            return
        session = []
        for i in range(5, 0, -1):
            try: session.append(data.get_session_name(i)) # in case there is no practice 2, 3
            except ValueError as e:
                if "does not exist for this event" in e.__str__(): continue
                raise e
        session = st.selectbox("Session", session) # [data.get_session_name(i) for i in range(5, 0, -1)]

    if st.sidebar.button("Load", use_container_width=True):
        placeholder = st.sidebar.empty()
        with placeholder, st.spinner("Loading..."):
            data = load_session(year, location, session)
        st.sidebar.success("Success!")

        st.title(f"{year} - {location} | {session}")
        load_graphs(data)

    else:
        st.header("<--- Select date from sidebar")

    with st.sidebar:
        for _ in range(8): st.write("")
        credits()

main()