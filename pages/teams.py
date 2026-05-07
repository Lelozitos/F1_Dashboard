import streamlit as st
from home import nav_bar, credits

import fastf1
from fastf1.ergast import Ergast
from graphs.colors import TEAM_COLORS

import plotly.graph_objects as go
import pandas as pd
import datetime

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
    "Racing Bulls":  "racingbulls",
    "Audi":          "audi",
    "Kick Sauber":   "audi",
    "Sauber":        "sauber",
    "Cadillac":      "cadillac",
}


def _team_color(team_name):
    for key, color in TEAM_COLORS.items():
        if key.lower() in team_name.lower():
            return color
    return "#888888"


def _team_slug(raw_name: str) -> str:
    for key, slug in _TEAM_SLUG.items():
        if key.lower() in raw_name.lower():
            return slug
    return raw_name.lower().replace(" ", "")


def _car_url(year: int, slug: str) -> str:
    return (
        f"https://media.formula1.com/image/upload/c_lfill,w_512/q_auto"
        f"/d_common:f1:{year}:fallback:car:{year}fallbackcarright.webp"
        f"/v1740000001/common/f1/{year}/{slug}/{year}{slug}carright.webp"
    )


def _logo_url(year: int, slug: str) -> str:
    return (
        f"https://media.formula1.com/image/upload/c_lfill,w_48/q_auto"
        f"/v1740000001/common/f1/{year}/{slug}/{year}{slug}logowhite.webp"
    )


def load_standings(standings, year):
    for i in range(0, len(standings), 2):
        cols = st.columns(2, gap="medium")
        for j in range(2):
            try:
                team = standings.iloc[i + j]
            except IndexError:
                continue

            raw  = team["constructorName"]
            slug = _team_slug(raw)
            color = _team_color(raw)

            with cols[j].container(border=True):
                st.markdown(
                    f"<div style='border-left:5px solid {color}; padding-left:10px;'>"
                    f"<span style='font-size:1.5rem; font-weight:800;'>P{int(team['position'])}</span> "
                    f"<span style='font-size:1.2rem; font-weight:600;'>{raw}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                c1, c2 = st.columns(2)
                c1.metric("Points", int(team["points"]))
                c2.metric("Wins", int(team.get("wins", 0)))

                img_c1, img_c2 = st.columns(2)
                with img_c1:
                    try:
                        st.image(_car_url(year, slug), use_container_width=True)
                    except Exception:
                        st.caption("🚗 Car image unavailable")
                with img_c2:
                    try:
                        st.image(_logo_url(year, slug), use_container_width=True)
                    except Exception:
                        st.caption("🏷 Logo unavailable")


@st.cache_data(persist=True)
def load_points_data(year, round_num):
    ergast = Ergast()
    try:
        schedule = fastf1.get_event_schedule(year).query("EventFormat != 'testing'")
        round_to_name = {
            int(r): n.replace(" Grand Prix", "")
            for r, n in zip(schedule["RoundNumber"], schedule["EventName"])
        }
    except Exception:
        round_to_name = {}

    rows = []
    for rnd in range(1, round_num + 1):
        try:
            result = ergast.get_constructor_standings(season=year, round=rnd).content[0]
            for _, team in result.iterrows():
                rows.append({
                    "Round": rnd,
                    "Event": round_to_name.get(rnd, f"R{rnd}"),
                    "Team":  team["constructorName"],
                    "Points": int(team["points"]),
                })
        except Exception:
            continue
    return pd.DataFrame(rows)


def load_graphs(year, round_num, standings):
    with st.spinner("Loading points progression..."):
        try:
            df = load_points_data(year, round_num)
        except Exception as e:
            st.error(f"Could not load data: {e}")
            return

    if df.empty:
        st.info("No data available.")
        return

    color_map = {row["constructorName"]: _team_color(row["constructorName"])
                 for _, row in standings.iterrows()}

    # Line chart – cumulative points per round, with unified hover + race name ticks
    event_labels = (
        df[["Round", "Event"]].drop_duplicates()
        .sort_values("Round")
        .set_index("Round")["Event"]
        .to_dict()
    )
    tick_vals  = sorted(event_labels.keys())
    tick_texts = [event_labels[r] for r in tick_vals]

    fig = go.Figure()
    for team_name, group in df.groupby("Team"):
        group = group.sort_values("Round")
        fig.add_trace(go.Scatter(
            x=group["Round"], y=group["Points"],
            mode="lines+markers", name=team_name,
            line=dict(color=color_map.get(team_name, "#888"), width=2.5),
            marker=dict(size=6),
            customdata=group["Event"],
            hovertemplate="%{fullData.name}: <b>%{y} pts</b><extra></extra>",
        ))
    fig.update_layout(
        title=dict(text=f"{year} Constructors — Points Progression", font_size=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=50, b=80),
        xaxis=dict(
            title="",
            tickmode="array",
            tickvals=tick_vals,
            ticktext=tick_texts,
            tickangle=-45,
        ),
        yaxis_title="Points",
        legend_title_text="Team",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Final standings — horizontal bar, sorted by points desc, with gap to leader
    last = (
        df[df["Round"] == df["Round"].max()]
        .sort_values("Points", ascending=False)
        .reset_index(drop=True)
    )
    leader_pts = last["Points"].iloc[0]
    last["Gap"]      = last["Points"] - leader_pts          # ≤ 0
    last["Position"] = [f"P{i+1}" for i in range(len(last))]
    last["Label"]    = last.apply(
        lambda r: f"{int(r['Points'])} pts" if r["Gap"] == 0
                  else f"{int(r['Points'])} pts  ({int(r['Gap'])})",
        axis=1,
    )
    bar_colors = [color_map.get(t, "#888") for t in last["Team"]]

    fig2 = go.Figure(go.Bar(
        y=last["Position"] + "  " + last["Team"],
        x=last["Points"],
        orientation="h",
        text=last["Label"],
        textposition="outside",
        marker_color=bar_colors,
        hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
    ))
    fig2.update_layout(
        title=dict(text=f"{year} Constructors Standings — Round {round_num}", font_size=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=120, t=50, b=0),
        xaxis_title="Points", yaxis=dict(autorange="reversed", title=""),
        height=max(350, len(last) * 42),
    )
    st.plotly_chart(fig2, use_container_width=True)


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
                standings = ergast.get_constructor_standings(
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
    st.title(f"🏗️ {year} Constructors Championship")
    st.caption(f"After round {round_num} — {location}")

    tabs = st.tabs(["🏆 Standings", "📈 Points Progression"])
    with tabs[0]:
        load_standings(standings, year)
    with tabs[1]:
        load_graphs(year, round_num, standings)


main()
