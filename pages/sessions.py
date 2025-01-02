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
    data.load(laps=True, telemetry=True, weather=True, messages=False, livedata=None)
    return data

def graph_results(session): # TODO add lap times and delta
    results = session.results
    results = results.sort_values(by="Position")
    results = results.reset_index(drop=True)

    colors = []
    for driver in results["Abbreviation"].unique():
        try: colors.append(fastf1.plotting.driver_color(driver))
        except: colors.append("gray")

    # TODO HeadshotURL awful quality
    # TODO Qualifying position does not have points
    # TODO old photos does not work
    cols = st.columns(3)
    for i in range(3):
        driver = results.iloc[i]
        with cols[i].container(border=True):
            st.markdown(f"{int(driver['Position'])} | {driver['FullName']} - {int(driver['Points'])} | {driver['TeamName']}")
            st.image(driver['HeadshotUrl'], use_container_width=True)

    with st.expander("more..."):
        for i in range(3, len(results.index), 4):
            cols = st.columns(4)
            for j in range(4):
                try:
                    driver = results.iloc[i+j]
                    with cols[j].container(border=True):
                        st.markdown(f"{int(driver['Position'])} | {driver['FullName']} - {int(driver['Points'])} | {driver['TeamName']}")
                        st.image(driver['HeadshotUrl'], use_container_width=True)
                except: continue

