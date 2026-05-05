import streamlit as st
from home import nav_bar, credits

import fastf1
from fastf1.ergast import Ergast
from graphs.colors import TEAM_COLORS

import plotly.express as px
import plotly.graph_objects as go
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
    return (sprint_events * POINTS_FOR_SPRINT) + (conventional_events * POINTS_FOR_CONVENTIONAL)


_TEAM_SLUG = {
    "Red Bull":      "redbullracing",
    "Ferrari":       "ferrari",
    "Mercedes":      "mercedes",
    "McLaren":       "mclaren",
    "Aston Martin":  "astonmartin",
    "Alpine":        "alpine",
    "Williams":      "williams",
    "Haas":          "haas",
    "RB":            "racingbulls",
    "Audi":          "audi",
    "Cadillac":      "cadillac",
}


def _team_slug(team_name: str) -> str:
    for key, slug in _TEAM_SLUG.items():
        if key.lower() in team_name.lower():
            return slug
    return team_name.lower().replace(" ", "")


def _driver_img_url(driver, year: int, team: str = "") -> str:
    fn, ln = driver["givenName"], driver["familyName"]
    drv_slug = f"{fn[:3].lower()}{ln[:3].lower()}01"
    team_s = _team_slug(team) if team else "unknown"
    return (
        f"https://media.formula1.com/image/upload/c_fill,w_720/q_auto"
        f"/common/f1/{year}/{team_s}/{drv_slug}/{year}{team_s}{drv_slug}right.webp"
    )


def _team_color(team_name):
    for key, color in TEAM_COLORS.items():
        if key.lower() in team_name.lower():
            return color
    return "#888888"


