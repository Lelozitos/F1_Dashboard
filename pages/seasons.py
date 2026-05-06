import streamlit as st
from home import nav_bar, credits

import fastf1
from fastf1.ergast import Ergast
from graphs.colors import TEAM_COLORS

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import datetime


def _team_color(name):
    for key, color in TEAM_COLORS.items():
        if key.lower() in name.lower():
            return color
    return "#888888"


@st.cache_data(persist=True)
def load_season_data(year):
    """
    Returns (race_winners_df, driver_points_df, constructor_cumulative_df)
    for all completed rounds of the given year.

    race_winners_df  : Round | Event | Country | Date | Winner | Team | WinnerCode
    driver_points_df : driverCode × race_name  (points earned that race, NaN = 0)
    constructor_cumulative_df : Round | Team | CumulativePoints
    """
    ergast = Ergast()
    try:
        schedule = fastf1.get_event_schedule(year, backend="ergast").query("EventFormat != 'testing'")
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    now = pd.Timestamp.utcnow().to_datetime64()
    past = schedule[schedule["Session5DateUtc"] < now].copy()
    if past.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    winners_rows = []
    driver_rows  = []   # [{round, race, driverCode, points}, …]
    constructor_rows = []

    for _, event in past.iterrows():
        rnd  = int(event["RoundNumber"])
        name = event["EventName"].replace(" Grand Prix", "")

        # ── Race results ──────────────────────────────────────────────────
        try:
            result = ergast.get_race_results(season=year, round=rnd)
            if not result.content:
                continue
            df = result.content[0].copy()

            # Merge sprint points if available
            try:
                sprint = ergast.get_sprint_results(season=year, round=rnd)
                if sprint.content and sprint.description["round"][0] == rnd:
                    df = pd.merge(df, sprint.content[0][["driverCode", "points"]],
                                  on="driverCode", how="left", suffixes=("", "_spr"))
                    df["points"] = df["points"] + df["points_spr"].fillna(0)
                    df.drop(columns=["points_spr"], inplace=True)
            except Exception:
                pass

            # Winner row
            w = df.iloc[0]
            winners_rows.append({
                "Round":      rnd,
                "Event":      name,
                "Country":    event["Country"],
                "Date":       event["EventDate"],
                "Winner":     f"{w['givenName']} {w['familyName']}",
                "Team":       w["constructorNames"][0] if w["constructorNames"] else "",
                "WinnerCode": w["driverCode"],
            })

            # Driver points rows
            for _, row in df.iterrows():
                driver_rows.append({
                    "Round":      rnd,
                    "Race":       name,
                    "DriverCode": row["driverCode"],
                    "Name":       f"{row['givenName']} {row['familyName']}",
                    "Points":     float(row["points"]),
                })

        except Exception:
            continue

        # ── Constructor standings (cumulative after this round) ───────────
        try:
            cs = ergast.get_constructor_standings(season=year, round=rnd)
            if cs.content:
                for _, team in cs.content[0].iterrows():
                    constructor_rows.append({
                        "Round":             rnd,
                        "Event":             name,
                        "Team":              team["constructorName"],
                        "CumulativePoints":  int(team["points"]),
                    })
        except Exception:
            pass

    winners_df = pd.DataFrame(winners_rows)
    driver_df  = pd.DataFrame(driver_rows)
    constructor_df = pd.DataFrame(constructor_rows)

    return winners_df, driver_df, constructor_df


# ─────────────────────────────────────────────────────────────────────────────

def _build_driver_matrix(driver_df):
    """Pivot: DriverCode × Race → Points earned that race."""
    if driver_df.empty:
        return pd.DataFrame()
    pivot = driver_df.pivot_table(index="DriverCode", columns="Race",
                                  values="Points", aggfunc="sum")
    pivot["_total"] = pivot.sum(axis=1)
    pivot.sort_values("_total", ascending=False, inplace=True)
    pivot.drop(columns="_total", inplace=True)
    return pivot


def _build_driver_cumulative(driver_df):
    """Cumulative driver points over rounds."""
    if driver_df.empty:
        return pd.DataFrame()
    grouped = (driver_df.groupby(["DriverCode", "Name", "Round"])["Points"]
               .sum().reset_index())
    grouped.sort_values("Round", inplace=True)
    grouped["Cumulative"] = grouped.groupby("DriverCode")["Points"].cumsum()
    return grouped


# ─────────────────────────────────────────────────────────────────────────────

