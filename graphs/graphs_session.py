import plotly.express as px
import plotly.graph_objects as go

import streamlit as st
import pandas as pd
import numpy as np
import datetime

import fastf1.plotting
import fastf1
import requests
from .colors import get_team_color_safe, get_driver_color_safe, get_compound_mapping_safe, get_driver_line_dash_map, get_driver_pattern_map, get_driver_symbol_map


def _hires_headshot(url):
    if not url or not isinstance(url, str):
        return url
    import re
    url = re.sub(r'w_\d+', 'w_1320', url)
    url = re.sub(r'q_\d+', 'q_auto', url)
    return url


def graph_results(session):
    results = session.results
    results = results.sort_values(by="Position")
    results = results.reset_index(drop=True)

    def fmt_laptime(seconds):
        """Format seconds into m:ss.mmm"""
        if not isinstance(seconds, (int, float)) or seconds != seconds:
            return None
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m}:{s:06.3f}"

    def fmt_racetime(seconds):
        """Format seconds into H:mm:ss.mmm for total race time"""
        if not isinstance(seconds, (int, float)) or seconds != seconds:
            return None
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:06.3f}"
        return f"{m}:{s:06.3f}"

    if session.session_info["Type"] == "Race":
        leader_time = results.iloc[0]["Time"]
        leader_total = leader_time.total_seconds() if hasattr(leader_time, "total_seconds") else None

        def race_display(row):
            if row.name == 0:
                t = leader_total
                return f"{fmt_racetime(t)}  (LEADER)" if t else "LEADER"
            gap = row["Time"]
            if hasattr(gap, "total_seconds"):
                g = gap.total_seconds()
                total = (leader_total + g) if leader_total else None
                time_str = fmt_racetime(total) if total else ""
                return f"{time_str}  (+{g:.3f}s)"
            status = str(row["Status"]).replace("+", "").strip()
            return status

        results["Display"] = results.apply(race_display, axis=1)

    elif session.session_info["Type"] == "Qualifying":
        def best_q_time(row):
            for col in ["Q3", "Q2", "Q1"]:
                v = row.get(col)
                if v is not None and hasattr(v, "total_seconds"):
                    return v.total_seconds()
            return None

        results["_BestTime"] = results.apply(best_q_time, axis=1)
        pole_time = results["_BestTime"].dropna().min()

        def qual_display(row):
            t = row["_BestTime"]
            if t is None or t != t:
                return str(row["Status"]).replace("+", "").strip()
            lap_str = fmt_laptime(t)
            if t == pole_time:
                return f"{lap_str}  (LEADER)"
            gap = t - pole_time
            return f"{lap_str}  (+{gap:.3f}s)"

        results["Display"] = results.apply(qual_display, axis=1)

    # --- Render cards ---
    cols = st.columns(3)
    for i in range(3):
        driver = results.iloc[i]
        with cols[i].container(border=True):
            pos = int(driver["Position"])
            if session.session_info["Type"] == "Race":
                st.markdown(f"**P{pos}** · {driver['FullName']} · {int(driver['Points'])} pts  \n{driver['TeamName']}  \n`{driver['Display']}`")
            else:
                st.markdown(f"**P{pos}** · {driver['FullName']}  \n{driver['TeamName']}  \n`{driver['Display']}`")
            try:
                st.image(_hires_headshot(driver['HeadshotUrl']), use_container_width=True)
            except: pass

    with st.expander("more..."):
        for i in range(3, len(results.index), 4):
            cols = st.columns(4)
            for j in range(4):
                try:
                    driver = results.iloc[i+j]
                    with cols[j].container(border=True):
                        pos = int(driver["Position"])
                        if session.session_info["Type"] == "Race":
                            st.markdown(f"**P{pos}** · {driver['FullName']} · {int(driver['Points'])} pts  \n{driver['TeamName']}  \n`{driver['Display']}`")
                        else:
                            st.markdown(f"**P{pos}** · {driver['FullName']}  \n{driver['TeamName']}  \n`{driver['Display']}`")
                        st.image(_hires_headshot(driver['HeadshotUrl']), use_container_width=True)
                except: continue


