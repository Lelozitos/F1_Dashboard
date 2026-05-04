import streamlit as st
import pandas as pd
import numpy as np
import fastf1
from fastf1.ergast import Ergast
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import plotly.graph_objects as go
from home import nav_bar, credits
from graphs.colors import TEAM_COLORS

CURRENT_YEAR = pd.Timestamp.now().year
FEATURES = ['grid', 'driver_pts_before', 'constructor_pts_before', 'recent_avg_3']
FEATURE_LABELS = ['Grid Position', 'Driver Champ. Points', 'Constructor Points', 'Recent Avg Finish (3 races)']


def _safe_int(val, default=20):
    try:
        return int(val)
    except Exception:
        return default


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except Exception:
        return default


def _col(row, names, default=None):
    for n in names:
        if n in row.index and pd.notna(row[n]):
            return row[n]
    return default


def _find_col(df, names):
    for n in names:
        if n in df.columns:
            return n
    return None


def _extract_constructor(val):
    if val is None:
        return ''
    if isinstance(val, (list, tuple)):
        return str(val[0]) if val else ''
    return str(val)


def _team_color(constructor: str) -> str:
    cl = constructor.lower()
    for team, color in TEAM_COLORS.items():
        tl = team.lower()
        if tl in cl or cl in tl:
            return color
    return '#888888'


@st.cache_data(persist=True, show_spinner=False)
def build_training_data(start_year: int, end_year: int) -> pd.DataFrame:
    ergast = Ergast()
    rows = []

    for year in range(start_year, end_year + 1):
        try:
            season = ergast.get_race_results(season=year)
        except Exception:
            continue
        if not season or not season.content:
            continue

        d_pts: dict = {}
        c_pts: dict = {}
        d_recent: dict = {}

        for round_idx, race_df in enumerate(season.content):
            if race_df is None or race_df.empty:
                continue

            drv_col = _find_col(race_df, ['driverCode', 'Driver.driverCode'])
            con_col = _find_col(race_df, ['constructorName', 'Constructor.name', 'constructorId'])

            for _, row in race_df.iterrows():
                drv = str(_col(row, [drv_col] if drv_col else [], ''))
                con = str(_col(row, [con_col] if con_col else [], ''))
                grid = _safe_int(_col(row, ['grid'], 20))
                if grid == 0:
                    grid = 20
                pos_text = str(_col(row, ['positionText', 'position'], '20'))
                try:
                    pos = int(pos_text)
                except Exception:
                    pos = 20
                pts = _safe_float(_col(row, ['points'], 0))

                recent = d_recent.get(drv, [])
                rows.append({
                    'year': year,
                    'driver': drv,
                    'constructor': con,
                    'grid': grid,
                    'driver_pts_before': d_pts.get(drv, 0.0),
                    'constructor_pts_before': c_pts.get(con, 0.0),
                    'recent_avg_3': float(np.mean(recent[-3:])) if recent else 10.0,
                    'won': 1 if pos == 1 else 0,
                })

                d_pts[drv] = d_pts.get(drv, 0.0) + pts
                c_pts[con] = c_pts.get(con, 0.0) + pts
                d_recent[drv] = (recent + [pos])[-10:]

    return pd.DataFrame(rows)


@st.cache_resource(show_spinner=False)
def get_trained_model(start_year: int, end_year: int):
    df = build_training_data(start_year, end_year)
    if df.empty or df['won'].sum() < 10:
        return None, FEATURES, 0.0, 0, 0

    X = df[FEATURES].fillna(df[FEATURES].median())
    y = df['won']
    split = int(len(df) * 0.8)

    model = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            min_samples_leaf=8, subsample=0.8, random_state=42,
        ))
    ])
    model.fit(X.iloc[:split], y.iloc[:split])
    accuracy = model.score(X.iloc[split:], y.iloc[split:])
    return model, FEATURES, accuracy, len(df), int(df['won'].sum())