def tab_overview(year, winners_df):
    if winners_df.empty:
        st.info("No completed races yet this season.")
        return

    # ── Top metrics ───────────────────────────────────────────────────────
    win_counts   = winners_df["Winner"].value_counts()
    team_counts  = winners_df["Team"].value_counts()
    leader       = win_counts.index[0]
    top_team     = team_counts.index[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rounds Completed", len(winners_df))
    c2.metric("Unique Winners",   winners_df["Winner"].nunique())
    c3.metric("Most Wins — Driver", f"{leader} ({win_counts.iloc[0]})")
    c4.metric("Most Wins — Team",   f"{top_team} ({team_counts.iloc[0]})")
    st.divider()

    # ── Wins per driver bar chart ─────────────────────────────────────────
    wc = win_counts.reset_index()
    wc.columns = ["Driver", "Wins"]
    fig = px.bar(
        wc, x="Driver", y="Wins", text="Wins",
        title=f"{year} — Wins per Driver",
        color="Wins", color_continuous_scale=["#6C3DE8", "#E8002D"],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False, title_font_size=20,
        margin=dict(l=0, r=0, t=50, b=0), xaxis_title="", yaxis_title="Wins",
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Race winners table ────────────────────────────────────────────────
    display = winners_df.copy()
    display["Date"] = pd.to_datetime(display["Date"]).dt.strftime("%d %b %Y")
    st.dataframe(
        display[["Round", "Country", "Event", "Date", "Winner", "Team"]],
        use_container_width=True, hide_index=True,
    )


def tab_driver_championship(year, driver_df):
    if driver_df.empty:
        st.info("No data available.")
        return

    # ── Cumulative points line chart ──────────────────────────────────────
    cum_df = _build_driver_cumulative(driver_df)
    top_drivers = (cum_df.groupby("DriverCode")["Cumulative"].max()
                   .sort_values(ascending=False).head(10).index.tolist())
    cum_top = cum_df[cum_df["DriverCode"].isin(top_drivers)]

    fig = px.line(
        cum_top, x="Round", y="Cumulative",
        color="DriverCode", markers=True,
        title=f"{year} — Driver Points Progression (Top 10)",
        labels={"DriverCode": "Driver", "Cumulative": "Points", "Round": "Round"},
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        title_font_size=20, margin=dict(l=0, r=0, t=50, b=0),
        legend_title_text="Driver",
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Points heatmap ────────────────────────────────────────────────────
    matrix = _build_driver_matrix(driver_df)
    if matrix.empty:
        return

    fig2 = px.imshow(
        matrix,
        text_auto=True, aspect="auto",
        color_continuous_scale=[
            [0,    "rgb(240,235,252)"],
            [0.25, "rgb(180,150,240)"],
            [0.5,  "rgb(108,61,232)"],
            [0.75, "rgb(70,20,180)"],
            [1,    "rgb(30,0,100)"],
        ],
        labels={"x": "Race", "y": "Driver", "color": "Points"},
        title=f"{year} — Points per Race per Driver",
    )
    fig2.update_xaxes(title_text="", side="top", showgrid=False, showline=False)
    fig2.update_yaxes(title_text="", tickmode="linear",
                      showgrid=True, gridwidth=1, gridcolor="#eee",
                      showline=False, tickson="boundaries")
    fig2.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False,
        margin=dict(l=0, r=0, b=0, t=60), title_font_size=20,
    )
    st.plotly_chart(fig2, use_container_width=True)


def tab_constructor_championship(year, constructor_df):
    if constructor_df.empty:
        st.info("No constructor data available.")
        return

    # ── Cumulative points line chart with team colors ─────────────────────
    teams = constructor_df["Team"].unique().tolist()
    color_map = {t: _team_color(t) for t in teams}

    fig = px.line(
        constructor_df, x="Round", y="CumulativePoints",
        color="Team", color_discrete_map=color_map,
        markers=True,
        title=f"{year} — Constructor Points Progression",
        labels={"CumulativePoints": "Points", "Round": "Round", "Team": "Team"},
        custom_data=["Team", "Event"],
    )
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Points: %{y}<extra></extra>",
        line=dict(width=2.5),
        marker=dict(size=6),
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        title_font_size=20, margin=dict(l=0, r=0, t=50, b=0),
        legend_title_text="Team", xaxis_title="Round", yaxis_title="Points",
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Final standings bar chart ─────────────────────────────────────────
    last_round = constructor_df["Round"].max()
    final = (constructor_df[constructor_df["Round"] == last_round]
             .sort_values("CumulativePoints", ascending=False)
             .reset_index(drop=True))

    bar_colors = [_team_color(t) for t in final["Team"]]
    fig2 = go.Figure(go.Bar(
        x=final["Team"], y=final["CumulativePoints"],
        text=final["CumulativePoints"], textposition="outside",
        marker_color=bar_colors,
    ))
    fig2.update_layout(
        title=dict(text=f"{year} — Constructor Standings after Round {last_round}",
                   font_size=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=50, b=0),
        xaxis_title="", yaxis_title="Points",
    )
    st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────

def main():
    nav_bar()

    with st.sidebar:
        year = st.selectbox("Year", range(datetime.date.today().year, 2018 - 1, -1))
        load_btn = st.button("Load Season", icon="📥", use_container_width=True)
        for _ in range(8):
            st.write("")
        credits()

    # Persist loaded state across reruns
    state_key = f"season_{year}"
    if load_btn:
        st.session_state[state_key] = None  # trigger reload

    if load_btn or state_key in st.session_state:
        if st.session_state.get(state_key) is None:
            with st.spinner(f"Loading {year} season data (this may take a minute)…"):
                winners_df, driver_df, constructor_df = load_season_data(year)
            st.session_state[state_key] = (winners_df, driver_df, constructor_df)
        else:
            winners_df, driver_df, constructor_df = st.session_state[state_key]

        st.title(f"📅 {year} Season Overview")
        completed = len(winners_df)
        total = len(fastf1.get_event_schedule(year).query("EventFormat != 'testing'"))
        st.caption(f"{completed} of {total} rounds completed")

        tabs = st.tabs(["🏆 Race Winners", "🙍 Driver Championship", "🏗️ Constructor Championship"])
        with tabs[0]:
            tab_overview(year, winners_df)
        with tabs[1]:
            tab_driver_championship(year, driver_df)
        with tabs[2]:
            tab_constructor_championship(year, constructor_df)

    else:
        st.title("📅 Season Overview")
        st.markdown(
            "<p style='color:#888; font-size:1.05rem;'>"
            "← Select a year in the sidebar and press <strong>Load Season</strong>.</p>",
            unsafe_allow_html=True,
        )


main()