def graph_drivers_position(session):
    try:
        # Prepare Core Data
        laps_data = session.laps.copy()
        if laps_data.empty:
            return None
            
        if "DriverNumber" in laps_data.columns:
            laps_data = laps_data.set_index("DriverNumber")
            
        # Subset what we need
        needed = ["Driver", "LapNumber", "Position", "TrackStatus"]
        race_df = laps_data[[c for c in needed if c in laps_data.columns]].copy()
        
        # Grid data (Lap 0)
        res_grid = session.results[["DriverNumber", "GridPosition", "Abbreviation"]].set_index("DriverNumber")
        grid_rows = []
        for d_num, row in res_grid.iterrows():
            if pd.notna(row["GridPosition"]) and row["GridPosition"] > 0:
                grid_rows.append({
                    "Driver": row["Abbreviation"],
                    "LapNumber": 0,
                    "Position": row["GridPosition"],
                    "TrackStatus": "1"
                })
        grid_df = pd.DataFrame(grid_rows)
        
        # Combine
        full_df = pd.concat([race_df, grid_df], sort=False)
        full_df.sort_values(["LapNumber"], inplace=True)
        
        # Ensure legend order is by finishing position
        finish_order = session.results.sort_values("Position")["Abbreviation"].unique().tolist()
        # Filter to drivers actually in the data
        graph_drivers = [d for d in finish_order if d in full_df["Driver"].unique()]
        full_df["Driver"] = pd.Categorical(full_df["Driver"], categories=graph_drivers, ordered=True)
        
        # Sort data to match legend order (Plotly often follows data order)
        full_df = full_df.sort_values(["Driver", "LapNumber"])
        
        # Map colors and dashes (ensure they align with the new order if needed, though dict mapping is safe)
        color_map = {d: get_driver_color_safe(d, session) for d in graph_drivers}
        dash_map = get_driver_line_dash_map(session)

        fig = px.line(
            full_df,
            x = "LapNumber",
            y = "Position",
            color = "Driver",
            color_discrete_map = color_map,
            category_orders = {"Driver": graph_drivers}, # Explicitly set legend order
            line_dash = "Driver",
            line_dash_map = dash_map,
            markers = True,
            title = "Position throughout the Race"
        )

        # Add SC/VSC/Red Flag Overlays
        if "TrackStatus" in full_df.columns:
            status_per_lap = full_df.groupby("LapNumber")["TrackStatus"].first()
            sc_laps = [lap for lap, stat in status_per_lap.items() if '4' in str(stat)]
            rf_laps = [lap for lap, stat in status_per_lap.items() if '5' in str(stat)]
            vsc_laps = [lap for lap, stat in status_per_lap.items() if '6' in str(stat) or '7' in str(stat)]
            
            def add_rects(l_list, color, label):
                if not l_list: return
                start = l_list[0]
                for i in range(1, len(l_list)):
                    if l_list[i] != l_list[i-1] + 1:
                        fig.add_vrect(x0=float(start)-0.5, x1=float(l_list[i-1])+0.5, fillcolor=color, opacity=0.12, layer="below", line_width=0, annotation_text=label)
                        start = l_list[i]
                fig.add_vrect(x0=float(start)-0.5, x1=float(l_list[-1])+0.5, fillcolor=color, opacity=0.12, layer="below", line_width=0, annotation_text=label)

            add_rects(sc_laps, "orange", "SC")
            add_rects(vsc_laps, "yellow", "VSC")
            add_rects(rf_laps, "red", "RED FLAG")

        fig.update_layout(
            title={"font": {"size": 30, "family":"Arial"}, "x": .5},
            width = 1100,
            height = 600,
            xaxis = {"title": "Lap №", "showgrid": False},
            yaxis = {"title": "Position", "autorange": "reversed", "showgrid": False, "tickvals": list(range(1, 21))},
        )

        fig.update_traces(marker=dict(size=6, line=dict(width=1, color="black")), line=dict(width=3))
        
        return fig
    except Exception as e:
        st.error(f"Position Graph Error: {e}")
        return None


