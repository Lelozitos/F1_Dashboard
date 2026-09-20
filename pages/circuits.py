import streamlit as st
from app import nav_bar, credits
from graphs.colors import CIRCUIT_CHARS

import fastf1
from fastf1.ergast import Ergast

import pandas as pd
import plotly.express as px
import datetime


# Static laps/distance (track geometry barely changes) — lap records are fetched
# live from Ergast in get_circuit_record() below, so they never go stale.
CIRCUIT_LAYOUT = {
    "Bahrain":          (57, 5.412),
    "Saudi Arabian":    (50, 6.174),
    "Australian":       (58, 5.278),
    "Japanese":         (53, 5.807),
    "Chinese":          (56, 5.451),
    "Miami":            (57, 5.412),
    "Monaco":           (78, 3.337),
    "Spanish":          (66, 4.675),
    "Barcelona":        (66, 4.675),
    "Canadian":         (70, 4.361),
    "Austrian":         (71, 4.318),
    "British":          (52, 5.891),
    "Hungarian":        (70, 4.381),
    "Belgian":          (44, 7.004),
    "Dutch":            (72, 4.259),
    "Italian":          (53, 5.793),
    "Azerbaijan":       (51, 6.003),
    "Singapore":        (61, 5.063),
    "United States":    (56, 5.513),
    "Mexico City":      (71, 4.304),
    "São Paulo":        (71, 4.309),
    "Las Vegas":        (50, 6.201),
    "Qatar":            (57, 5.380),
    "Abu Dhabi":        (58, 5.281),
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


@st.cache_data(ttl=3600 * 24)
def get_circuit_record(event_name):
    """Fastest official race lap ever set at this circuit, scanned live from Ergast
    across every season on record (2018–present) so new records surface automatically."""
    ergast = Ergast()
    keyword = event_name.replace(" Grand Prix", "").strip()
    best = None  # (LapTime as pd.Timedelta, driver name, year)
    for year in range(datetime.date.today().year, 2018 - 1, -1):
        try:
            schedule = fastf1.get_event_schedule(year).query("EventFormat != 'testing'")
            match = schedule[schedule["EventName"].str.contains(keyword, case=False, na=False)]
            if match.empty:
                continue
            rnd = int(match.iloc[0]["RoundNumber"])
            result = ergast.get_race_results(season=year, round=rnd)
            if not result.content:
                continue
            df = result.content[0].dropna(subset=["fastestLapTime"])
            if df.empty:
                continue
            row = df.loc[df["fastestLapTime"].idxmin()]
            lap_time = row["fastestLapTime"]
            if best is None or lap_time < best[0]:
                best = (lap_time, f"{row['givenName']} {row['familyName']}", year)
        except Exception:
            continue
    if best is None:
        return None
    lap_time, driver, year = best
    total_seconds = lap_time.total_seconds()
    m, s = divmod(total_seconds, 60)
    return {"time": f"{int(m)}:{s:06.3f}", "driver": driver, "year": year}


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
    layout = CIRCUIT_LAYOUT.get(short)
    chars = CIRCUIT_CHARS.get(short)
    with col.container(border=True):
        st.markdown(f"#### R{int(event['RoundNumber'])} {flag} {short}")
        st.caption(f"📍 {event['Location']}, {event['Country']}")
        st.caption(f"📅 {pd.Timestamp(event['EventDate']).strftime('%d %b %Y')}")
        if show_record and layout:
            c1, c2 = st.columns(2)
            c1.metric("Laps", layout[0])
            c2.metric("Dist.", f"{layout[1]} km")
            record = get_circuit_record(event["EventName"])
            if record:
                st.caption(f"⏱ Record: **{record['time']}** — {record['driver']} ({record['year']})")
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
    layout = CIRCUIT_LAYOUT.get(short)
    chars = CIRCUIT_CHARS.get(short)
    with st.spinner("Loading lap record..."):
        record = get_circuit_record(selected)
    if layout:
        c1, c2, c3 = st.columns(3)
        c1.metric("Laps per Race", layout[0])
        c2.metric("Circuit Length", f"{layout[1]} km")
        c3.metric("Lap Record", record["time"] if record else "—")
        if record:
            st.caption(f"Record held by **{record['driver']}** ({record['year']})")
    if chars:
        st.markdown(_meters_html(*chars), unsafe_allow_html=True)
    if layout or chars:
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
