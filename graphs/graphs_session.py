import plotly.express as px
import plotly.graph_objects as go

import pandas as pd
import numpy as np
import datetime

import fastf1.plotting
import fastf1.api
import requests

def graph_drivers_posistion(session):
    colors = []
    laps = session.laps.copy().set_index("DriverNumber")[["Driver", "LapNumber", "Stint", "Compound", "Team", "Position", "TrackStatus"]]
    laps.loc[:,"GridPosition"] = session.results["GridPosition"]

    grid = pd.DataFrame(session.results["GridPosition"])
    grid.rename(columns={"GridPosition": "Position"}, inplace=True)
    grid["LapNumber"] = 0
    
    # Hate how this is done btw # TODO fix that pls i hate it
    grid_names = []
    for driver in grid.index:
        grid_names.append(session.get_driver(driver)["Abbreviation"])
    grid["Driver"] = grid_names
    grid = grid[grid["Position"] != 0] # In case of a pit lane start
    
    laps = pd.concat([laps, grid])
    # laps.fillna(method="ffill", inplace=True) # Wish this worked

    laps.sort_values(["LapNumber"], inplace=True)
    laps = laps.loc[session.drivers] # Filter out drivers not in laps, might cause an error
    for driver in laps["Driver"].unique():
        try: colors.append(fastf1.plotting.get_driver_color(driver, session))
        except: colors.append("gray")

    fig = px.line(
        laps,
        x = "LapNumber",
        y = "Position",
        color = "Driver",
        color_discrete_sequence = colors,
        markers = True,
        hover_data = ["GridPosition", "Team", "Compound", "Stint"], # TODO add starting position
        )

    fig.update_layout(
        title={"text": "Posistion throughout the Race", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        width = 1000,
        height = 500,
        xaxis = {"title": "Lap №", "showgrid": False, "zeroline": False},
        yaxis = {"title": "Position", "autorange": "reversed", "showgrid": False, "zeroline": False, "tickvals": [1, 5, 10, 15, 20]},
    )

    fig.update_traces(
        marker=dict(
            size=5,
            line=dict(
                width=.5,
                color="black"
            )
        ),
        line=dict(
            width=3,
        )
    )
    
    return fig

def graph_drivers_fastest_laps_time(session):
    fastest_laps = []
    for driver in session.drivers:
        fastest_laps.append(session.laps.pick_drivers([driver]).pick_fastest())

    fastest_laps = fastf1.core.Laps(fastest_laps).sort_values(by="LapTime").reset_index(drop=True)

    pole_lap = fastest_laps.pick_fastest()
    fastest_laps['LapTimeDelta'] = fastest_laps['LapTime'] - pole_lap['LapTime']
    fastest_laps['LapTimeDelta'] = fastest_laps['LapTimeDelta'].dt.total_seconds()

    team_colors = []
    for team in fastest_laps["Team"].unique():
        color = fastf1.plotting.get_team_color(team, session)
        team_colors.append(color)

    fig = px.bar(
        fastest_laps,
        x="LapTimeDelta",
        y="Driver",
        color="Team",
        color_discrete_sequence=team_colors,
        category_orders={"Driver": fastest_laps["Driver"]},
        hover_data=["LapTime", "Team", "LapNumber"],
        text_auto=True,
        orientation="h"
    )

    fig.update_layout(
        title={"text": "Fastest Laps", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Lap Time Delta (s)"},
        yaxis = {"title": "Driver"},
    )
    
    fig.update_traces(
        marker={"line": {"color": "black", "width": 1}},
        textfont={"family": "Arial", "size": 12, "color": "#F1F1F3", "shadow": "1px 1px 2px black"},
    )

    return fig

def graph_drivers_consistency(session): # TODO add safety car periods and yellow flags (Open F1)
    laps = session.laps.pick_quicklaps() # Remove pit lanes -> this causes graph to start later, due to too much inconsistency in the beginning
    transformed_laps = laps.copy()
    transformed_laps["LapTime (s)"] = transformed_laps["LapTime"].dt.total_seconds()

    driver_order = (transformed_laps[["Driver", "LapTime (s)"]].groupby("Driver").median()["LapTime (s)"].sort_values().index)
    
    colors = []
    for driver in driver_order:
        try: colors.append(fastf1.plotting.get_driver_color(driver, session))
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
        xaxis = {"title": "Lap №"},
        yaxis = {"title": "Lap Time (s)"},
    )

    fig.update_traces(
        marker=dict(
            size=8,
            line=dict(
                width=1,
                color="black"
            )
        ),
        line=dict(
            width=3,
        )
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
        try: colors.append(fastf1.plotting.get_team_color(team, session))
        except: colors.append("gray")

    transformed_laps = transformed_laps.set_index("Team")
    transformed_laps = transformed_laps.loc[team_order]

    median_lap_times = transformed_laps.groupby("Team")["LapTime (s)"].median().sort_values()
    fastest_median = median_lap_times.min()
    median_differences = median_lap_times - fastest_median

    custom_x_labels = [
        f"{team}<br>+{diff:.2f}s" if diff > 0 else f"{team}<br>{diff:.2f}s"
        for team, diff in median_differences.items()
    ]

    fig = px.box(
        transformed_laps,
        x=transformed_laps.index,
        y="LapTime (s)",
        color=transformed_laps.index,
        color_discrete_sequence=colors
        )

    fig.update_layout(
        title={"text": "Lap Time Distribution by Team", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis={
            "title": "Teams",
            "ticktext": custom_x_labels,
            "tickvals": team_order
        },
        yaxis = {"title": "Lap Time (s)"},
    )

    fig.update_traces(
        marker=dict(
            size=8,
            line=dict(
                width=1,
                color="black"
            )
        ),
        line=dict(
            width=2,
        )
    )

    return fig

def graph_drivers_boxplot(session):
    laps = session.laps.pick_quicklaps() # Remove pit lanes
    transformed_laps = laps.copy()
    transformed_laps["LapTime (s)"] = transformed_laps["LapTime"].dt.total_seconds()

    driver_order = (
        transformed_laps[["Driver", "LapTime (s)"]]
        .groupby("Driver")
        .median()["LapTime (s)"]
        .sort_values()
        .index
    )
    
    colors = []
    for driver in driver_order:
        try: colors.append(fastf1.plotting.get_driver_color(driver, session))
        except: colors.append("gray")

    transformed_laps = transformed_laps.set_index("Driver")
    transformed_laps = transformed_laps.loc[driver_order]

    median_lap_times = transformed_laps.groupby("Driver")["LapTime (s)"].median().sort_values()
    fastest_median = median_lap_times.min()
    median_differences = median_lap_times - fastest_median

    custom_x_labels = [
        f"{driver}<br>+{diff:.2f}s" if diff > 0 else f"{driver}<br>{diff:.2f}s"
        for driver, diff in median_differences.items()
    ]

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
        xaxis={
            "title": "Drivers",
            "ticktext": custom_x_labels,
            "tickvals": driver_order
        },
        yaxis = {"title": "Lap Time (s)"},
    )

    fig.update_traces(
        marker=dict(
            size=8,
            line=dict(
                width=1,
                color="black"
            )
        ),
        line=dict(
            width=2,
        )
    )

    return fig
    
def graph_drivers_stints(session): # TODO LapNumber in this case is the duration of stint, not the lap it was placed # TODO stint order messed up
    driver_order = [session.get_driver(driver)["Abbreviation"] for driver in session.drivers]

    stints = session.laps[["Driver", "Stint", "Compound", "FreshTyre", "LapNumber"]]

    stints = stints.groupby(["Driver", "Stint", "Compound", "FreshTyre"])
    stints = stints.count().reset_index()

    fig = px.bar(
        stints,
        x="LapNumber",
        y="Driver",
        color="Compound",
        color_discrete_map=fastf1.plotting.get_compound_mapping(session),
        hover_data=["Stint", "Compound"],
        orientation="h",
        pattern_shape="FreshTyre",
        pattern_shape_map={True: "", False: "/"},
        text_auto=True,
        category_orders={"Driver": driver_order}
    )

    fig.update_layout(
        title={"text": "Tyre Strategies", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Lap №"},
        yaxis = {"title": "Driver"},
        showlegend=False # TODO wish legend was with TEAMS or drivers, not compounds
    )

    fig.update_traces(
        marker={"line": {"color": "gray", "width": 1}, "pattern_fillmode": "overlay"},
        textfont={"family": "Arial", "size": 16, "color": "#F1F1F3", "shadow": "1px 1px 6px black", "weight": "bold"},
        insidetextanchor="middle",
    )

    for trace in fig.data:
        if trace.marker.color in ["#f0f0ec"]:
            trace.update(
                textfont=dict(
                    color="black",
                    shadow="1px 1px 6px white"
                )
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
        color_discrete_map=fastf1.plotting.get_compound_mapping(session),
        hover_data=["LapTime"],
        markers=True
    )

    fig.update_layout(
        title={"text": "Overall Tyre Degradation", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Tyre Life"},
        yaxis = {"title": "Lap Time (s)"},
    )

    fig.update_traces(
        marker=dict(
            size=10,
            line=dict(
                width=1,
                color="black"
            )
        ),
        line=dict(
            width=3,
        )
    )

    return fig

def graph_drivers_top_speed(session): # TODO add 5 or 10 top speeds
    top_speeds = []
       
    for driver in session.drivers:
        try: # If driver has no laps, it will give an error
            telemetry = session.laps.pick_drivers([driver]).get_car_data()
            telemetry["Driver"] = session.get_driver(driver)["Abbreviation"]
            top_speeds.append(telemetry.iloc[telemetry["Speed"].idxmax()])
        except: pass

    top_speeds = pd.DataFrame(top_speeds)
    top_speeds["DRS"] = top_speeds["DRS"] > 9 # not certain about drs number
    top_speeds = top_speeds.sort_values(by="Speed", ascending=False).reset_index(drop=True)

    colors = []
    for driver in top_speeds["Driver"]:
        try: colors.append(fastf1.plotting.get_driver_color(driver, session))
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
        xaxis = {"title": "Driver"},
        yaxis = {"title": "Speed (km/h)"},
        yaxis_range = [top_speeds["Speed"].min() - 5, top_speeds["Speed"].max() + 5],
        showlegend=False    
    )

    fig.update_traces(
        marker={"line": {"color": "gray", "width": 1}, "pattern_fillmode": "overlay"},
        textfont={"family": "Arial", "size": 12, "color": "#F1F1F3", "shadow": "1px 1px 2px black"},
    )

    return fig

def graph_car_style(session):
    # Scatter plot with top speed and mean speed
    # TODO better to do by team, since it is the car style
    speeds = []
       
    for driver in session.drivers:
        try: # If driver has no laps, it will give an error
            telemetry = session.laps.pick_drivers([driver]).pick_quicklaps().get_car_data() # Remove pit lanes for mean speed
            telemetry["Driver"] = session.get_driver(driver)["Abbreviation"]
            telemetry["MeanSpeed"] = telemetry["Speed"].mean()
            telemetry.rename(columns={"Speed": "TopSpeed"}, inplace=True)
            speeds.append(telemetry.iloc[telemetry["TopSpeed"].idxmax()])
        except: pass

    speeds = pd.DataFrame(speeds)
    speeds["DRS"] = speeds["DRS"] > 9 # not certain about drs number

    colors = []
    for driver in speeds["Driver"]:
        try: colors.append(fastf1.plotting.get_driver_color(driver, session))
        except: colors.append("gray")

    fig = px.scatter(
        speeds,
        x="MeanSpeed",
        y="TopSpeed",
        color="Driver",
        color_discrete_sequence=colors,
        hover_data=["DRS"],
        )

    fig.update_layout(
        title={"text": "Car Style", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Mean Speed (km/h)"},
        yaxis = {"title": "Top Speed (km/h)"} ,
    )

    fig.update_traces(
        marker=dict(
            size=10,
            line=dict(
                color="black",
                width=1.5,
            ),
        )
    )

    return fig

def graph_drivers_start(session):
    # Every driver has the same starting distance, maybe api bug?
    # ^^^ kinda worried that distance is related with starting position, cuz every pole starts accelerating way sooner than the rest
    # ^^^ can be because the pole has the least speed going into a corner, so it can accelerate sooner
    # Almost certain distance is 0 for every driver start, that means that the first curve is later in distance for the last than pole
    # https://aws.amazon.com/sports/f1/start-analysis/

    telemetries = []
    first_lap = session.laps.pick_laps([1])
    for driver in session.drivers:
        try: # If driver has no laps, it will give an error
            telemetry = first_lap.pick_drivers([driver]).get_car_data().add_distance().fill_missing() # TODO increase frequency
            telemetry["Driver"] = session.get_driver(driver)["Abbreviation"]
            telemetries.append(telemetry)
        except: pass
    
    telemetries = pd.concat(telemetries)

    # Remove telemetry after the first curve
    telemetries.sort_values("Distance", inplace=True)
    telemetries.reset_index(drop=True, inplace=True)
    first_curve_index = telemetries[telemetries['Distance'] > session.get_circuit_info().corners.iloc[0]["Distance"]].index[0]
    telemetries = telemetries.iloc[:first_curve_index]

    # Keep legend order
    driver_order = [session.get_driver(driver)["Abbreviation"] for driver in session.drivers]
    telemetries = telemetries.set_index("Driver")
    telemetries = telemetries.loc[driver_order]
    telemetries.reset_index(inplace=True)

    telemetries["Time"] = telemetries["Time"].dt.total_seconds()

    colors = []
    for driver in telemetries["Driver"].unique():
        try: colors.append(fastf1.plotting.get_driver_color(driver, session))
        except: colors.append("gray")

    # GRAPHS

    fig1 = px.line(
        telemetries,
        x="Time",
        y="Throttle",
        color="Driver",
        color_discrete_sequence=colors,
        hover_data=["Speed", "Brake"],
        markers=True
    )

    fig1.update_layout(
        title={"text": "Throttle at start of the Race", "font": {"size": 30, "family": "Arial"}, "automargin": True, "xanchor": "center", "x": 0.5, "yanchor": "top", "y": 0.9},
        xaxis_title="Time (s)",
        yaxis_title="Throttle %",
    )

    fig2 = px.line(
        telemetries,
        x="Time",
        y="Speed",
        color="Driver",
        color_discrete_sequence=colors,
        hover_data=["Speed", "Brake"],
        markers=True
    )

    fig2.update_layout(
        title={"text": "Speed at start of the Race", "font": {"size": 30, "family": "Arial"}, "automargin": True, "xanchor": "center", "x": 0.5, "yanchor": "top", "y": 0.9},
        xaxis_title="Time (s)",
        yaxis_title="Speed (km/h)",
    )

    speed_times = pd.DataFrame(columns=["Driver", "0-100", "100-200", "0-200"])

    # Iterate through each unique driver and calculate times
    for driver in telemetries["Driver"].unique():
        # Filter the telemetry data for the current driver
        driver_data = telemetries[telemetries["Driver"] == driver]
        
        # Find the time to reach 100 km/h and 200 km/h
        time_100 = driver_data[driver_data["Speed"] > 100].iloc[0]["Time"] if not driver_data[driver_data["Speed"] > 100].empty else None
        time_200 = driver_data[driver_data["Speed"] > 200].iloc[0]["Time"] if not driver_data[driver_data["Speed"] > 200].empty else None
        
        # Append the results to the DataFrame
        speed_times = pd.concat([speed_times, pd.DataFrame([[driver, time_100, time_200-time_100, time_200]], columns=speed_times.columns)], ignore_index=True)
            
    speed_times = speed_times.round(2)
    speed_times.sort_values("0-200", inplace=True)

    fig3 = go.Figure(data=go.Table(
        header=dict(
            values=["", "<b>0-100</b>", "<b>100-200</b>", "<b>0-200</b>"],
            line_color=["rgba(0,0,0,0)", "darkslategray", "darkslategray"],
            fill_color=["rgba(0,0,0,0)", "blue", "blue"]
        ),
        cells=dict(
            values=[speed_times["Driver"], speed_times["0-100"], speed_times["100-200"], speed_times["0-200"]],
            line_color="darkslategray",fill_color=["lightgray"],
            align="center", font=dict(color="black", size=11)
        )
    ))

    fig3.update_layout(
        title={"text": "Time for Speed", "font": {"size": 30, "family": "Arial"}, "automargin": True, "xanchor": "center", "x": 0.5, "yanchor": "top", "y": 0.9},
        margin=dict(l=10, r=10, t=50, b=20)
    )

    return fig1, fig2, fig3

def graph_teams_pitstop(session):
    pits = requests.get(f"https://api.openf1.org/v1/pit?session_key={session.session_info["Key"]}")
    pits = pd.DataFrame(pits.json())
    pits["team"] = pits["driver_number"]
    pits["team"] = pits["team"].apply(lambda x: fastf1.plotting.get_team_name_by_driver(session.get_driver(str(x))["Abbreviation"], session))
    
    pits = pits[["pit_duration", "team"]]
    pits = pits.groupby("team")
    pits = pits.sum().reset_index()
    pits.sort_values("pit_duration", inplace=True)

    team_colors = []
    for team in pits["team"].unique():
        color = fastf1.plotting.get_team_color(team, session)
        team_colors.append(color)

    fig = px.bar(
        pits,
        x="team",
        y="pit_duration",
        color="team",
        color_discrete_sequence=team_colors,
        text_auto=True
    )

    fig.update_layout(
        title={"text": "Time in Pits", "font": {"size": 30, "family": "Arial"}, "automargin": True, "xanchor": "center", "x": 0.5, "yanchor": "top", "y": 0.9},
        xaxis_title="Team",
        yaxis_title="Pit Duration (s)",
    )

    return fig

def graph_drivers_fastest_lap_telemetry(session):
    telemetries = []
    for driver in session.drivers:
        try: # If driver has no laps, it will give an error
            lap = session.laps.pick_drivers([driver]).pick_fastest()
            telemetry = lap.get_car_data().add_distance()
            telemetry["Driver"] = session.get_driver(driver)["Abbreviation"]
            telemetry["LapTime (s)"] = lap["LapTime"].total_seconds()
            telemetry["Compound"] = lap["Compound"]
            telemetry["TyreLife"] = lap["TyreLife"]
            telemetries.append(telemetry)
        except: pass
    
    telemetries = pd.concat(telemetries)

    colors = []
    for driver in telemetries["Driver"].unique():
        try: colors.append(fastf1.plotting.get_driver_color(driver, session))
        except: colors.append("gray")

    fig = px.line(
        telemetries,
        x="Distance",
        y="Speed",
        color="Driver",
        color_discrete_sequence=colors,
        hover_data=["Speed", "Throttle", "Brake", "RPM", "nGear", "LapTime (s)", "Compound", "TyreLife"],
        markers=True
    )

    # TODO add curves distances
    for curve in session.get_circuit_info().corners.iterrows():
        curve = curve[1]
        fig.add_vline(x=curve["Distance"], line_dash="dot", line_color="gray", annotation_text=curve["Number"], annotation_position="bottom right")

    fig.update_layout(
        title={"text": "Speed throughout fastest lap", "font": {"size": 30, "family": "Arial"}, "automargin": True, "xanchor": "center", "x": 0.5, "yanchor": "top", "y": 0.9},
        xaxis_title="Distance (m)",
        yaxis_title="Speed (km/h)",
    )

    return fig

def graph_drivers_curves(session): # https://plotly.com/python/v3/dropdowns/
    # choose lap and curve to analyze the speed, throttle and brake
    pass

def graph_weather(session):
    weather_data = session.weather_data

    # Maybe fastf1.api can break someday
    weather_data = pd.merge_asof(weather_data, pd.DataFrame(fastf1.api.lap_count(session.api_path)), on="Time", direction="backward")
    weather_data.drop_duplicates(subset=["CurrentLap"], keep="last", inplace=True)

    raining = False
    if weather_data["Rainfall"].any(): # len(weather_data.index) * .3
        raining = True

    fig = px.line(
        weather_data,
        x="CurrentLap",
        y=["AirTemp", "TrackTemp"],
        labels={"value": "Temperature (°C)"},
        title="Weather Data Analysis",
        color_discrete_map={"AirTemp": "gray", "TrackTemp": "red"},
        markers=True,
    )

    for data in fig.data:
        data.update(
            hovertemplate="<b>Lap:</b> %{x}<br><b>Temperature:</b> %{y:.1f} °C<extra></extra>"
        )

    fig.add_scatter(
        x=weather_data["CurrentLap"], y=weather_data["Humidity"], mode="lines+markers",
        name="Humidity", line=dict(color="blue", dash="dot"),
        yaxis="y2",  # Link to secondary Y-axis
        hovertemplate="<b>Lap:</b> %{x}<br><b>Humidity:</b> %{y:.2f} %<extra></extra>"  # Custom hover text
    )

    fig.update_layout(
        title={"text": f"Weather Data Analysis | {'Raining' if raining else 'Clear'}", "font": {"size": 30, "family": "Arial"}, "automargin": True, "xanchor": "center", "x": 0.5, "yanchor": "top", "y": 0.9},
        xaxis_title="Lap №",
        yaxis_title="Temperature (°C)",
        yaxis2=dict(
            title="Humidity (%)",
            overlaying="y",  # Overlay the secondary axis on the same plot
            side="right"  # Position the secondary axis on the right
        ),
        legend_title="Variables",
    )
    
    # TODO if it stops raining and starts again, it will fail
    rains = weather_data[weather_data["Rainfall"] == True]

    if raining:
        fig.update_layout(
            shapes=[
                dict(
                    type="rect",
                    xref="x",
                    yref="paper",
                    x0=rains.iloc[0]["CurrentLap"],
                    x1=rains.iloc[-1]["CurrentLap"],
                    y0=0,
                    y1=1,
                    fillcolor="LightBlue",
                    opacity=0.5,
                    layer="below",
                    line_width=0
                )
            ],
            annotations=[
                dict(
                    x=(rains.iloc[0]["CurrentLap"] + rains.iloc[-1]["CurrentLap"])/2,
                    y=1.05, 
                    xref="x",
                    yref="paper",
                    text="Rain Interval",
                    showarrow=False,
                    font=dict(size=12, color="blue"),
                    align="center",
                    bgcolor="LightBlue",
                    borderwidth=1
                )
            ]
        )

    return fig

def graph_wind(session):
    weather_data = session.weather_data

    # Maybe fastf1.api can break someday
    weather_data = pd.merge_asof(weather_data, pd.DataFrame(fastf1.api.lap_count(session.api_path)), on="Time", direction="backward")
    weather_data.drop_duplicates(subset=["CurrentLap"], keep="last", inplace=True)
    weather_data = weather_data.groupby('WindDirection', as_index=False).agg({'WindSpeed': 'mean'})

    fig = px.bar_polar(
        weather_data,
        r="WindSpeed",
        theta="WindDirection",
    )

    fig.update_layout(
        title={"text": "Wind Rose", "font": {"size": 30, "family": "Arial"}, "automargin": True, "xanchor": "center", "x": 0.5, "yanchor": "top", "y": 0.9},
        polar=dict(
            radialaxis=dict(
                range=[0, weather_data["WindSpeed"].max() * 1.2],
                title="Wind Speed (km/h)",
                ticklen=8
            ),
            angularaxis=dict(
                tickmode='array',
                tickvals=list(range(0, 360, 45)), # [0, 45, 90, 135, 180, 225, 270, 315]
                ticktext=['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
            ),
        ),
    )

    return fig