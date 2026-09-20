"""Tools wrapping FastF1, Ergast and OpenF1 data sources for the F1 AI agent.

Mirrors the data-access patterns already used across pages/*.py in the main app
(fastf1.get_session / fastf1.get_event_schedule, fastf1.ergast.Ergast, and the
OpenF1 pit-stop endpoint), but returns compact JSON strings instead of
rendering Streamlit widgets, since these are consumed by Gemini as tool results.

No `from __future__ import annotations` here on purpose: google-genai's automatic
function calling reads argument types straight off `inspect.signature(...).annotation`
without resolving postponed (string) annotations, so a deferred annotation makes it
crash with "isinstance() arg 2 must be a type, a tuple of types, or a union" on every
call. Keep annotations as real runtime types, or the resolution differs on schema
build vs. call time.
"""
import functools
import json
import fastf1
import pandas as pd
import requests
from fastf1.ergast import Ergast

_ergast = Ergast()


def _df_to_records(df: pd.DataFrame) -> list:
    """Convert a DataFrame to JSON-safe records (NaN -> null, dates -> ISO strings)."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _fmt_td(td) -> str | None:
    """Format a pandas Timedelta as "M:SS.mmm" instead of "0 days 00:01:21.676000"."""
    if td is None or pd.isna(td):
        return None
    total = td.total_seconds()
    minutes, seconds = divmod(total, 60)
    return f"{int(minutes)}:{seconds:06.3f}"


def _stringify_timedeltas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_timedelta64_dtype(df[col]):
            df[col] = df[col].apply(_fmt_td)
    return df


@functools.lru_cache(maxsize=16)
def _load_session(year: int, event: str, session: str, laps: bool, weather: bool):
    data = fastf1.get_session(year, event, session)
    data.load(laps=laps, telemetry=False, weather=weather, messages=False)
    return data


def get_event_schedule(year: int) -> str:
    """List the Grand Prix calendar for a season (rounds, events, countries, dates).

    Args:
        year: Season year, e.g. 2024. Data only goes back to 2018.
    """
    try:
        schedule = fastf1.get_event_schedule(year).query("EventFormat != 'testing'")
    except Exception as e:
        return json.dumps({"error": str(e)})
    cols = ["RoundNumber", "EventName", "Country", "Location", "EventDate", "EventFormat"]
    cols = [c for c in cols if c in schedule.columns]
    return json.dumps(_df_to_records(schedule[cols]))


def get_session_results(year: int, event: str, session: str) -> str:
    """Get the classification, fastest lap per driver, and weather summary for one session.

    Args:
        year: Season year, e.g. 2024.
        event: Event name or round number, e.g. "Monza" or "Italian Grand Prix".
        session: Session identifier: "FP1", "FP2", "FP3", "Q", "S" (sprint), or "R" (race).
    """
    try:
        data = _load_session(year, event, session, True, True)
    except Exception as e:
        return json.dumps({"error": str(e)})

    cols = [c for c in ["Position", "Abbreviation", "TeamName", "GridPosition",
                         "Status", "Points", "Time"] if c in data.results.columns]
    results = _df_to_records(data.results[cols]) if cols else []

    fastest = []
    if not data.laps.empty:
        for drv in data.laps["Driver"].unique():
            lap = data.laps.pick_drivers([drv]).pick_fastest()
            if lap is not None and pd.notna(lap.get("LapTime")):
                fastest.append({"Driver": drv, "FastestLap": _fmt_td(lap["LapTime"])})

    weather = {}
    if not data.weather_data.empty:
        w = data.weather_data
        weather = {
            "AirTemp_avg_C": round(float(w["AirTemp"].mean()), 1),
            "TrackTemp_avg_C": round(float(w["TrackTemp"].mean()), 1),
            "Humidity_avg_pct": round(float(w["Humidity"].mean()), 1),
            "Rainfall": bool(w["Rainfall"].any()),
        }

    return json.dumps({
        "session": f"{year} {event} {session}",
        "results": results,
        "fastest_laps": fastest,
        "weather": weather,
    })


def get_driver_lap_times(year: int, event: str, session: str, driver: str) -> str:
    """Get every lap time for one driver in a session, including compound and pit laps.

    Args:
        year: Season year.
        event: Event name or round number.
        session: Session identifier: "FP1", "FP2", "FP3", "Q", "S", or "R".
        driver: Driver three-letter code, e.g. "VER", "HAM", "LEC".
    """
    try:
        data = _load_session(year, event, session, True, False)
    except Exception as e:
        return json.dumps({"error": str(e)})

    laps = data.laps.pick_drivers([driver])
    if laps.empty:
        return json.dumps({"error": f"No laps found for driver '{driver}' in this session"})

    cols = [c for c in ["LapNumber", "LapTime", "Compound", "Stint",
                         "PitInTime", "PitOutTime", "TrackStatus"] if c in laps.columns]
    rows = _stringify_timedeltas(laps[cols])
    return json.dumps(_df_to_records(rows))


def compare_fastest_laps(year: int, event: str, session: str, drivers: list[str]) -> str:
    """Compare fastest lap time, compound and sector times for several drivers in one session.

    Args:
        year: Season year.
        event: Event name or round number.
        session: Session identifier: "FP1", "FP2", "FP3", "Q", "S", or "R".
        drivers: Driver three-letter codes to compare, e.g. ["VER", "LEC"].
    """
    try:
        data = _load_session(year, event, session, True, False)
    except Exception as e:
        return json.dumps({"error": str(e)})

    out = []
    for drv in drivers:
        lap = data.laps.pick_drivers([drv]).pick_fastest()
        if lap is None or pd.isna(lap.get("LapTime")):
            out.append({"Driver": drv, "error": "no valid lap found"})
            continue
        out.append({
            "Driver": drv,
            "LapTime": _fmt_td(lap.get("LapTime")),
            "Compound": lap.get("Compound"),
            "Sector1": _fmt_td(lap.get("Sector1Time")),
            "Sector2": _fmt_td(lap.get("Sector2Time")),
            "Sector3": _fmt_td(lap.get("Sector3Time")),
        })
    return json.dumps(out)


def get_driver_standings(year: int, round: int | None = None) -> str:
    """Get the drivers' championship standings for a season.

    Args:
        year: Season year.
        round: Round number to get standings as-of. Omit for the latest available round.
    """
    try:
        result = _ergast.get_driver_standings(season=year, round=round)
        if not result.content:
            return json.dumps({"error": "No standings found"})
        df = result.content[0]
        cols = [c for c in ["position", "driverCode", "givenName", "familyName",
                             "constructorNames", "points", "wins"] if c in df.columns]
        return json.dumps(_df_to_records(df[cols]))
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_constructor_standings(year: int, round: int | None = None) -> str:
    """Get the constructors' championship standings for a season.

    Args:
        year: Season year.
        round: Round number to get standings as-of. Omit for the latest available round.
    """
    try:
        result = _ergast.get_constructor_standings(season=year, round=round)
        if not result.content:
            return json.dumps({"error": "No standings found"})
        df = result.content[0]
        cols = [c for c in ["position", "constructorName", "points", "wins"] if c in df.columns]
        return json.dumps(_df_to_records(df[cols]))
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_race_results(year: int, round: int) -> str:
    """Get full race classification for one round, merged with sprint points if that weekend ran a sprint.

    Args:
        year: Season year.
        round: Round number in the season, e.g. 1 for the season opener.
    """
    try:
        result = _ergast.get_race_results(season=year, round=round)
        if not result.content:
            return json.dumps({"error": "No results found"})
        df = result.content[0].copy()
        try:
            sprint = _ergast.get_sprint_results(season=year, round=round)
            if sprint.content and sprint.description["round"][0] == round:
                df = pd.merge(df, sprint.content[0][["driverCode", "points"]],
                               on="driverCode", how="left", suffixes=("", "_sprint"))
                df["points"] = df["points"] + df["points_sprint"].fillna(0)
                df.drop(columns=["points_sprint"], inplace=True)
        except Exception:
            pass
        cols = [c for c in ["position", "driverCode", "givenName", "familyName",
                             "constructorNames", "grid", "points", "status", "time"] if c in df.columns]
        return json.dumps(_df_to_records(df[cols]))
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_pit_stops(year: int, event: str, session: str) -> str:
    """Get pit stop data for a session from OpenF1 (community data source, occasionally incomplete/unreliable).

    Args:
        year: Season year.
        event: Event name or round number.
        session: Session identifier: "FP1", "FP2", "FP3", "Q", "S", or "R".
    """
    try:
        data = _load_session(year, event, session, False, False)
    except Exception as e:
        return json.dumps({"error": str(e)})

    key = data.session_info.get("Key")
    if key is None:
        return json.dumps({"error": "Session key unavailable"})

    try:
        resp = requests.get(f"https://api.openf1.org/v1/pit?session_key={key}", timeout=15)
        resp.raise_for_status()
        pits = resp.json()
    except Exception as e:
        return json.dumps({"error": f"OpenF1 request failed: {e}"})

    if not pits:
        return json.dumps({"error": "No pit stop data returned by OpenF1 for this session"})

    for p in pits:
        try:
            p["driver"] = data.get_driver(str(p.get("driver_number")))["Abbreviation"]
        except Exception:
            p["driver"] = p.get("driver_number")

    return json.dumps(pits)


ALL_TOOLS = [
    get_event_schedule,
    get_session_results,
    get_driver_lap_times,
    compare_fastest_laps,
    get_driver_standings,
    get_constructor_standings,
    get_race_results,
    get_pit_stops,
]
