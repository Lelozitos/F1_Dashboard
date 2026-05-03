import streamlit as st
from home import nav_bar, credits
from graphs.colors import CIRCUIT_CHARS

import fastf1
from fastf1.ergast import Ergast

import pandas as pd
import plotly.express as px
import datetime


# TODO Change it in the future for real time data
CIRCUIT_INFO = {
    "Bahrain":          (57, 5.412, "1:31.447", "Pedro de la Rosa",   2005),
    "Saudi Arabian":    (50, 6.174, "1:30.734", "Lewis Hamilton",      2021),
    "Australian":       (58, 5.278, "1:19.813", "Charles Leclerc",     2022),
    "Japanese":         (53, 5.807, "1:30.983", "Lewis Hamilton",      2019),
    "Chinese":          (56, 5.451, "1:32.238", "Michael Schumacher",  2004),
    "Miami":            (57, 5.412, "1:29.708", "Max Verstappen",      2023),
    "Monaco":           (78, 3.337, "1:12.909", "Rubens Barrichello",  2004),
    "Spanish":          (66, 4.675, "1:18.149", "Max Verstappen",      2021),
    "Barcelona":        (66, 4.675, "1:18.149", "Max Verstappen",      2021),
    "Canadian":         (70, 4.361, "1:13.078", "Valtteri Bottas",     2019),
    "Austrian":         (71, 4.318, "1:05.619", "Carlos Sainz",        2020),
    "British":          (52, 5.891, "1:27.097", "Max Verstappen",      2020),
    "Hungarian":        (70, 4.381, "1:16.627", "Lewis Hamilton",      2020),
    "Belgian":          (44, 7.004, "1:46.286", "Valtteri Bottas",     2018),
    "Dutch":            (72, 4.259, "1:11.097", "Lewis Hamilton",      2021),
    "Italian":          (53, 5.793, "1:21.046", "Rubens Barrichello",  2004),
    "Azerbaijan":       (51, 6.003, "1:43.009", "Charles Leclerc",     2019),
    "Singapore":        (61, 5.063, "1:35.867", "Kevin Magnussen",     2018),
    "United States":    (56, 5.513, "1:36.169", "Charles Leclerc",     2019),
    "Mexico City":      (71, 4.304, "1:17.774", "Valtteri Bottas",     2021),
    "São Paulo":        (71, 4.309, "1:10.540", "Valtteri Bottas",     2018),
    "Las Vegas":        (50, 6.201, "1:35.490", "Max Verstappen",      2023),
    "Qatar":            (57, 5.380, "1:24.319", "Max Verstappen",      2023),
    "Abu Dhabi":        (58, 5.281, "1:26.103", "Max Verstappen",      2021),
}


COUNTRY_FLAGS = {
    "Bahrain": "🇧🇭", "Saudi Arabia": "🇸🇦", "Australia": "🇦🇺",
    "Japan": "🇯🇵", "China": "🇨🇳", "United States": "🇺🇸",
    "Italy": "🇮🇹", "Monaco": "🇲🇨", "Canada": "🇨🇦",
    "Spain": "🇪🇸", "Austria": "🇦🇹", "United Kingdom": "🇬🇧",
    "Hungary": "🇭🇺", "Belgium": "🇧🇪", "Netherlands": "🇳🇱",
    "Azerbaijan": "🇦🇿", "Singapore": "🇸🇬", "Mexico": "🇲🇽",
    "Brazil": "🇧🇷", "Qatar": "🇶🇦", "United Arab Emirates": "🇦🇪",
}


@st.cache_data(persist=True)
def get_event_schedule(year):
    return fastf1.get_event_schedule(year).query("EventFormat != 'testing'").reset_index(drop=True)


@st.cache_data(ttl=3600 * 6)
def get_race_winners(year):
    ergast = Ergast()
    try:
        schedule = fastf1.get_event_schedule(year).query("EventFormat != 'testing'")
    except Exception:
        return pd.DataFrame()
    now = pd.Timestamp.now("UTC")
    s5  = pd.to_datetime(schedule["Session5DateUtc"], utc=True)
    past = schedule[s5 < now]
    rows = []
    for _, event in past.iterrows():
        try:
            result = ergast.get_race_results(season=year, round=int(event["RoundNumber"]))
            if result.content:
                w = result.content[0].iloc[0]
                rows.append({
                    "Round": int(event["RoundNumber"]),
                    "Event": event["EventName"].replace(" Grand Prix", ""),
                    "Country": event["Country"],
                    "Date": event["EventDate"],
                    "Winner": f"{w['givenName']} {w['familyName']}",
                    "Team": w["constructorNames"][0] if w["constructorNames"] else "",
                })
        except Exception:
            continue
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600 * 24)
def get_circuit_history(event_name):
    ergast = Ergast()
    keyword = event_name.replace(" Grand Prix", "").strip()
    rows = []
    for year in range(datetime.date.today().year, 2018 - 1, -1):
        try:
            schedule = fastf1.get_event_schedule(year).query("EventFormat != 'testing'")
            match = schedule[schedule["EventName"].str.contains(keyword, case=False, na=False)]
            if match.empty:
                continue
            rnd = int(match.iloc[0]["RoundNumber"])
            result = ergast.get_race_results(season=year, round=rnd)
            if result.content:
                w = result.content[0].iloc[0]
                rows.append({
                    "Year": year,
                    "Winner": f"{w['givenName']} {w['familyName']}",
                    "Team": w["constructorNames"][0] if w["constructorNames"] else "",
                    "Code": w["driverCode"],
                })
        except Exception:
            continue
    return pd.DataFrame(rows)


