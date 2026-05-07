import streamlit as st
from home import nav_bar, credits

from graphs.graphs_session import *
import fastf1

import pandas as pd
import datetime

@st.cache_resource
def load_session(year, location, session):
    print(year, location, session)
    data = fastf1.get_session(year, location, session)
    data.load(laps=True, telemetry=True, weather=True, messages=False, livedata=None)
    print(data.results)
    return data


def load_graphs(session):
    if session.session_info["Type"] != "Practice": 
        with st.spinner("Loading Results..."):
            graph_results(session)

    cols = st.columns(2)
    with cols[0]:
        with st.spinner("Loading Positions & Times..."):
            if session.session_info["Type"] == "Race": st.plotly_chart(graph_drivers_position(session))
            else: st.plotly_chart(graph_drivers_fastest_laps_time(session))
    
    with cols[1]:
        show_fuel_adj = True
        if session.session_info["Type"] == "Race":
            show_fuel_adj = st.toggle("Fuel Adjusted View", value=True, key="fuel_adj_toggle")
            
        with st.spinner("Loading Consistency..."):
            st.plotly_chart(graph_drivers_consistency(session, show_fuel_adj=show_fuel_adj))

    cols = st.columns(2)
    with cols[0]:
        with st.spinner("Loading Teams Boxplot..."):
            st.plotly_chart(graph_teams_boxplot(session))
            
    with cols[1]:
        with st.spinner("Loading Drivers Boxplot..."):
            st.plotly_chart(graph_drivers_boxplot(session))

    cols = st.columns(2)
    with cols[0]:
        with st.spinner("Loading Tyre Strategies..."):
            st.plotly_chart(graph_drivers_stints(session))
            
    with cols[1]:
        with st.spinner("Loading Tyre Performance..."):
            st.plotly_chart(graph_overall_tyre(session))

    cols = st.columns(2) # TODO maybe join these two graphs and make another for car style
    with cols[0]:
        with st.spinner("Loading Top Speeds..."):
            st.plotly_chart(graph_drivers_top_speed(session))
            
    with cols[1]:
        with st.spinner("Loading Car Style..."):
            st.plotly_chart(graph_car_style(session))

    cols = st.columns(2)
    with cols[0]:
        with st.spinner("Loading Engine Clipping..."):
            st.plotly_chart(graph_engine_clipping(session))
            
    with cols[1]:
        with st.spinner("Loading Detailed Clipping Stats..."):
            clipping_df = graph_engine_clipping_stats(session)
            if isinstance(clipping_df, pd.DataFrame) and not clipping_df.empty:
                # Engine colors mapping
                engine_colors = {
                    "Ferrari": "#FF4B4B", 
                    "Mercedes": "#00D2BE",
                    "Ford": "#005AFF",
                    "Audi": "#AA0000",
                    "Honda": "#006400"
                }
                
                def color_engine(val):
                    color = engine_colors.get(val, "white")
                    return f'color: {color}; font-weight: bold'

                styled_clipping = clipping_df.style.map(color_engine, subset=['Engine']) \
                    .background_gradient(cmap='Reds', subset=['Duration (s)', 'Speed Lost (km/h)', 'Severity (km/h/s)']) \
                    .format("{:.2f}", subset=['Duration (s)', 'Severity (km/h/s)']) \
                    .format("{:.1f}", subset=['Speed Lost (km/h)', 'Peak Speed'])

                st.markdown("### Detailed clipping impacts per straight")
                st.dataframe(styled_clipping, use_container_width=True, hide_index=True)
            else:
                st.plotly_chart(clipping_df)
            
    cols = st.columns(2)
    with cols[0]:
        with st.spinner("Loading Throttle Usage..."):
            st.plotly_chart(graph_full_throttle_pct(session))
    
    with cols[1]:
        # Track map is computationally heavy, load it on demand
        if 'load_track_map' not in st.session_state:
            st.session_state.load_track_map = False
            
        if not st.session_state.load_track_map:
            if st.button("🗺️ Load Animated Track Map", key="btn_load_track_map"):
                st.session_state.load_track_map = True
                st.rerun()
        else:
            with st.spinner("Loading Animated Track Map..."):
                st.plotly_chart(graph_drivers_curves(session))

    if session.session_info["Type"] == "Race":
        cols = st.columns([2,2,1])
        graph1, graph2, start_df = graph_drivers_start(session)
        cols[0].plotly_chart(graph1)
        cols[1].plotly_chart(graph2)
        
        if isinstance(start_df, pd.DataFrame) and not start_df.empty:
            styled_start = start_df.style.background_gradient(cmap='Greens_r', subset=['0-100', '100-200', '0-200']) \
                .format("{:.2f}s", subset=['0-100', '100-200', '0-200'])
            
            with cols[2]:
                st.markdown("### Launch Analysis (s)")
                st.dataframe(styled_start, use_container_width=True, hide_index=True)
        else:
            cols[2].plotly_chart(start_df)
        # cols[1].plotly_chart(graph_teams_pitstop(session)) # TODO API too broken to be reliable
    
        cols = st.columns(2)
        with cols[0]:
            with st.spinner("Loading Weather..."):
                st.plotly_chart(graph_weather(session))
                
        with cols[1]:
            with st.spinner("Loading Wind..."):
                st.plotly_chart(graph_wind(session))

def main():
    nav_bar()

    with st.sidebar:
        year = st.selectbox("Year", range(datetime.date.today().year, 2018 - 1, -1)) # Data only goes back to 2018
        data = fastf1.get_event_schedule(year).query("EventFormat != 'testing'")
        data.set_index("EventName", inplace=True)
        data = data[data["Session1DateUtc"] < (pd.Timestamp.utcnow()).to_datetime64()]
        location = st.selectbox("Event", data.index[::-1])
        try: data = data.loc[location]
        except:
            st.error("Failed to load data.")
            return
        session_names = []
        now = pd.Timestamp.utcnow().to_datetime64()
        for i in range(5, 0, -1):
            try:
                # Use data dictionary from get_event_schedule
                if data[f"Session{i}DateUtc"] < now:
                    session_names.append(data.get_session_name(i))
            except (ValueError, KeyError):
                continue
        
        if not session_names:
            st.warning("No finished sessions found for this event.")
            return

        session = st.selectbox("Session", session_names)

    # Reset loaded state if selection changes
    selection_key = f"{year}_{location}_{session}"
    if 'current_selection' not in st.session_state or st.session_state.current_selection != selection_key:
        st.session_state.loaded_session = False
        st.session_state.current_selection = selection_key
        st.session_state.load_track_map = False

    if st.sidebar.button("Load", use_container_width=True) or st.session_state.get('loaded_session', False):
        if not st.session_state.get('loaded_session', False):
            placeholder = st.sidebar.empty()
            with placeholder, st.spinner("Loading..."):
                st.session_state.session_data = load_session(year, location, session)
            st.session_state.loaded_session = True
            st.sidebar.success("Success!")

        st.title(f"{year} - {location} | {session}")
        load_graphs(st.session_state.session_data)

    else:
        st.header("<--- Select date from sidebar")

    with st.sidebar:
        for _ in range(8): st.write("")
        credits()

main()