@st.cache_data(persist=True, show_spinner=False)
def get_quali_grid(year: int, round_num: int):
    try:
        ergast = Ergast()
        quali = ergast.get_qualifying_results(season=year, round=round_num)
        if not (quali and quali.content and not quali.content[0].empty):
            return pd.DataFrame(), False

        df = quali.content[0].copy()
        drv_col = _find_col(df, ['driverCode', 'Driver.driverCode'])
        con_col = _find_col(df, ['constructorName', 'Constructor.name', 'constructorNames', 'constructorId', 'constructorIds'])
        pos_col = _find_col(df, ['position'])

        if not (drv_col and pos_col):
            return pd.DataFrame(), False

        result = pd.DataFrame({
            'driver': df[drv_col].astype(str),
            'constructor': df[con_col].apply(_extract_constructor) if con_col else [''] * len(df),
            'grid': pd.to_numeric(df[pos_col], errors='coerce').fillna(20).astype(int),
        })
        return result, True
    except Exception:
        return pd.DataFrame(), False


@st.cache_data(persist=True, show_spinner=False)
def get_standings_and_form(year: int, round_num: int):
    ergast = Ergast()
    d_pts: dict = {}
    c_pts: dict = {}
    d_con: dict = {}
    recent_form: dict = {}
    prev = max(1, round_num - 1)

    try:
        ds = ergast.get_driver_standings(season=year, round=prev).content[0]
        drv_col = _find_col(ds, ['driverCode', 'Driver.driverCode'])
        con_col = _find_col(ds, ['constructorName', 'Constructor.name', 'constructorNames', 'constructorId', 'constructorIds'])
        pts_col = _find_col(ds, ['points', 'Points'])
        if drv_col:
            for _, r in ds.iterrows():
                d = str(r[drv_col])
                d_pts[d] = _safe_float(r.get(pts_col or 'points', 0))
                if con_col:
                    d_con[d] = _extract_constructor(r[con_col])
    except Exception:
        pass

    try:
        cs = ergast.get_constructor_standings(season=year, round=prev).content[0]
        con_col = _find_col(cs, ['constructorName', 'Constructor.name', 'constructorId'])
        pts_col = _find_col(cs, ['points', 'Points'])
        if con_col:
            for _, r in cs.iterrows():
                c_pts[str(r[con_col])] = _safe_float(r.get(pts_col or 'points', 0))
    except Exception:
        pass

    try:
        season = ergast.get_race_results(season=year)
        if season and season.content:
            for race_df in season.content[:prev]:
                if race_df is None or race_df.empty:
                    continue
                drv_col = _find_col(race_df, ['driverCode', 'Driver.driverCode'])
                if not drv_col:
                    continue
                for _, r in race_df.iterrows():
                    d = str(r[drv_col])
                    pos_text = str(_col(r, ['positionText', 'position'], '20'))
                    try:
                        pos = int(pos_text)
                    except Exception:
                        pos = 20
                    recent_form.setdefault(d, []).append(pos)
    except Exception:
        pass

    return d_pts, c_pts, d_con, recent_form


def _build_pred_df(grid_df, d_pts, c_pts, d_con, recent_form):
    rows = []
    for _, row in grid_df.iterrows():
        drv = str(row['driver'])
        con = str(row.get('constructor') or d_con.get(drv, ''))
        grid = _safe_int(row['grid'])
        dp = d_pts.get(drv, 0.0)

        cp = c_pts.get(con, 0.0)
        if cp == 0.0 and con:
            for k, v in c_pts.items():
                if k.lower() in con.lower() or con.lower() in k.lower():
                    cp = v
                    break

        recent = recent_form.get(drv, [])
        rows.append({
            'driver': drv,
            'constructor': con,
            'grid': grid,
            'driver_pts_before': dp,
            'constructor_pts_before': cp,
            'recent_avg_3': float(np.mean(recent[-3:])) if recent else 10.0,
        })
    return pd.DataFrame(rows)