def _meters_html(speed: int, downforce: int, braking: int, overtaking: int) -> str:
    metrics = [("Speed", speed), ("Downforce", downforce), ("Braking", braking), ("Overtaking", overtaking)]

    def bars(val):
        return "".join(
            f'<span style="display:inline-block;width:14px;height:7px;border-radius:2px;'
            f'background:{"#6C3DE8" if i <= val else "#e5e7eb"};margin-right:2px;"></span>'
            for i in range(1, 6)
        )

    rows = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">'
        f'<span style="font-size:0.72rem;color:#666;width:68px;flex-shrink:0;">{label}</span>'
        f'<div>{bars(val)}</div>'
        f'</div>'
        for label, val in metrics
    )
    return f'<div style="margin-top:8px;">{rows}</div>'


def _circuit_card(col, event, show_record=True):
    short = event["EventName"].replace(" Grand Prix", "")
    flag = COUNTRY_FLAGS.get(event["Country"], "🏁")
    info = CIRCUIT_INFO.get(short)
    chars = CIRCUIT_CHARS.get(short)
    with col.container(border=True):
        st.markdown(f"#### R{int(event['RoundNumber'])} {flag} {short}")
        st.caption(f"📍 {event['Location']}, {event['Country']}")
        st.caption(f"📅 {pd.Timestamp(event['EventDate']).strftime('%d %b %Y')}")
        if show_record and info:
            c1, c2 = st.columns(2)
            c1.metric("Laps", info[0])
            c2.metric("Dist.", f"{info[1]} km")
            st.caption(f"⏱ Record: **{info[2]}** — {info[3]} ({info[4]})")
        if chars:
            st.markdown(_meters_html(*chars), unsafe_allow_html=True)


def tab_calendar(schedule):
    now = pd.Timestamp.now("UTC")
    s5  = pd.to_datetime(schedule["Session5DateUtc"], utc=True)
    past = schedule[s5 < now]
    upcoming = schedule[s5 >= now]

    if not past.empty:
        st.subheader(f"Completed — {len(past)} rounds")
        for i in range(0, len(past), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(past):
                    _circuit_card(cols[j], past.iloc[i + j])

    if not upcoming.empty:
        st.subheader(f"Upcoming — {len(upcoming)} rounds")
        for i in range(0, len(upcoming), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(upcoming):
                    _circuit_card(cols[j], upcoming.iloc[i + j])


def tab_winners(year, schedule):
    with st.spinner("Loading race results..."):
        df = get_race_winners(year)

    if df.empty:
        st.info("No race results available yet for this season.")
        return

    win_counts = df["Winner"].value_counts().reset_index()
    win_counts.columns = ["Driver", "Wins"]
    fig = px.bar(
        win_counts, x="Driver", y="Wins",
        title=f"{year} — Wins per Driver",
        color="Wins", color_continuous_scale=["#6C3DE8", "#E8002D"],
        text="Wins",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False, title_font_size=20,
        margin=dict(l=0, r=0, t=50, b=0), xaxis_title="", yaxis_title="Wins",
    )
    st.plotly_chart(fig, use_container_width=True)

    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%d %b %Y")
    st.dataframe(
        df[["Round", "Country", "Event", "Date", "Winner", "Team"]],
        use_container_width=True, hide_index=True,
    )


def tab_history(schedule):
    event_names = schedule["EventName"].tolist()
    selected = st.selectbox("Select Circuit", event_names, format_func=lambda x: x.replace(" Grand Prix", ""))

    short = selected.replace(" Grand Prix", "")
    info = CIRCUIT_INFO.get(short)
    chars = CIRCUIT_CHARS.get(short)
    if info:
        c1, c2, c3 = st.columns(3)
        c1.metric("Laps per Race", info[0])
        c2.metric("Circuit Length", f"{info[1]} km")
        c3.metric("Lap Record", info[2])
        st.caption(f"Record held by **{info[3]}** ({info[4]})")
    if chars:
        st.markdown(_meters_html(*chars), unsafe_allow_html=True)
    if info or chars:
        st.divider()

    with st.spinner("Loading circuit history (2018–present)..."):
        df = get_circuit_history(selected)

    if df.empty:
        st.info("No historical data found for this circuit.")
        return

    win_counts = df["Winner"].value_counts().reset_index()
    win_counts.columns = ["Driver", "Wins"]
    fig = px.bar(
        win_counts, x="Driver", y="Wins",
        title=f"Most wins at {short} (2018–present)",
        color="Wins", color_continuous_scale=["#6C3DE8", "#E8002D"],
        text="Wins",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False, title_font_size=20,
        margin=dict(l=0, r=0, t=50, b=0), xaxis_title="", yaxis_title="Wins",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


def main():
    nav_bar()

    with st.sidebar:
        year = st.selectbox("Year", range(datetime.date.today().year, 2018 - 1, -1))
        for _ in range(20):
            st.write("")
        credits()

    schedule = get_event_schedule(year)

    st.title(f"🏁 {year} Circuits & Calendar")

    tabs = st.tabs(["🗺️ Season Calendar", "🏆 Race Winners", "📜 Circuit History"])
    with tabs[0]:
        tab_calendar(schedule)
    with tabs[1]:
        tab_winners(year, schedule)
    with tabs[2]:
        tab_history(schedule)


main()