def load_standings(standings, year, round_num):
    MAX_POINTS = calculate_max_points(year, round_num)
    LEADER_POINTS = int(standings.iloc[0]["points"])

    def render_card(col, driver, MAX_POINTS, LEADER_POINTS):
        pts = int(driver["points"])
        gap = pts - LEADER_POINTS
        can_win = pts + MAX_POINTS >= LEADER_POINTS
        team = driver["constructorNames"][0] if driver["constructorNames"] else ""
        color = _team_color(team)

        with col.container(border=True):
            st.markdown(
                f"<div style='border-left:4px solid {color}; padding-left:8px;'>"
                f"<span style='font-size:1.3rem; font-weight:700;'>P{int(driver['position'])}</span> "
                f"<span style='font-size:1.1rem;'>{driver['givenName']} {driver['familyName']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            # gap is always ≤ 0; "normal" colors: negative = red (deficit), zero = no arrow
            c1.metric("Points", pts, delta=f"{gap}" if gap != 0 else None, delta_color="normal")
            c2.metric("Team", team, label_visibility="collapsed")
            st.caption(f"**{team}** · {'✅ Can win' if can_win else '❌ Out of title'}")
            st.markdown(f"[![{driver['driverCode']}]({_driver_img_url(driver, year, team)})]({driver['driverUrl']})")

    # Top 3 podium
    cols = st.columns(3, gap="medium")
    for i in range(min(3, len(standings))):
        render_card(cols[i], standings.iloc[i], MAX_POINTS, LEADER_POINTS)

    # Rest of field in rows of 4
    for i in range(3, len(standings.index), 4):
        cols = st.columns(4, gap="small")
        for j in range(4):
            try:
                render_card(cols[j], standings.iloc[i + j], MAX_POINTS, LEADER_POINTS)
            except Exception:
                continue


@st.cache_data(persist=True)
def load_points_data(year, round_num):
    ergast = Ergast()
    races = ergast.get_race_schedule(year)
    results = []
    for rnd, race in races["raceName"].items():
        actual_round = rnd + 1
        if actual_round > round_num:
            break
        try:
            temp = ergast.get_race_results(season=year, round=actual_round).content[0]
            sprint = ergast.get_sprint_results(season=year, round=actual_round)
            if sprint.content and sprint.description["round"][0] == actual_round:
                temp = pd.merge(temp, sprint.content[0], on="driverCode", how="left")
                temp["points"] = temp["points_x"] + temp["points_y"]
                temp.drop(columns=["points_x", "points_y"], inplace=True)
            temp["round"] = actual_round
            temp["race"] = race.removesuffix(" Grand Prix")
            temp = temp[["round", "race", "driverCode", "points"]]
            results.append(temp)
        except Exception:
            continue
    if not results:
        return pd.DataFrame()
    results = pd.concat(results)
    races_list = results["race"].drop_duplicates()
    pivot = results.pivot(index="driverCode", columns="round", values="points")
    pivot["total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("total", ascending=False)
    pivot.drop(columns="total", inplace=True)
    pivot.columns = races_list
    return pivot


def load_graphs(year, round_num):
    with st.spinner("Loading points data..."):
        try:
            results = load_points_data(year, round_num)
        except Exception as e:
            st.error(f"Could not load points data: {e}")
            return

    if results is None or results.empty:
        st.info("No points data available.")
        return

    # ── Total points bar chart ────────────────────────────────────────────
    totals = results.sum(axis=1).reset_index()
    totals.columns = ["Driver", "Total"]
    totals = totals.sort_values("Total", ascending=False)

    fig_bar = go.Figure(go.Bar(
        x=totals["Driver"], y=totals["Total"],
        text=totals["Total"], textposition="outside",
        marker_color="#6C3DE8",
    ))
    fig_bar.update_layout(
        title=dict(text=f"{year} Total Points after Round {round_num}", font_size=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=50, b=0),
        xaxis_title="", yaxis_title="Points",
        yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Per-race heatmap ──────────────────────────────────────────────────
    fig = px.imshow(
        results,
        text_auto=True,
        aspect="auto",
        color_continuous_scale=[
            [0,    "rgb(240,235,252)"],
            [0.25, "rgb(180,148,240)"],
            [0.5,  "rgb(108,61,232)"],
            [0.75, "rgb(70,20,180)"],
            [1,    "rgb(30,0,100)"],
        ],
        labels={"x": "Race", "y": "Driver", "color": "Points"},
        title=f"{year} Points per Race",
    )
    fig.update_xaxes(title_text="", side="top", showgrid=False, showline=False)
    fig.update_yaxes(title_text="", tickmode="linear", showgrid=True, gridwidth=1,
                     gridcolor="#eee", showline=False, tickson="boundaries")
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False,
        margin=dict(l=0, r=0, b=0, t=60), title_font_size=20,
    )
    st.plotly_chart(fig, use_container_width=True)


def main():
    ergast = Ergast()
    nav_bar()

    with st.sidebar:
        year = st.selectbox("Year", range(datetime.date.today().year, 2018 - 1, -1))
        data = fastf1.events.get_event_schedule(year).query("EventFormat != 'testing'")
        data.set_index("EventName", inplace=True)
        data = data[data["Session5DateUtc"] < (pd.Timestamp.utcnow() - pd.Timedelta("4h")).to_datetime64()]
        location = st.selectbox("Event", data.index[::-1])

        with st.spinner("Loading..."):
            try:
                standings = ergast.get_driver_standings(
                    season=year, round=data.loc[location]["RoundNumber"]
                ).content[0]
            except Exception:
                st.error("Failed to load standings.")
                return
        st.success("Loaded!")

        for _ in range(15):
            st.write("")
        credits()

    round_num = int(data.loc[location]["RoundNumber"])
    st.title(f"🙍 {year} Drivers Championship")
    st.caption(f"After round {int(round_num)} — {location}")

    tabs = st.tabs(["🏆 Standings", "📊 Points per Race"])
    with tabs[0]:
        load_standings(standings, year, round_num)
    with tabs[1]:
        load_graphs(year, round_num)


main()