def graph_drivers_posistion(session): # TODO Starting position not tracked. Add qualifying position # TODO sometimes legend is not in order 
    colors = []
    laps = session.laps.set_index("DriverNumber")
    laps = laps.loc[laps.index.intersection(session.drivers)] # Filter out drivers not in laps
    for driver in laps["Driver"].unique():
        try: colors.append(fastf1.plotting.driver_color(driver))
        except: colors.append("gray")

    fig = px.line(
        laps,
        x = "LapNumber",
        y = "Position",
        color = "Driver",
        color_discrete_sequence = colors,
        markers = True,
        hover_data = ["Team", "Compound", "Stint"] # TODO add starting position
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

def graph_fastest_laps(session):
    fastest_laps = []
    for driver in session.drivers:
        fastest_laps.append(session.laps.pick_driver(driver).pick_fastest())

    fastest_laps = fastf1.core.Laps(fastest_laps).sort_values(by="LapTime").reset_index(drop=True)

    pole_lap = fastest_laps.pick_fastest()
    fastest_laps['LapTimeDelta'] = fastest_laps['LapTime'] - pole_lap['LapTime']
    fastest_laps['LapTimeDelta'] = fastest_laps['LapTimeDelta'].dt.total_seconds()

    team_colors = []
    for index, lap in fastest_laps.iterlaps():
        color = fastf1.plotting.team_color(lap["Team"])
        team_colors.append(color)

    fig = px.bar(
        fastest_laps,
        x="LapTimeDelta",
        y="Driver",
        color="Driver", # TODO color by team instead, to add to legend
        color_discrete_sequence=team_colors,
        category_orders={"Driver": fastest_laps["Driver"]},
        hover_data=["LapTime", "Team", "LapNumber"],
        text_auto=True,    # TODO formmat this text, awful readability
        orientation="h"
    )

    fig.update_layout(
        title={"text": "Fastest Laps", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Lap Time Delta (s)", "color": "#F1F1F3"},
        yaxis = {"title": "Driver", "color": "#F1F1F3"},
        showlegend=False
    )

    return fig

def graph_drivers_consistency(session): # TODO add safety car periods and yellow flags
    laps = session.laps.pick_quicklaps() # Remove pit lanes -> this causes graph to start later, due to too much inconsistency in the beginning
    transformed_laps = laps.copy()
    transformed_laps["LapTime (s)"] = transformed_laps["LapTime"].dt.total_seconds()

    driver_order = (transformed_laps[["Driver", "LapTime (s)"]].groupby("Driver").median()["LapTime (s)"].sort_values().index)
    
    colors = []
    for driver in driver_order:
        try: colors.append(fastf1.plotting.driver_color(driver))
        except: colors.append("gray")

    transformed_laps = transformed_laps.set_index("Driver")
    transformed_laps = transformed_laps.loc[driver_order]
    transformed_laps["Compound"] = transformed_laps["Compound"].apply(str.capitalize)

    fig = px.line(
        transformed_laps,
        x="LapNumber",
        y="LapTime (s)",
        hover_data=["Team", "LapNumber", "Compound", "Stint", "TyreLife"],
        color=transformed_laps.index,
        color_discrete_sequence=colors,
        markers=True
    )

    fig.update_layout(
        title={"text": "Drivers' Consistency", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Lap №", "color": "#F1F1F3"},
        yaxis = {"title": "Lap Time (s)", "color": "#F1F1F3"},
    )

    fig.update_traces(
        marker={"line": {"color": "black", "width": 1}},
        textfont={"family": "Arial", "size": 12, "color": "#F1F1F3", "shadow": "1px 1px 2px black"}, # TODO austrian 2024 race gives error
    )

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

    fig = px.box(
        transformed_laps,
        x=transformed_laps.index,
        y="LapTime (s)",
        color=transformed_laps.index,
        color_discrete_sequence=colors
        )

    fig.update_layout(
        title={"text": "Lap Time Distribution by Team", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Teams", "color": "#F1F1F3"},
        yaxis = {"title": "Lap Time (s)", "color": "#F1F1F3"},
        legend = {"title": "Team", "font": {"color": "#F1F1F3"}},
    )
    return fig

def graph_drivers_boxplot(session):
    laps = session.laps.pick_quicklaps() # Remove pit lanes
    transformed_laps = laps.copy()
    transformed_laps["LapTime (s)"] = transformed_laps["LapTime"].dt.total_seconds()

    driver_order = (transformed_laps[["Driver", "LapTime (s)"]].groupby("Driver").median()["LapTime (s)"].sort_values().index)
    
    colors = []
    for driver in driver_order:
        try: colors.append(fastf1.plotting.driver_color(driver))
        except: colors.append("gray")

    transformed_laps = transformed_laps.set_index("Driver")
    transformed_laps = transformed_laps.loc[driver_order]

    fig = px.box(
        transformed_laps,
        x=transformed_laps.index,
        y="LapTime (s)",
        hover_data=["LapNumber", "Compound"],
        color=transformed_laps.index,
        color_discrete_sequence=colors
        )

    fig.add_hline(y=transformed_laps["LapTime (s)"].mean(), line_dash="dot", line_color="gray", annotation_text="Average", annotation_position="bottom right")

    fig.update_layout(
        title={"text": "Lap Time Distribution by Driver", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Drivers", "color": "#F1F1F3"},
        yaxis = {"title": "Lap Time (s)", "color": "#F1F1F3"},
        legend = {"title": "Driver", "font": {"color": "#F1F1F3"}},
    )

    return fig
    
def graph_drivers_stints(session): # TODO LapNumber in this case is the duration of stint, not the lap it was placed # TODO fix Tyrelife as well
    drivers = [session.get_driver(driver)["Abbreviation"] for driver in session.drivers]

    stints = session.laps[["Driver", "Stint", "Compound", "FreshTyre", "LapNumber", "TyreLife"]]

    stints = stints.groupby(["Driver", "Stint", "Compound", "FreshTyre"])
    stints = stints.count().reset_index()

    stints = stints.set_index("Driver")
    stints = stints.loc[stints.index.intersection(drivers[::-1])]
    stints.reset_index(inplace=True)

    fig = px.bar(
        stints,
        x="LapNumber",
        y="Driver",
        color="Compound",
        color_discrete_map=fastf1.plotting.COMPOUND_COLORS,
        hover_data=["Stint", "Compound", "TyreLife"],
        orientation="h",
        pattern_shape="FreshTyre", # TODO messes up the drivers order
        text_auto=True
    )

    fig.update_layout(
        title={"text": "Tyre Strategies", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Lap №", "color": "#F1F1F3"},
        yaxis = {"title": "Driver", "color": "#F1F1F3"},
        showlegend=False # TODO wish legend was with TEAMS or drivers, not compounds
    )

    fig.update_traces(
        marker={"line": {"color": "black", "width": 1}},
        textfont={"family": "Arial", "size": 12, "color": "#F1F1F3", "shadow": "1px 1px 2px black"},
    )

    return fig

def graph_overall_tyre(session):
    laps = session.laps.pick_quicklaps()
    laps = laps[["TyreLife", "Compound", "LapTime"]]
    laps = laps.groupby(["TyreLife", "Compound"])
    laps = laps.mean().reset_index()

    laps["LapTime"] = laps["LapTime"].dt.total_seconds()

    fig = px.line(
        laps,
        x="TyreLife",
        y="LapTime",
        color="Compound",
        color_discrete_map=fastf1.plotting.COMPOUND_COLORS,
        hover_data=["LapTime"],
        markers=True
    )

    fig.update_layout(
        title={"text": "Overall Tyre Degradation", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Tyre Life", "color": "#F1F1F3"},
        yaxis = {"title": "Lap Time (s)", "color": "#F1F1F3"},
    )

    return fig

def graph_drivers_top_speed(session): # TODO add 5 or 10 top speeds
    top_speeds = []
       
    for driver in session.drivers:
        try: # If driver has no laps, it will give an error
            telemetry = session.laps.pick_drivers([driver]).get_telemetry() # TODO optimize this
            telemetry["Driver"] = session.get_driver(driver)["Abbreviation"]
            top_speeds.append(telemetry.iloc[telemetry["Speed"].idxmax()])
        except: pass

    top_speeds = pd.DataFrame(top_speeds)
    top_speeds["DRS"] = top_speeds["DRS"] > 9 # not certain about drs number
    top_speeds = top_speeds.sort_values(by="Speed", ascending=False).reset_index(drop=True)

    colors = []
    for driver in top_speeds["Driver"]:
        try: colors.append(fastf1.plotting.driver_color(driver))
        except: colors.append("gray")

    fig = px.bar(
        top_speeds,
        x="Driver",
        y="Speed",
        color="Driver",
        color_discrete_sequence=colors,
        hover_data=["Speed"], # TODO add "LapNumber", "Compound", "Stint"
        pattern_shape="DRS", # TODO remove DRS from legend
        pattern_shape_map={True: "/", False: ""},
        text_auto=True,
        )

    fig.add_hline(y=top_speeds["Speed"].mean(), line_dash="dot", line_color="gray", annotation_text="Average", annotation_position="bottom right") # TODO remove outliers, if a driver has no top speed, messes up the average

    fig.update_layout(
        title={"text": "Top Speed", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Driver", "color": "#F1F1F3"},
        yaxis = {"title": "Speed (km/h)", "color": "#F1F1F3"},
        yaxis_range = [top_speeds["Speed"].min() - 10, top_speeds["Speed"].max() + 10],
    )

    fig.update_traces(
        marker={"line": {"color": "black", "width": 1}},
        textfont={"family": "Arial", "size": 12, "color": "#F1F1F3", "shadow": "1px 1px 2px black"},
    )

    return fig

def graph_car_style(session):
    # scatter plot with top speed and mean speed
    pass

def graph_drivers_start(session):
    # TODO every driver has the same starting distance, maybe api bug?
    # ^^^ kinda worried that distance is related with starting position, cuz every pole starts accelerating way sooner than the rest
    # ^^^ can be because the pole has the least speed going into a corner, so it can accelerate sooner

    # https://aws.amazon.com/sports/f1/start-analysis/

    telemetries = []
    first_lap = session.laps.pick_laps([1])
    for driver in session.drivers:
        try: # If driver has no laps, it will give an error
            telemetry = first_lap.pick_drivers([driver]).get_telemetry().add_distance()
            telemetry["Driver"] = session.get_driver(driver)["Abbreviation"]
            telemetries.append(telemetry)
        except: pass
    
    # Remove telemetry after the first curve
    for telemetry in telemetries:
        try: # If driver has no laps, it will give an error
            first_curve_index = telemetry[telemetry['Distance'] > session.get_circuit_info().corners.iloc[0]["Distance"]].index[0]
            telemetry.drop(telemetry.index[first_curve_index:], inplace=True)
        except: pass

    telemetries = pd.concat(telemetries)
    telemetries = telemetries.sort_values(by="Distance", ascending=False).reset_index(drop=True)

    colors = []
    for driver in telemetries["Driver"].unique():
        try: colors.append(fastf1.plotting.driver_color(driver))
        except: colors.append("gray")
    
    # TODO have no idea how to plot this, I wanted to show the throttle, break, speed and distance.
    fig = px.line(
        telemetries,
        x="Distance",
        y="Throttle",
        color="Driver",
        color_discrete_sequence=colors,
        hover_data=["Speed", "Brake"],
        markers=True
    )

    fig.update_layout(
        title={"text": "Start of the Race", "font": {"size": 30, "family": "Arial"}, "automargin": True, "xanchor": "center", "x": 0.5, "yanchor": "top", "y": 0.9},
        xaxis_title="Distance (m)",
        yaxis_title="Throttle %",
        # legend_title="Temperature",
    )

    return fig

def graph_teams_pitstop(session):
    pitstops = session.laps.pick_box_laps()
    pitstops = pitstops[["Driver", "Team", "PitInTime", "PitOutTime"]] # Driver to make it easier to calculate ?

    # Problem to calculate time in pits, since there is entering without exit (DNF) and multiple pitstops in a single lap
    st.dataframe(pitstops)

    pitstops = pitstops.groupby("Team")
    pitstops = pitstops.mean().reset_index()
    pitstops = pitstops.sort_values(by="PitStop", ascending=False)

    fig = px.bar(
        pitstops,
        x="Team",
        y="PitStop",
        color="Team",
        color_discrete_sequence=fastf1.plotting.TEAM_COLORS,
        text_auto=True
    )

    fig.update_layout(
        title={"text": "Pit Stops", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Driver", "color": "#F1F1F3"},
        yaxis = {"title": "Pit Stops", "color": "#F1F1F3"},
    )

    return fig

def graph_weather(session):
    weather_data = session.weather_data

    raining = False
    if weather_data["Rainfall"].sum() > len(weather_data.index) * .3:
        raining = True

    fig = px.line(
        weather_data,
        x="Time",
        y=["AirTemp", "TrackTemp"],
        labels={"value": "Temperature (°C)", "variable": "Temperature"},
        title="Weather Data Analysis",
        color_discrete_map={"AirTemp": "blue", "TrackTemp": "red"},
        markers=True,
    )

    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Temperature (°C)",
        legend_title="Temperature",
        title={"text": f"Weather Data Analysis | {'Raining' if raining else 'Clear'}", "font": {"size": 30, "family": "Arial"}, "automargin": True, "xanchor": "center", "x": 0.5, "yanchor": "top", "y": 0.9},
    )

    return fig

def load_graphs(session):
    if session.session_info["Type"] != "Practice": graph_results(session)

    cols = st.columns(2)
    if session.session_info["Type"] == "Race": cols[0].plotly_chart(graph_drivers_posistion(session))
    else: cols[0].plotly_chart(graph_fastest_laps(session))
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

    cols = st.columns(2) # TODO remove this for qualifying and practice
    cols[0].plotly_chart(graph_drivers_start(session))
    # cols[1].plotly_chart(graph_teams_pitstop(session))
    
    cols = st.columns(2)
    cols[0].plotly_chart(graph_weather(session))

def main():
    nav_bar()

    with st.sidebar:
        year = st.selectbox("Year", range(datetime.date.today().year, 2018 - 1, -1))
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
            st.cache_data.clear() # aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
            fastf1.Cache.clear_cache() # deep=True aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
            data = load_session(year, location, session)
        st.sidebar.success("Success!")

        st.title(f"{year} - {location} | {session}")
        load_graphs(data)

    else:
        st.header("<--- Select date from sidebar")

main()