def show_predictions(pred_df, event_name, has_quali):
    st.subheader(f"🔮 {event_name} — Win Probabilities")

    if not has_quali:
        st.info("Qualifying hasn't happened yet — using championship standings order as estimated grid.")

    pred_df = pred_df.sort_values('win_probability', ascending=False).reset_index(drop=True)

    c1, c2, c3 = st.columns(3)
    medals = ["🥇", "🥈", "🥉"]
    for i, col in enumerate([c1, c2, c3]):
        if i >= len(pred_df):
            break
        r = pred_df.iloc[i]
        color = _team_color(r['constructor'])
        with col:
            st.markdown(f"""
<div style="border-left:5px solid {color}; background:#f8f4ff; padding:14px 18px;
            border-radius:8px; margin-bottom:8px;">
  <div style="font-size:1.4rem; font-weight:800;">{medals[i]} {r['driver']}</div>
  <div style="color:#555; font-size:0.88rem; margin-bottom:6px;">{r['constructor']}</div>
  <div style="font-size:1.25rem; color:#6C3DE8; font-weight:700;">{r['win_probability']:.1%} win chance</div>
  <div style="color:#888; font-size:0.82rem; margin-top:3px;">Grid P{int(r['grid'])}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    colors = [_team_color(c) for c in pred_df['constructor']]
    fig = go.Figure(go.Bar(
        x=pred_df['driver'],
        y=pred_df['win_probability'],
        marker_color=colors,
        text=[f"{p:.1%}" for p in pred_df['win_probability']],
        textposition='outside',
        hovertemplate="<b>%{x}</b><br>Win: %{y:.1%}<br>Grid: P%{customdata}<extra></extra>",
        customdata=pred_df['grid'],
    ))
    fig.update_layout(
        title=dict(text="Predicted Win Probability per Driver", font_size=26, x=0.5),
        xaxis_title="Driver",
        yaxis_title="Win Probability",
        yaxis_tickformat=".0%",
        height=460,
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,
        margin=dict(t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Full Rankings")
    tbl = pred_df[['driver', 'constructor', 'grid', 'driver_pts_before', 'recent_avg_3', 'win_probability']].copy()
    tbl.columns = ['Driver', 'Constructor', 'Grid', 'Champ. Points', 'Recent Avg Finish', 'Win Probability']
    tbl['Win Probability'] = tbl['Win Probability'].map(lambda x: f"{x:.2%}")
    tbl['Recent Avg Finish'] = tbl['Recent Avg Finish'].map(lambda x: f"{x:.1f}")
    tbl.index = range(1, len(tbl) + 1)
    st.dataframe(tbl, use_container_width=True)


def show_model_info(model, accuracy, n_races, n_wins, start_year, end_year):
    st.subheader("📊 Model Details")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Test Accuracy", f"{accuracy:.1%}")
    c2.metric("Training Entries", f"{n_races:,}")
    c3.metric("Wins in Data", f"{n_wins:,}")
    c4.metric("Seasons Used", f"{end_year - start_year + 1}")

    try:
        clf = model.named_steps['clf']
        feat_df = pd.DataFrame({
            'Feature': FEATURE_LABELS,
            'Importance': clf.feature_importances_,
        }).sort_values('Importance')

        fig = go.Figure(go.Bar(
            x=feat_df['Importance'],
            y=feat_df['Feature'],
            orientation='h',
            marker_color='#6C3DE8',
            hovertemplate="%{y}: %{x:.3f}<extra></extra>",
        ))
        fig.update_layout(
            title=dict(text="Feature Importance", font_size=22, x=0.5),
            xaxis_title="Importance",
            height=280,
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(t=50, b=30, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass

    st.markdown("""
**Algorithm**: Gradient Boosting Classifier (sklearn)
**Features**: starting grid position, driver championship points, constructor points, recent 3-race average finish position
**Training split**: 80% train / 20% test (chronological — no data leakage)
**Output**: win probability per driver, normalized so all drivers sum to 100%

> Accuracy looks high because wins are rare — the model learns that most drivers don't win.
> The useful signal is the **relative ranking** of win probabilities, not the absolute values.
""")


def main():
    nav_bar()

    st.markdown("# 🔮 Race Winner Predictor")
    st.caption(
        "Gradient boosted trees trained on historical F1 race data — "
        "grid position, championship standings, and recent form."
    )

    with st.sidebar:
        st.header("⚙️ Settings")

        year = st.selectbox("Season", range(CURRENT_YEAR, 2017, -1))

        try:
            schedule = fastf1.get_event_schedule(year, include_testing=False)
            now = pd.Timestamp.utcnow()
            upcoming = schedule[
                schedule['Session5DateUtc'] > (now - pd.Timedelta('4h')).to_datetime64()
            ].set_index('EventName')
            if upcoming.empty:
                upcoming = schedule.set_index('EventName')
        except Exception:
            st.error("Could not load race schedule.")
            credits()
            return

        if upcoming.empty:
            st.warning("No races found for this season.")
            credits()
            return

        event_name = st.selectbox("Race", upcoming.index)
        train_seasons = st.slider(
            "Training data (years back)", 3, 8, 5,
            help="More seasons = richer model but slower first load (results are cached)"
        )

        st.divider()
        credits()

    try:
        full_schedule = fastf1.get_event_schedule(year, include_testing=False)
        round_num = int(
            full_schedule.loc[full_schedule['EventName'] == event_name, 'RoundNumber'].values[0]
        )
    except Exception:
        st.error("Could not determine round number for the selected event.")
        return

    start_year = max(2018, CURRENT_YEAR - train_seasons)
    end_year = CURRENT_YEAR - 1
    if start_year > end_year:
        start_year = end_year = 2024

    with st.spinner(f"Training model on {start_year}–{end_year} data (cached after first load)..."):
        model, features, accuracy, n_races, n_wins = get_trained_model(start_year, end_year)

    if model is None:
        st.error("Not enough historical data to train the model.")
        return

    with st.spinner("Fetching qualifying results..."):
        grid_df, has_quali = get_quali_grid(year, round_num)

    if grid_df.empty:
        with st.spinner("Qualifying not available — loading standings order..."):
            try:
                ergast = Ergast()
                prev = max(1, round_num - 1)
                ds = ergast.get_driver_standings(season=year, round=prev).content[0]
                drv_col = _find_col(ds, ['driverCode', 'Driver.driverCode'])
                con_col = _find_col(ds, ['constructorName', 'Constructor.name', 'constructorNames', 'constructorId', 'constructorIds'])
                grid_df = pd.DataFrame({
                    'driver': ds[drv_col].astype(str) if drv_col else pd.Series(dtype=str),
                    'constructor': ds[con_col].apply(_extract_constructor) if con_col else pd.Series([''] * len(ds)),
                    'grid': range(1, len(ds) + 1),
                })
                has_quali = False
            except Exception:
                st.error("Could not load driver data for prediction.")
                return

    with st.spinner("Fetching current standings..."):
        d_pts, c_pts, d_con, recent_form = get_standings_and_form(year, round_num)

    pred_df = _build_pred_df(grid_df, d_pts, c_pts, d_con, recent_form)

    if pred_df.empty:
        st.error("No prediction data available.")
        return

    X = pred_df[FEATURES].fillna(pred_df[FEATURES].median())
    probs = model.predict_proba(X)[:, 1]
    probs = probs / probs.sum()
    pred_df['win_probability'] = probs

    tab1, tab2 = st.tabs(["🔮 Prediction", "📊 Model Info"])

    with tab1:
        show_predictions(pred_df, event_name, has_quali)

    with tab2:
        show_model_info(model, accuracy, n_races, n_wins, start_year, end_year)


if __name__ == "__main__":
    main()