def graph_drivers_fastest_laps_time(session):
    fastest_laps = []
    for driver in session.drivers:
        lap = session.laps.pick_drivers([driver]).pick_fastest()
        if lap is not None:
            fastest_laps.append(lap)

    if not fastest_laps:
        return None

    fastest_laps = fastf1.core.Laps(fastest_laps).sort_values(by="LapTime").reset_index(drop=True)

    pole_lap = fastest_laps.pick_fastest()
    fastest_laps['LapTimeDelta'] = fastest_laps['LapTime'] - pole_lap['LapTime']
    fastest_laps['LapTimeDelta'] = fastest_laps['LapTimeDelta'].dt.total_seconds()

    def fmt_time(td):
        total = td.total_seconds()
        m = int(total // 60)
        s = total % 60
        return f"{m}:{s:06.3f}"

    fastest_laps['LapTimeStr'] = fastest_laps['LapTime'].apply(fmt_time)
    fastest_laps['GapStr'] = fastest_laps['LapTimeDelta'].apply(
        lambda d: "LEADER" if d == 0 else f"+{d:.3f}s"
    )
    fastest_laps['Label'] = fastest_laps['LapTimeStr'] + "  (" + fastest_laps['GapStr'] + ")"

    fig = px.bar(
        fastest_laps,
        x="LapTimeDelta",
        y="Driver",
        color="Driver",
        color_discrete_map={d: get_driver_color_safe(d, session) for d in fastest_laps["Driver"]},
        pattern_shape="Driver",
        pattern_shape_map=get_driver_pattern_map(session),
        category_orders={"Driver": fastest_laps["Driver"]},
        hover_data={"LapTimeStr": True, "GapStr": True, "LapTimeDelta": False, "Team": True, "LapNumber": True},
        text="Label",
        orientation="h",
    )

    fig.update_layout(
        title={"text": "Fastest Laps", "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis={"title": "Gap to Leader (s)"},
        yaxis={"title": "Driver", "tickmode": "linear"},
    )

    fig.update_traces(
        marker={"line": {"color": "black", "width": 1}, "pattern_fillmode": "overlay"},
        textfont={"family": "Arial", "size": 12, "color": "#F1F1F3", "shadow": "0 0 4px black, 0 0 8px black, 1px 1px 3px black"},

        textposition="outside",
        cliponaxis=False,
    )

    return fig


def graph_drivers_consistency(session, show_fuel_adj=True): # TODO add safety car periods and yellow flags (Open F1)
    laps = session.laps.pick_quicklaps() # Remove pit lanes -> this causes graph to start later, due to too much inconsistency in the beginning
    transformed_laps = laps.copy()
    transformed_laps["LapTime (s)"] = transformed_laps["LapTime"].dt.total_seconds()

    # --- Fuel compensation ---
    is_race = session.session_info["Type"] == "Race"
    y_col = "LapTime (s)"
    graph_title = "Drivers' Consistency"

    if is_race:
        try:
            event_name = session.event["EventName"]
            race_distance_km = 230 if "Monaco" in event_name else 300
            circuit_length_km = session.event.get("CircuitLength", None)
            if circuit_length_km and circuit_length_km > 0:
                total_laps = round(race_distance_km / circuit_length_km)
            else:
                total_laps = int(session.laps["LapNumber"].max())
        except Exception:
            total_laps = int(session.laps["LapNumber"].max())

        FUEL_START_KG = 70.0
        FUEL_EFFECT_PER_KG = 0.025 

        def fuel_correction(lap_number):
            fuel_kg = max(0.0, FUEL_START_KG * (1 - (lap_number - 1) / total_laps))
            return fuel_kg * FUEL_EFFECT_PER_KG

        transformed_laps["FuelCorrection"] = transformed_laps["LapNumber"].apply(fuel_correction)
        transformed_laps["LapTime Fuel Adj. (s)"] = transformed_laps["LapTime (s)"] - transformed_laps["FuelCorrection"]
        
        if show_fuel_adj:
            y_col = "LapTime Fuel Adj. (s)"
            graph_title = "Drivers' Consistency (Fuel Adjusted)"

    driver_order = (
        transformed_laps[[driver_col for driver_col in ["Driver", y_col] if driver_col in transformed_laps.columns]]
        .groupby("Driver").median()[y_col].sort_values().index
    )

    colors = []
    for driver in driver_order:
        colors.append(get_driver_color_safe(driver, session))

    transformed_laps["Driver"] = pd.Categorical(transformed_laps["Driver"], categories=driver_order, ordered=True)
    transformed_laps = transformed_laps.sort_values(["Driver", "LapNumber"])
    transformed_laps["Compound"] = transformed_laps["Compound"].apply(str.capitalize)

    if transformed_laps.empty:
        return None

    fig = px.line(
        transformed_laps,
        x="LapNumber",
        y=y_col,
        hover_data=["Team", "LapNumber", "Compound", "Stint", "TyreLife"],
        color="Driver",
        color_discrete_sequence=colors,
        line_dash="Driver",
        line_dash_map=get_driver_line_dash_map(session),
        markers=True
    )

    for trace in fig.data:
        trace.legendgroup = trace.name

    fig.update_layout(
        title={"text": graph_title, "font": {"size": 30, "family":"Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis = {"title": "Lap №"},
        yaxis = {"title": f"{y_col}"},
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
        colors.append(get_team_color_safe(team, session))

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
        colors.append(get_driver_color_safe(driver, session))

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
    

def graph_drivers_stints(session):
    # Build driver order from session results (position), fallback to session.drivers
    try:
        results = session.results.sort_values("Position")
        driver_order = list(results["Abbreviation"])
    except Exception:
        driver_order = [session.get_driver(driver)["Abbreviation"] for driver in session.drivers]

    # Reverse so best position is at the top of horizontal bar chart
    driver_order = driver_order[::-1]

    stints = session.laps[["Driver", "Stint", "Compound", "FreshTyre", "LapNumber"]]
    stints = stints.groupby(["Driver", "Stint", "Compound", "FreshTyre"])
    stints = stints.count().reset_index()
    stints = stints.sort_values(["Driver", "Stint"])  # critical: iterate in stint order

    compound_colors = get_compound_mapping_safe(session)
    shown_compounds = set()

    fig = go.Figure()
    for _, row in stints.iterrows():
        compound = row["Compound"]
        color = compound_colors.get(compound, "#888888")
        pattern_shape = "" if row["FreshTyre"] else "/"
        lap_count = int(row["LapNumber"])

        is_white = color in ["#f0f0ec", "#F0F0EC"]
        text_color = "black" if is_white else "#F1F1F3"
        text_shadow = "1px 1px 6px white" if is_white else "1px 1px 6px black"

        show_legend = compound not in shown_compounds
        shown_compounds.add(compound)

        fig.add_trace(go.Bar(
            x=[lap_count],
            y=[row["Driver"]],
            orientation="h",
            name=compound,
            legendgroup=compound,
            showlegend=show_legend,
            marker=dict(
                color=color,
                line=dict(color="gray", width=1),
                pattern=dict(shape=pattern_shape, fillmode="overlay"),
            ),
            text=[str(lap_count)],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(family="Arial", size=16, color=text_color, shadow=text_shadow, weight="bold"),
            hovertemplate=f"Driver: {row['Driver']}<br>Stint: {int(row['Stint'])}<br>Compound: {compound}<br>Laps: {lap_count}<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        title={"text": "Tyre Strategies", "font": {"size": 30, "family": "Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis={"title": "Lap №"},
        yaxis={"title": "Driver", "categoryorder": "array", "categoryarray": driver_order, "tickmode": "linear"},
        showlegend=False,
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
        color_discrete_map=get_compound_mapping_safe(session),
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
        try:
            telemetry = session.laps.pick_drivers([driver]).get_car_data()
            if telemetry.empty: continue
            telemetry["Driver"] = session.get_driver(driver)["Abbreviation"]
            top_speeds.append(telemetry.iloc[telemetry["Speed"].idxmax()])
        except: pass

    top_speeds = pd.DataFrame(top_speeds)
    top_speeds = top_speeds.sort_values(by="Speed", ascending=False).reset_index(drop=True)

    colors = []
    for driver in top_speeds["Driver"]:
        colors.append(get_driver_color_safe(driver, session))

    fig = px.bar(
        top_speeds,
        x="Driver",
        y="Speed",
        color="Driver",
        color_discrete_sequence=colors,
        pattern_shape="Driver",
        pattern_shape_map=get_driver_pattern_map(session),
        hover_data=["Speed"], # TODO add "LapNumber", "Compound", "Stint"
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
    # Scatter plot with mean speed (aero/cornering proxy) vs top speed (engine proxy)
    speeds = []

    for driver in session.drivers:
        try:
            telemetry = session.laps.pick_drivers([driver]).pick_quicklaps().pick_accurate().get_car_data()
            if telemetry.empty: continue
            telemetry["Driver"] = session.get_driver(driver)["Abbreviation"]
            telemetry["Team"] = session.get_driver(driver)["TeamName"]
            telemetry["MeanSpeed"] = telemetry["Speed"].mean()
            telemetry.rename(columns={"Speed": "TopSpeed"}, inplace=True)
            speeds.append(telemetry.iloc[telemetry["TopSpeed"].idxmax()])
        except: pass

    speeds = pd.DataFrame(speeds)

    colors = []
    for driver in speeds["Driver"]:
        colors.append(get_driver_color_safe(driver, session))

    mid_x = speeds["MeanSpeed"].median()
    mid_y = speeds["TopSpeed"].median()

    x_min = speeds["MeanSpeed"].min() - 5
    x_max = speeds["MeanSpeed"].max() + 5
    y_min = speeds["TopSpeed"].min() - 5
    y_max = speeds["TopSpeed"].max() + 5

    # Quadrant metadata: (x0, y0, x1, y1, fill colour, label, label anchor)
    quadrants = [
        # upper-left: high engine, low cornering → Powerhouse
        (x_min, mid_y, mid_x, y_max, "rgba(255,100,100,0.08)", "⚡ Powerhouse<br><sub>High top speed,<br>less aero</sub>", mid_x - 1, (y_max + mid_y) / 2, "right"),
        # upper-right: high engine + high cornering → Complete Car
        (mid_x, mid_y, x_max, y_max, "rgba(100,220,150,0.10)", "🏆 Complete Car<br><sub>High top speed<br>+ cornering</sub>", mid_x + 1, (y_max + mid_y) / 2, "left"),
        # lower-left: low both → Underpowered
        (x_min, y_min, mid_x, mid_y, "rgba(180,180,180,0.10)", "💤 Underpowered<br><sub>Low speed<br>everywhere</sub>", mid_x - 1, (y_min + mid_y) / 2, "right"),
        # lower-right: high cornering, lower top → Downforce specialist
        (mid_x, y_min, x_max, mid_y, "rgba(100,150,255,0.10)", "🔵 Downforce<br><sub>Great cornering,<br>lower top speed</sub>", mid_x + 1, (y_min + mid_y) / 2, "left"),
    ]

    fig = px.scatter(
        speeds,
        x="MeanSpeed",
        y="TopSpeed",
        color="Driver",
        color_discrete_sequence=colors,
        symbol="Driver",
        symbol_map=get_driver_symbol_map(session),
        hover_data=["Driver", "Team", "MeanSpeed", "TopSpeed"],
        text="Driver",
    )

    # Draw quadrant backgrounds
    for x0, y0, x1, y1, color, label, lx, ly, anchor in quadrants:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      fillcolor=color, line_width=0, layer="below")
        fig.add_annotation(x=lx, y=ly, text=label, showarrow=False,
                           xanchor=anchor, yanchor="middle",
                           font=dict(size=11, color="gray"),
                           align="center" if anchor == "left" else "right")

    # Legend for axes in top-right
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.98, y=0.98,
        text="<b>Axis Legend</b><br>Vertical: Engine Power<br>Horizontal: Cornering / Aero",
        showarrow=False,
        bgcolor="rgba(255, 255, 255, 0.7)",
        bordercolor="gray",
        borderwidth=1,
        borderpad=4,
        xanchor="right", yanchor="top",
        font=dict(size=12, color="black")
    )

    # Crosshair dividers
    fig.add_hline(y=mid_y, line_dash="dot", line_color="gray", line_width=1, opacity=0.5)
    fig.add_vline(x=mid_x, line_dash="dot", line_color="gray", line_width=1, opacity=0.5)

    fig.update_layout(
        title={"text": "Car Style", "font": {"size": 30, "family": "Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis={"title": "Mean Speed — Aero / Cornering (km/h)", "range": [x_min, x_max]},
        yaxis={"title": "Top Speed — Engine Power (km/h)", "range": [y_min, y_max]},
        showlegend=False,
    )

    fig.update_traces(
        marker=dict(size=12, line=dict(color="black", width=1.5)),
        textposition="top center",
        textfont=dict(size=10),
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
    
    if telemetries == []:
        return None, None, None
        
    telemetries = pd.concat(telemetries)

    # Remove telemetry after the first curve
    telemetries.sort_values("Distance", inplace=True)
    telemetries.reset_index(drop=True, inplace=True)
    
    # Safety check for empty slice or if no points are past the first corner
    corners = session.get_circuit_info().corners
    if not corners.empty:
        past_corner = telemetries[telemetries['Distance'] > corners.iloc[0]["Distance"]]
        if not past_corner.empty:
            first_curve_index = past_corner.index[0]
            telemetries = telemetries.iloc[:first_curve_index]

    # Keep legend order
    driver_order = [session.get_driver(driver)["Abbreviation"] for driver in session.drivers]
    telemetries = telemetries.set_index("Driver")
    
    # Use intersection to avoid KeyError for DNS drivers
    present_drivers = telemetries.index.intersection(driver_order).unique()
    telemetries = telemetries.loc[present_drivers]
    telemetries.reset_index(inplace=True)

    telemetries["Time"] = telemetries["Time"].dt.total_seconds()

    colors = []
    for driver in telemetries["Driver"].unique():
        colors.append(get_driver_color_safe(driver, session))

    # GRAPHS

    fig1 = px.line(
        telemetries,
        x="Time",
        y="Throttle",
        color="Driver",
        color_discrete_sequence=colors,
        line_dash="Driver",
        line_dash_map=get_driver_line_dash_map(session),
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
        line_dash="Driver",
        line_dash_map=get_driver_line_dash_map(session),
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
        # Use np.nan instead of 0 to avoid "infinite" or misleading calculations
        t_100_data = driver_data[driver_data["Speed"] > 100]
        t_200_data = driver_data[driver_data["Speed"] > 200]
        
        time_100 = t_100_data.iloc[0]["Time"] if not t_100_data.empty else np.nan
        time_200 = t_200_data.iloc[0]["Time"] if not t_200_data.empty else np.nan
        
        delta_100_200 = (time_200 - time_100) if (not pd.isna(time_100) and not pd.isna(time_200)) else np.nan
        
        # Append the results to the DataFrame
        speed_times = pd.concat([speed_times, pd.DataFrame([[driver, time_100, delta_100_200, time_200]], columns=speed_times.columns)], ignore_index=True)
            
    speed_times = speed_times.round(2)
    speed_times.sort_values("0-200", inplace=True)

    return fig1, fig2, speed_times


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
        team_colors.append(get_team_color_safe(team, session))

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





def graph_drivers_curves(session):
    # Retrieve track info and determine rotation
    circuit_info = session.get_circuit_info()
    track_angle = circuit_info.rotation / 180 * np.pi

    def rotate(xy, angle):
        rot_mat = np.array([[np.cos(angle), np.sin(angle)],
                            [-np.sin(angle), np.cos(angle)]])
        return np.matmul(xy, rot_mat)

    # Get the fastest lap overall to draw the base track path
    try:
        fastest_lap = session.laps.pick_fastest()
        pos = fastest_lap.get_pos_data()
        track = pos.loc[:, ('X', 'Y')].to_numpy()
        rotated_track = rotate(track, angle=track_angle)
    except Exception:
        return go.Figure()

    # Determine axis boundaries based on the track
    x_min, x_max = rotated_track[:, 0].min(), rotated_track[:, 0].max()
    y_min, y_max = rotated_track[:, 1].min(), rotated_track[:, 1].max()
    # Add some padding
    x_pad = (x_max - x_min) * 0.1
    y_pad = (y_max - y_min) * 0.1

    # Extract fastest lap telemetry for all drivers and interpolate to common time frames (every 0.5s)
    dfs = []
    max_time = 0
    driver_data = {}

    for driver in session.drivers:
        driver_abbr = session.get_driver(driver)["Abbreviation"]
        try:
            lap = session.laps.pick_drivers([driver]).pick_fastest()
            if lap is not None and pd.notnull(lap["LapTime"]):
                tel = lap.get_telemetry()
                if tel.empty: continue
                
                if "Distance" not in tel.columns:
                    tel = tel.add_distance()

                # Normalize time to start from 0
                time_sec = tel["Time"].dt.total_seconds()
                time_sec = time_sec - time_sec.iloc[0]
                
                # Convert coords to numpy and rotate
                coords = tel[["X", "Y"]].to_numpy()
                rot_coords = rotate(coords, angle=track_angle)
                
                df_driver = pd.DataFrame({
                    "Time_sec": time_sec,
                    "X": rot_coords[:, 0],
                    "Y": rot_coords[:, 1],
                    "Distance": tel["Distance"].to_numpy(),
                    "Speed": tel["Speed"].to_numpy(),
                    "Driver": driver_abbr,
                    "Team": session.get_driver(driver)["TeamName"]
                })
                df_driver["LapTime_sec"] = lap["LapTime"].total_seconds()
                driver_data[driver_abbr] = df_driver
                max_time = max(max_time, time_sec.max())
        except Exception:
            pass

    if not driver_data:
        return go.Figure()

    # Common time grid: from 0s to max lap time in 0.5s steps
    time_grid = np.arange(0, max_time + 0.5, 0.5)
    fastest_lap_time = min(df["LapTime_sec"].iloc[0] for df in driver_data.values())

    all_frames = []
    for driver, df_drv in driver_data.items():
        # Interpolate X, Y, Distance, and Speed onto the common time grid
        interp_x = np.interp(time_grid, df_drv["Time_sec"], df_drv["X"])
        interp_y = np.interp(time_grid, df_drv["Time_sec"], df_drv["Y"])
        interp_dist = np.interp(time_grid, df_drv["Time_sec"], df_drv["Distance"])
        interp_speed = np.interp(time_grid, df_drv["Time_sec"], df_drv["Speed"])
        
        final_gap = df_drv["LapTime_sec"].iloc[0] - fastest_lap_time
        final_gap_str = f"+{final_gap:.3f}s" if final_gap > 0.001 else "LEADER"

        df_interp = pd.DataFrame({
            "Time": time_grid,
            "X": interp_x,
            "Y": interp_y,
            "Distance": interp_dist,
            "Speed_mps": interp_speed / 3.6, # km/h to m/s
            "Driver": driver,
            "Team": df_drv["Team"].iloc[0],
            "IsFinished": time_grid >= (df_drv["Time_sec"].max() - 0.01),
            "FinalGapStr": final_gap_str
        })
        all_frames.append(df_interp)

    df_anim = pd.concat(all_frames, ignore_index=True)

    # Calculate gap to leader at each time frame based on distance
    def calc_gap(group):
        leader_dist = group["Distance"].max()
        # Time gap = Distance Diff / Current Speed (avoid divide by zero)
        group["DistDiff"] = leader_dist - group["Distance"]
        group["Gap_sec"] = group["DistDiff"] / group["Speed_mps"].replace(0, 0.1)
        
        # Apply formatting
        def format_gap(row):
            if row["IsFinished"]: return row["FinalGapStr"]
            return f"+{row['Gap_sec']:.2f}s" if row['Gap_sec'] > 0.01 else "LEADER"
            
        group["GapStr"] = group.apply(format_gap, axis=1)
        return group

    df_anim = df_anim.groupby("Time", group_keys=False).apply(calc_gap)

    # Format time label for the animation slider
    df_anim["TimeLabel"] = df_anim["Time"].apply(lambda t: f"{t:05.1f}s")
    
    # Create the text label that will show next to the dot (Driver + Gap)
    def make_label(row):
        if row["GapStr"] == "LEADER":
            return row["Driver"]
        return f"{row['Driver']} {row['GapStr']}"
        
    df_anim["Label"] = df_anim.apply(make_label, axis=1)
    df_anim = df_anim.sort_values(["Time", "Driver"])

    colors = [get_driver_color_safe(d, session) for d in df_anim["Driver"].unique()]

    # Create the animated scatter
    fig = px.scatter(
        df_anim,
        x="X", y="Y",
        animation_frame="TimeLabel",
        animation_group="Driver",
        color="Driver",
        color_discrete_sequence=colors,
        text="Label",
        hover_data={"Driver": True, "Team": True, "GapStr": True, "TimeLabel": False, "Time": False, "X": False, "Y": False, "Label": False},
        labels={"GapStr": "Gap"}
    )

    # Increase animated marker sizes and font overlays for drivers
    fig.update_traces(
        marker=dict(size=14, line=dict(color="black", width=1.5)),
        textfont=dict(size=12, color="black", shadow="1px 1px 3px white"),
        selector=dict(mode="markers+text")
    )

    # Stagger text positions to prevent overlap when cars are bunched together
    pos_cycle = [
        "top left", "top center", "top right", 
        "middle right", "bottom right", "bottom center", 
        "bottom left", "middle left"
    ]
    
    # Apply to base animated traces
    for i, trace in enumerate(fig.data):
        if getattr(trace, "name", None): 
            trace.textposition = pos_cycle[i % len(pos_cycle)]
            
    # Apply to every animation frame
    if fig.frames:
        for frame in fig.frames:
            for i, trace in enumerate(frame.data):
                trace.textposition = pos_cycle[i % len(pos_cycle)]

    # Add static background track path
    fig.add_trace(go.Scatter(
        x=rotated_track[:, 0],
        y=rotated_track[:, 1],
        mode="lines",
        line=dict(color="gray", width=4),
        opacity=0.3,
        hoverinfo="skip",
        showlegend=False,
    ))

    # Add corners (static)
    offset_vector = [700, 0]  # Increased arbitrary offset slightly for clarity on full map

    corner_x = []
    corner_y = []
    corner_texts = []
    line_shapes = []

    for _, corner in circuit_info.corners.iterrows():
        txt = f"{corner['Number']}{corner['Letter']}"
        offset_angle = corner['Angle'] / 180 * np.pi
        offset_x, offset_y = rotate(offset_vector, angle=offset_angle)

        # Apply offset
        text_raw_x = corner['X'] + offset_x
        text_raw_y = corner['Y'] + offset_y

        # Rotate to match track orientation
        text_x, text_y = rotate([text_raw_x, text_raw_y], angle=track_angle)
        track_x, track_y = rotate([corner['X'], corner['Y']], angle=track_angle)

        corner_x.append(text_x)
        corner_y.append(text_y)
        corner_texts.append(txt)

        # Line connecting track to text circle
        line_shapes.append(
            dict(type="line", x0=track_x, y0=track_y, x1=text_x, y1=text_y, line=dict(color="gray", width=1))
        )

    # Add corner text circles
    fig.add_trace(go.Scatter(
        x=corner_x, y=corner_y,
        mode="markers+text",
        marker=dict(color="#6C3DE8", size=24, line=dict(color="white", width=1)),
        text=corner_texts,
        textfont=dict(color="white", size=10, weight="bold"),
        hoverinfo="skip",
        showlegend=False
    ))

    # Layout settings
    fig.update_layout(
        title={"text": "Fastest Lap Animation", "font": {"size": 30, "family": "Arial"}, "automargin": True, "xanchor": "center", "x": .5, "yanchor": "top", "y": .9},
        xaxis=dict(visible=False, range=[x_min - x_pad, x_max + x_pad]),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1, range=[y_min - y_pad, y_max + y_pad]),
        shapes=line_shapes,
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            y=0, x=0, xanchor="right", yanchor="top", pad=dict(t=30, r=10),
            buttons=[
                dict(label="Play", method="animate", args=[None, dict(frame=dict(duration=100, redraw=True), transition=dict(duration=50), fromcurrent=True)]),
                dict(label="Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])
            ]
        )],
        sliders=[dict(
            y=0, x=0, xanchor="left", yanchor="top",
            currentvalue=dict(font=dict(size=14), prefix="Time: ", visible=True, xanchor="right"),
            transition=dict(duration=50)
        )]
    )

    return fig


def graph_engine_clipping(session):
    df_list = []
    lap_times = {}
    
    for driver in session.drivers:
        driver_abbr = session.get_driver(driver)["Abbreviation"]
        try:
            lap = session.laps.pick_drivers([driver]).pick_accurate().pick_fastest()
            if lap is None or pd.isnull(lap["LapTime"]): continue
            
            tel = lap.get_telemetry()
            if tel.empty: continue
            
            if "Distance" not in tel.columns:
                tel = tel.add_distance()
                
            tel["Driver"] = driver_abbr
            tel["LapNumber"] = lap["LapNumber"]
            lap_times[driver_abbr] = lap["LapTime"].total_seconds()
            
            # Calculate acceleration (using numpy gradient of speed relative to time)
            time_sec = tel["Time"].dt.total_seconds().to_numpy()
            # Keep in km/h so acceleration is calculated in (km/h)/s
            speed_kmh = tel["Speed"].to_numpy()
            
            # To avoid dividing by zero if time differences are exactly zero, add a tiny epsilon
            dt = np.gradient(time_sec)
            dt[dt == 0] = 1e-6
            accel = np.gradient(speed_kmh) / dt
            
            tel["Acceleration"] = accel
            
            # Define "Super Clipping": 
            # 1. Near 100% Throttle (>= 97%)
            # 2. At high speed (e.g. > 260 km/h where drag and ERS cut-off matter most)
            # 3. Not accelerating (Acceleration <= 1.0 km/h/s)
            tel["IsClipping"] = (tel["Throttle"] >= 97) & (tel["Speed"] >= 260) & (tel["Acceleration"] <= 1.0)
            
            df_list.append(tel)
        except Exception:
            pass
            
    if not df_list:
        return go.Figure()
        
    df = pd.concat(df_list, ignore_index=True)
    
    from plotly.subplots import make_subplots
    
    # Create subplots: top for Speed, bottom for Acceleration impact
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.4],
        subplot_titles=("Speed Trace", "Acceleration Loss (Clipping Impact)")
    )
    
    # Sort drivers by their fastest lap time for the legend
    sorted_drivers = sorted(df["Driver"].unique(), key=lambda d: lap_times.get(d, 9999))
    colors = {d: get_driver_color_safe(d, session) for d in sorted_drivers}
    dash_map = get_driver_line_dash_map(session)
    
    # Pre-calculate hover templates
    hover_speed = "<b>%{customdata[0]}</b> (Lap %{customdata[2]})<br>Distance: %{x:.0f} m<br>Speed: %{y:.1f} km/h<br>Throttle: %{customdata[1]:.0f}%<extra></extra>"
    hover_accel = "<b>%{customdata[0]}</b> (Lap %{customdata[2]})<br>Distance: %{x:.0f} m<br>Accel: %{y:.2f} km/h/s<extra></extra>"
    
    for driver in sorted_drivers:
        driver_df = df[df["Driver"] == driver]
        color = colors[driver]
        dash = dash_map.get(driver, "solid")
        
        # Top Plot: Speed
        fig.add_trace(
            go.Scatter(
                x=driver_df["Distance"], y=driver_df["Speed"],
                mode="lines",
                name=driver,
                line=dict(color=color, dash=dash, width=2),
                customdata=np.stack((driver_df["Driver"], driver_df["Throttle"], driver_df["LapNumber"]), axis=-1),
                hovertemplate=hover_speed,
                legendgroup=driver
            ),
            row=1, col=1
        )
        
        # Bottom Plot: Acceleration Trace
        fig.add_trace(
            go.Scatter(
                x=driver_df["Distance"], y=driver_df["Acceleration"],
                mode="lines",
                name=f"{driver} Accel",
                line=dict(color=color, dash=dash, width=1, shape='spline'),
                opacity=0.4,
                customdata=np.stack((driver_df["Driver"], driver_df["Throttle"], driver_df["LapNumber"]), axis=-1),
                hovertemplate=hover_accel,
                legendgroup=driver,
                showlegend=False
            ),
            row=2, col=1
        )

        # Bottom Plot: Highlight exactly when and how much they are clipping
        # To make it obvious, we draw a filled area covering the clipping zones
        clip_df = driver_df[driver_df["IsClipping"]].copy()
        if not clip_df.empty:
            # We want to draw bars hanging down from a "healthy" acceleration baseline
            # But drawing raw bars for high density telemetry is messy. 
            # We will use Scatter with fill="tozeroy" for exact clipping zones
            
            # Find continuous blocks of clipping
            clip_df["block"] = (clip_df.index.to_series().diff() != 1).cumsum()
            
            for block_id, block in clip_df.groupby("block"):
                # Bottom plot: Fill to zero
                x_vals = [block["Distance"].iloc[0]] + block["Distance"].tolist() + [block["Distance"].iloc[-1]]
                y_vals = [0] + block["Acceleration"].tolist() + [0]
                
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode="lines",
                        fill="tozeroy",
                        fillcolor=color,
                        opacity=0.8,
                        line=dict(color=color, width=0),
                        name=f"{driver} Clip Zone",
                        hoverinfo="skip",
                        legendgroup=driver,
                        showlegend=False
                    ),
                    row=2, col=1
                )
                
                # # Top plot: Highlight the speed trace with red dots to show exactly WHERE the clipping is
                # fig.add_trace(
                #     go.Scatter(
                #         x=block["Distance"],
                #         y=block["Speed"],
                #         mode="markers",
                #         marker=dict(color="red", size=6, symbol="x"),
                #         hoverinfo="skip",
                #         legendgroup=driver,
                #         showlegend=False
                #     ),
                #     row=1, col=1
                # )

    # Add curves distances (vertical lines marking the corners)
    for curve in session.get_circuit_info().corners.iterrows():
        curve = curve[1]
        fig.add_vline(x=curve["Distance"], line_dash="dot", line_color="gray", annotation_text=curve["Number"], annotation_position="bottom right", row="all", col=1)

    # To make the filled blocks pop, we set opacity to 0.7 
    # and give them a dashed outline
    fig.update_layout(
        title={"text": "Engine 'Super Clipping' Impact", "x": 0.5, "xanchor": "center"},
        hovermode="x unified",
        height=650,
        margin=dict(r=10, t=60, b=10, l=10)
    )
    
    # Configure axes
    fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
    
    # Center the bottom Y axis around zero to clearly see negative acceleration (loss of speed)
    # Give it a thick grey zero-line to act as the visual "floor"
    fig.update_yaxes(
        title_text="Accel (km/h/s)", 
        row=2, col=1, 
        zeroline=True, 
        zerolinewidth=2, 
        zerolinecolor="rgba(200,200,200,0.5)",
        gridcolor="rgba(128,128,128,0.1)"
    )
    
    fig.update_xaxes(title_text="Track Distance (m)", row=2, col=1)

    return fig


def graph_engine_clipping_stats(session):
    stats_data = []

    # Map team to engine constructor 2026
    def get_engine_manufacturer(team):
        t = team.lower()
        if any(x in t for x in ['cadillac', 'haas', 'ferrari']): return "Ferrari"
        if any(x in t for x in ['williams', 'alpine', 'mercedes', 'mclaren']): return "Mercedes"
        if any(x in t for x in ['red bull', 'racing bulls', 'rb']): return "Ford"
        if 'audi' in t: return "Audi"
        if 'aston martin' in t: return "Honda"
        return "Other"

    # Define track segments (straights) based on corners
    try:
        circuit_info = session.get_circuit_info()
        corners = circuit_info.corners
        
        # Get track length from the fastest lap telemetry
        fastest_lap = session.laps.pick_fastest()
        if fastest_lap is not None:
            track_length = fastest_lap.get_telemetry().add_distance()["Distance"].max()
        else:
            track_length = 6000 # fallback
            
        segments = []
        if not corners.empty:
            corner_dists = sorted(corners["Distance"].tolist())
            
            # Start to first corner
            if corner_dists[0] > 100:
                segments.append((0, corner_dists[0], f"Start -> T{corners.iloc[0]['Number']}"))
                
            for i in range(len(corners) - 1):
                start = corners.iloc[i]["Distance"]
                end = corners.iloc[i+1]["Distance"]
                # Straights between corners
                if end - start > 100:
                    segments.append((start, end, f"T{corners.iloc[i]['Number']} -> T{corners.iloc[i+1]['Number']}"))
            
            # Final corner to finish
            if track_length - corner_dists[-1] > 100:
                segments.append((corner_dists[-1], track_length, f"T{corners.iloc[-1]['Number']} -> Finish"))
        else:
            segments.append((0, track_length, "Full Lap"))

    except Exception:
        segments = [(0, 10000, "Full Track")]

    for driver in session.drivers:
        driver_info = session.get_driver(driver)
        driver_abbr = driver_info["Abbreviation"]
        team_name = driver_info["TeamName"]
        engine_name = get_engine_manufacturer(team_name)

        try:
            lap = session.laps.pick_drivers([driver]).pick_accurate().pick_fastest()
            if lap is None or pd.isnull(lap["LapTime"]): continue
            
            tel = lap.get_telemetry().add_distance()
            if tel.empty: continue
            
            # Reprocess acceleration
            time_sec = tel["Time"].dt.total_seconds().to_numpy()
            speed_kmh = tel["Speed"].to_numpy()
            dt = np.gradient(time_sec)
            dt[dt == 0] = 1e-6
            accel = np.gradient(speed_kmh) / dt
            tel["Acceleration"] = accel
            
            # Detect clipping
            tel["IsClipping"] = (tel["Throttle"] >= 97) & (tel["Speed"] >= 260) & (tel["Acceleration"] <= 1.0)
            
            # Analyze each segment
            for start, end, label in segments:
                seg_tel = tel[(tel["Distance"] >= start) & (tel["Distance"] <= end)]
                if seg_tel.empty: continue
                
                clipping_seg = seg_tel[seg_tel["IsClipping"]]
                if not clipping_seg.empty:
                    # Duration in seconds
                    duration = clipping_seg["Time"].iloc[-1].total_seconds() - clipping_seg["Time"].iloc[0].total_seconds()
                    
                    # Speed Lost calculation: Peak speed in segment -> Speed when Brake == True
                    peak_idx = clipping_seg["Speed"].idxmax()
                    v_max = tel.loc[peak_idx, "Speed"]
                    
                    # Find first braking after peak
                    after_peak = tel.loc[peak_idx:seg_tel.index[-1]]
                    brake_tel = after_peak[after_peak["Brake"] == True]
                    
                    if not brake_tel.empty:
                        v_brake = brake_tel["Speed"].iloc[0]
                        speed_loss_kmh = v_max - v_brake
                    else:
                        # Fallback to end of segment speed if no brake recorded in this segment
                        speed_loss_kmh = v_max - seg_tel["Speed"].iloc[-1]
                    
                    max_deccl = clipping_seg["Acceleration"].min()
                    
                    stats_data.append({
                        "Driver": driver_abbr,
                        "Engine": engine_name,
                        "Straight": label,
                        "Duration (s)": round(duration, 3),
                        "Speed Lost (km/h)": round(max(0, speed_loss_kmh), 1),
                        "Severity (km/h/s)": round(abs(min(0, max_deccl)), 2),
                        "Peak Speed": round(v_max, 1)
                    })
        except Exception:
            continue

    if not stats_data:
        return go.Figure()

    df_stats = pd.DataFrame(stats_data)
    df_stats = df_stats.sort_values("Duration (s)", ascending=False)
    return df_stats


def graph_full_throttle_pct(session):
    data = []
    
    for driver in session.drivers:
        driver_abbr = session.get_driver(driver)["Abbreviation"]
        team = session.get_driver(driver)["TeamName"]
        try:
            lap = session.laps.pick_drivers([driver]).pick_accurate().pick_fastest()
            if lap is None or pd.isnull(lap["LapTime"]): continue
            
            tel = lap.get_telemetry()
            if tel.empty: continue
            
            # Count percentage of telemetry samples where Throttle is at 100%
            full_throttle_samples = (tel["Throttle"] >= 99).sum()
            total_samples = len(tel)
            
            pct = (full_throttle_samples / total_samples) * 100
            data.append({"Driver": driver_abbr, "Team": team, "Full Throttle %": pct})
        except Exception:
            pass
            
    if not data:
        return go.Figure()
        
    df = pd.DataFrame(data).sort_values(by="Full Throttle %", ascending=True)
    
    fig = px.bar(
        df, x="Full Throttle %", y="Driver", color="Driver",
        color_discrete_map={d: get_driver_color_safe(d, session) for d in df["Driver"].unique()},
        pattern_shape="Driver",
        pattern_shape_map=get_driver_pattern_map(session),
        orientation="h",
        text=df["Full Throttle %"].apply(lambda x: f"{x:.1f}%"),
        title="Lap Time Spent at Full Throttle (%)",
        labels={"Full Throttle %": "Full Throttle Percentage"}
    )
    
    fig.update_layout(showlegend=False)
    fig.update_traces(textposition="outside")
    return fig


def graph_weather(session):
    weather_data = session.weather_data

    # Map Time to Lap number using session.laps (avoiding deprecated fastf1.api)
    if not session.laps.empty:
        # Use first driver as reference for lap timing
        ref_driver = session.drivers[0]
        ref_laps = session.laps.pick_drivers([ref_driver])[['Time', 'LapNumber']].copy()
        ref_laps = ref_laps.rename(columns={'LapNumber': 'CurrentLap'}).sort_values('Time')
        
        # Merge weather data with lap timing
        weather_data = pd.merge_asof(
            weather_data.sort_values('Time'), 
            ref_laps, 
            on='Time', 
            direction='backward'
        )
        weather_data.drop_duplicates(subset=["CurrentLap"], keep="last", inplace=True)
    else:
        weather_data["CurrentLap"] = 0

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

    # Map Time to Lap number using session.laps (avoiding deprecated fastf1.api)
    if not session.laps.empty:
        # Use first driver as reference for lap timing
        ref_driver = session.drivers[0]
        ref_laps = session.laps.pick_drivers([ref_driver])[['Time', 'LapNumber']].copy()
        ref_laps = ref_laps.rename(columns={'LapNumber': 'CurrentLap'}).sort_values('Time')
        
        weather_data = pd.merge_asof(
            weather_data.sort_values('Time'), 
            ref_laps, 
            on='Time', 
            direction='backward'
        )
        weather_data.drop_duplicates(subset=["CurrentLap"], keep="last", inplace=True)
    else:
        weather_data["CurrentLap"] = 0
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