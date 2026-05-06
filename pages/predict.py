import streamlit as st
import pandas as pd
import numpy as np
import fastf1
from fastf1.ergast import Ergast
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, brier_score_loss
import plotly.graph_objects as go
from home import nav_bar, credits
from graphs.colors import TEAM_COLORS, CIRCUIT_CHARS, CONSTRUCTOR_CHARS

CURRENT_YEAR = pd.Timestamp.now().year

# 17 features (was 9)
FEATURES = [
    'grid',
    'driver_pts_before',
    'constructor_pts_before',
    'recent_avg_3',
    'recent_avg_5',
    'form_momentum',
    'dnf_rate',
    'circuit_avg_finish',
    'circuit_win_rate',
    'teammate_delta',
    'season_progress',
    'constructor_form_6',
    'circuit_speed',
    'circuit_downforce',
    'circuit_braking',
    'circuit_overtaking',
    'car_circuit_fit',
]

FEATURE_LABELS = [
    'Grid Position',
    'Driver Champ. Points',
    'Constructor Points',
    'Recent Avg Finish (3r)',
    'Recent Avg Finish (5r)',
    'Form Momentum (slope)',
    'DNF Rate',
    'Circuit Hist. Avg Finish',
    'Circuit Hist. Win Rate',
    'Teammate Δ (avg finish)',
    'Season Progress',
    'Constructor Form (6r)',
    'Circuit Speed',
    'Circuit Downforce',
    'Circuit Braking',
    'Circuit Overtaking',
    'Car-Circuit Fit',
]

_DEFAULT_CHARS = (3, 3, 3, 3)


# ── Helpers ──────────────────────────────────────────────────────────────────

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


def _car_circuit_fit(constructor: str, circ_speed: int, circ_downforce: int, circ_braking: int) -> float:
    con_lower = constructor.lower()
    car = next(
        (v for k, v in CONSTRUCTOR_CHARS.items() if k.lower() in con_lower or con_lower in k.lower()),
        None,
    )
    if car is None:
        return 3.0
    car_speed, car_downforce, car_braking, _ = car
    total = circ_speed + circ_downforce + circ_braking or 1
    return (
        (5 - abs(circ_speed - car_speed)) * circ_speed +
        (5 - abs(circ_downforce - car_downforce)) * circ_downforce +
        (5 - abs(circ_braking - car_braking)) * circ_braking
    ) / total


def _team_color(constructor: str) -> str:
    cl = constructor.lower()
    for team, color in TEAM_COLORS.items():
        if team.lower() in cl or cl in team.lower():
            return color
    return '#888888'


def _extract_positions(hist_list: list) -> list:
    """Extract int positions from list that may contain (pos, con) tuples."""
    if not hist_list:
        return []
    return [item[0] if isinstance(item, tuple) else item for item in hist_list]


def _weighted_circ_stats(hist_raw: list, cur_con: str):
    """Circuit avg finish and win rate weighted by car quality ratio (old vs current).
    Discounts results from when the driver was in a much better/worse car."""
    if not hist_raw:
        return 10.0, 0.05
    cur_chars = next(
        (v for k, v in CONSTRUCTOR_CHARS.items()
         if k.lower() in cur_con.lower() or cur_con.lower() in k.lower()),
        _DEFAULT_CHARS,
    )
    cur_q = sum(cur_chars) / len(cur_chars)
    positions, weights = [], []
    for item in hist_raw:
        pos = item[0] if isinstance(item, tuple) else item
        old_con = item[1] if isinstance(item, tuple) else ''
        old_chars = next(
            (v for k, v in CONSTRUCTOR_CHARS.items()
             if old_con and (k.lower() in old_con.lower() or old_con.lower() in k.lower())),
            cur_chars,
        )
        old_q = sum(old_chars) / len(old_chars)
        # Weight ≤ 1.0: if old car was better, result counts less for current car prediction
        weight = min(cur_q / max(old_q, 0.5), 1.0)
        positions.append(pos)
        weights.append(weight)
    total_w = sum(weights) or 1.0
    avg = sum(p * w for p, w in zip(positions, weights)) / total_w
    win_r = sum(w for p, w in zip(positions, weights) if p == 1) / total_w
    return float(avg), float(win_r)


def _form_slope(positions: list) -> float:
    """Linear slope of recent positions. Negative = improving (lower position = better)."""
    if len(positions) < 3:
        return 0.0
    recent = positions[-5:]
    n = len(recent)
    x = np.arange(n, dtype=float)
    return float(np.polyfit(x, recent, 1)[0])


def _make_hgbc():
    """HistGradientBoostingClassifier with class_weight if sklearn >= 1.2, else without."""
    params = dict(max_iter=400, max_depth=4, learning_rate=0.04,
                  min_samples_leaf=8, l2_regularization=0.1, random_state=42)
    try:
        return HistGradientBoostingClassifier(**params, class_weight='balanced')
    except TypeError:
        return HistGradientBoostingClassifier(**params)


def _train_calibrated(X_train, y_train, X_cal, y_cal, weights_train):
    """Train base model then calibrate isotonically on held-out cal set."""
    base = Pipeline([('scaler', StandardScaler()), ('clf', _make_hgbc())])
    base.fit(X_train, y_train, clf__sample_weight=weights_train)
    if y_cal.sum() < 5:
        return base
    try:
        # cv='prefit' requires sklearn >= 0.24
        model = CalibratedClassifierCV(base, method='isotonic', cv='prefit')
        model.fit(X_cal, y_cal)
        return model
    except (TypeError, ValueError):
        return base


# ── Training data ─────────────────────────────────────────────────────────────

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

        try:
            sched = fastf1.get_event_schedule(year, include_testing=False)
            sched = sched.sort_values('RoundNumber')
            circuit_names = [ev['EventName'].replace(' Grand Prix', '') for _, ev in sched.iterrows()]
            chars_by_round = [CIRCUIT_CHARS.get(n, _DEFAULT_CHARS) for n in circuit_names]
        except Exception:
            circuit_names = []
            chars_by_round = []

        total_rounds = max(len(season.content), 1)
        d_pts: dict = {}
        c_pts: dict = {}
        d_recent: dict = {}        # driver -> last-10 finish positions
        d_dnf: dict = {}           # driver -> DNF count
        d_races: dict = {}         # driver -> race count
        d_circ_hist: dict = {}     # (driver, circuit) -> [positions]
        c_recent: dict = {}        # constructor -> last-6 finish positions

        for round_idx, race_df in enumerate(season.content):
            if race_df is None or race_df.empty:
                continue

            circuit_name = circuit_names[round_idx] if round_idx < len(circuit_names) else ''
            circ = chars_by_round[round_idx] if round_idx < len(chars_by_round) else _DEFAULT_CHARS
            season_progress = (round_idx + 1) / total_rounds

            drv_col = _find_col(race_df, ['driverCode', 'Driver.driverCode'])
            con_col = _find_col(race_df, ['constructorName', 'Constructor.name', 'constructorId'])

            # Phase 1 — snapshot pre-race features for every driver
            race_rows = []
            con_to_idx: dict = {}

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
                is_dnf = pos_text in ('R', 'D', 'E', 'W', 'F', 'N')

                recent = d_recent.get(drv, [])
                dnf_c = d_dnf.get(drv, 0)
                race_c = d_races.get(drv, 0)
                circ_hist = d_circ_hist.get((drv, circuit_name), [])
                c_form = c_recent.get(con, [])

                idx = len(race_rows)
                race_rows.append({
                    'year': year,
                    'driver': drv,
                    'constructor': con,
                    'grid': grid,
                    'driver_pts_before': d_pts.get(drv, 0.0),
                    'constructor_pts_before': c_pts.get(con, 0.0),
                    'recent_avg_3': float(np.mean(recent[-3:])) if recent else 10.0,
                    'recent_avg_5': float(np.mean(recent[-5:])) if recent else 10.0,
                    'form_momentum': _form_slope(recent),
                    'dnf_rate': dnf_c / race_c if race_c > 0 else 0.05,
                    'circuit_avg_finish': float(np.mean(circ_hist)) if circ_hist else 10.0,
                    'circuit_win_rate': sum(1 for p in circ_hist if p == 1) / len(circ_hist) if circ_hist else 0.05,
                    'teammate_delta': 0.0,   # filled in phase 2
                    'season_progress': season_progress,
                    'constructor_form_6': float(np.mean(c_form[-6:])) if c_form else 10.0,
                    'circuit_speed': circ[0],
                    'circuit_downforce': circ[1],
                    'circuit_braking': circ[2],
                    'circuit_overtaking': circ[3],
                    'car_circuit_fit': _car_circuit_fit(con, circ[0], circ[1], circ[2]),
                    'won': 1 if pos == 1 else 0,
                    'podium': 1 if pos <= 3 else 0,
                    '_pos': pos,
                    '_pts': pts,
                    '_is_dnf': is_dnf,
                })
                con_to_idx.setdefault(con, []).append(idx)

            # Phase 2 — teammate delta (uses pre-race recent_avg_3 of all drivers in same car)
            for con, idxs in con_to_idx.items():
                if len(idxs) < 2:
                    continue
                for i in idxs:
                    my_avg = race_rows[i]['recent_avg_3']
                    mate_avg = float(np.mean([race_rows[j]['recent_avg_3'] for j in idxs if j != i]))
                    race_rows[i]['teammate_delta'] = my_avg - mate_avg

            rows.extend(race_rows)

            # Phase 3 — update rolling state for next round
            for r in race_rows:
                drv, con = r['driver'], r['constructor']
                pos, pts = r['_pos'], r['_pts']
                d_pts[drv] = d_pts.get(drv, 0.0) + pts
                c_pts[con] = c_pts.get(con, 0.0) + pts
                d_recent[drv] = (d_recent.get(drv, []) + [pos])[-10:]
                d_races[drv] = d_races.get(drv, 0) + 1
                if r['_is_dnf']:
                    d_dnf[drv] = d_dnf.get(drv, 0) + 1
                if circuit_name:
                    d_circ_hist[(drv, circuit_name)] = d_circ_hist.get((drv, circuit_name), []) + [pos]
                c_recent[con] = (c_recent.get(con, []) + [pos])[-6:]

    df = pd.DataFrame(rows)
    return df.drop(columns=[c for c in ['_pos', '_pts', '_is_dnf'] if c in df.columns])


# ── Model training ────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_trained_model(start_year: int, end_year: int):
    """Returns (win_model, pod_model, feature_cols, win_auc, pod_auc, win_brier, n_rows, n_wins)."""
    df = build_training_data(start_year, end_year)
    if df.empty or df['won'].sum() < 10:
        return None, None, FEATURES, 0.5, 0.6, 0.05, 0, 0

    feature_cols = [f for f in FEATURES if f in df.columns]
    X = df[feature_cols].copy()
    X = X.fillna(X.median())

    # Temporal 70 / 15 / 15 split — no data leakage
    n = len(df)
    i_train = int(n * 0.70)
    i_cal = int(n * 0.85)

    X_train = X.iloc[:i_train]
    X_cal = X.iloc[i_train:i_cal]
    X_test = X.iloc[i_cal:]

    year_range = max(end_year - start_year, 1)
    weights_train = 1.0 + (df['year'].iloc[:i_train] - start_year) / year_range

    y_win_train = df['won'].iloc[:i_train]
    y_win_cal = df['won'].iloc[i_train:i_cal]
    y_win_test = df['won'].iloc[i_cal:]

    y_pod_train = df['podium'].iloc[:i_train]
    y_pod_cal = df['podium'].iloc[i_train:i_cal]
    y_pod_test = df['podium'].iloc[i_cal:]

    win_model = _train_calibrated(X_train, y_win_train, X_cal, y_win_cal, weights_train)
    pod_model = _train_calibrated(X_train, y_pod_train, X_cal, y_pod_cal, weights_train)

    win_auc, win_brier = 0.5, 0.05
    pod_auc = 0.6
    if y_win_test.sum() > 0:
        p_win = win_model.predict_proba(X_test)[:, 1]
        win_auc = float(roc_auc_score(y_win_test, p_win))
        win_brier = float(brier_score_loss(y_win_test, p_win))
    if y_pod_test.sum() > 0:
        p_pod = pod_model.predict_proba(X_test)[:, 1]
        pod_auc = float(roc_auc_score(y_pod_test, p_pod))

    return win_model, pod_model, feature_cols, win_auc, pod_auc, win_brier, len(df), int(df['won'].sum())


# ── Qualifying / standings fetchers ──────────────────────────────────────────

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

        return pd.DataFrame({
            'driver': df[drv_col].astype(str),
            'constructor': df[con_col].apply(_extract_constructor) if con_col else [''] * len(df),
            'grid': pd.to_numeric(df[pos_col], errors='coerce').fillna(20).astype(int),
        }), True
    except Exception:
        return pd.DataFrame(), False


@st.cache_data(persist=True, show_spinner=False)
def get_standings_and_form(year: int, round_num: int):
    """Returns (d_pts, c_pts, d_con, recent_form, circuit_hist, dnf_info, con_recent, recent_gaps, recent_pts, total_rounds)."""
    ergast = Ergast()
    d_pts: dict = {}
    c_pts: dict = {}
    d_con: dict = {}
    recent_form: dict = {}
    circuit_hist: dict = {}    # (driver, circuit_name) -> [positions]
    dnf_info: dict = {}        # driver -> [dnf_count, race_count]
    con_recent: dict = {}      # constructor -> [last-6 positions]
    recent_gaps: dict = {}     # driver -> [gap-to-winner in seconds per race]
    recent_pts: dict = {}      # driver -> [points per race]
    total_rounds = 24
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
        cc = _find_col(cs, ['constructorName', 'Constructor.name', 'constructorId'])
        pc = _find_col(cs, ['points', 'Points'])
        if cc:
            for _, r in cs.iterrows():
                c_pts[str(r[cc])] = _safe_float(r.get(pc or 'points', 0))
    except Exception:
        pass

    circuit_names_sched: list = []
    try:
        sched = fastf1.get_event_schedule(year, include_testing=False)
        sched = sched.sort_values('RoundNumber')
        circuit_names_sched = [ev['EventName'].replace(' Grand Prix', '') for _, ev in sched.iterrows()]
        total_rounds = len(sched)
    except Exception:
        pass

    try:
        season = ergast.get_race_results(season=year)
        if season and season.content:
            for race_idx, race_df in enumerate(season.content[:prev]):
                if race_df is None or race_df.empty:
                    continue
                drv_col = _find_col(race_df, ['driverCode', 'Driver.driverCode'])
                con_col = _find_col(race_df, ['constructorName', 'Constructor.name', 'constructorId'])
                if not drv_col:
                    continue

                circuit_name = circuit_names_sched[race_idx] if race_idx < len(circuit_names_sched) else ''
                time_col = _find_col(race_df, ['time', 'Time'])

                for _, r in race_df.iterrows():
                    d = str(r[drv_col])
                    pos_text = str(_col(r, ['positionText', 'position'], '20'))
                    try:
                        pos = int(pos_text)
                    except Exception:
                        pos = 20
                    is_dnf = pos_text in ('R', 'D', 'E', 'W', 'F', 'N')

                    # Gap-to-winner in seconds (winner = 0, DNF = 999)
                    gap_s = 0.0
                    if pos != 1:
                        if is_dnf:
                            gap_s = 999.0
                        elif time_col:
                            try:
                                tv = r.get(time_col)
                                if tv is not None and hasattr(tv, 'total_seconds') and not pd.isna(tv):
                                    ts = abs(tv.total_seconds())
                                    gap_s = ts if 0 < ts < 300 else float((pos - 1) * 8)
                                else:
                                    gap_s = float((pos - 1) * 8)
                            except Exception:
                                gap_s = float((pos - 1) * 8)
                        else:
                            gap_s = float((pos - 1) * 8)

                    race_pts = _safe_float(_col(r, ['points'], 0))
                    recent_form.setdefault(d, []).append(pos)
                    recent_gaps.setdefault(d, []).append(gap_s)
                    recent_pts.setdefault(d, []).append(race_pts)
                    if circuit_name:
                        circuit_hist.setdefault((d, circuit_name), []).append(pos)
                    if d not in dnf_info:
                        dnf_info[d] = [0, 0]
                    dnf_info[d][1] += 1
                    if is_dnf:
                        dnf_info[d][0] += 1

                    if con_col:
                        con = str(_col(r, [con_col], ''))
                        con_recent.setdefault(con, []).append(pos)
                        con_recent[con] = con_recent[con][-6:]
    except Exception:
        pass

    return d_pts, c_pts, d_con, recent_form, circuit_hist, dnf_info, con_recent, recent_gaps, recent_pts, total_rounds


@st.cache_data(persist=True, show_spinner=False)
def get_circuit_history(circuit_name: str, current_year: int, years_back: int = 6):
    """Multi-year results for one circuit. Returns driver -> [finish positions]."""
    ergast = Ergast()
    hist: dict = {}
    for y in range(max(2018, current_year - years_back), current_year):
        try:
            sched = fastf1.get_event_schedule(y, include_testing=False)
            name_col = 'EventName'
            short_names = sched[name_col].str.replace(' Grand Prix', '', regex=False).str.strip()
            mask = short_names == circuit_name.strip()
            if not mask.any():
                mask = short_names.str.contains(circuit_name.strip(), case=False, na=False)
            if not mask.any():
                continue
            rn = int(sched.loc[mask, 'RoundNumber'].iloc[0])
            result = ergast.get_race_results(season=y, round=rn)
            if not result or not result.content:
                continue
            race_df = result.content[0]
            drv_col = _find_col(race_df, ['driverCode', 'Driver.driverCode'])
            con_col_h = _find_col(race_df, ['constructorName', 'Constructor.name', 'constructorId'])
            if not drv_col:
                continue
            for _, r in race_df.iterrows():
                d = str(r[drv_col])
                pos_text = str(_col(r, ['positionText', 'position'], '20'))
                try:
                    pos = int(pos_text)
                except Exception:
                    pos = 20
                con_name = str(_col(r, [con_col_h] if con_col_h else [], ''))
                hist.setdefault(d, []).append((pos, con_name))
        except Exception:
            continue
    return hist


# ── Prediction dataframe builder ──────────────────────────────────────────────

def _build_pred_df(grid_df, d_pts, c_pts, d_con, recent_form,
                   circuit_chars=_DEFAULT_CHARS, circuit_name='',
                   circuit_hist=None, dnf_info=None, con_recent=None,
                   recent_gaps=None, circuit_hist_multi=None,
                   recent_pts=None, round_num=1, total_rounds=24):
    circuit_hist = circuit_hist or {}
    dnf_info = dnf_info or {}
    con_recent = con_recent or {}
    recent_gaps = recent_gaps or {}
    circuit_hist_multi = circuit_hist_multi or {}
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
        di = dnf_info.get(drv, [0, 0])

        # Circuit history: prefer multi-year lookup (with con info), fall back to current-year
        circ_hist_raw = circuit_hist_multi.get(drv, []) or circuit_hist.get((drv, circuit_name), [])
        circ_avg_finish, circ_win_rate = _weighted_circ_stats(circ_hist_raw, con)
        circ_positions = _extract_positions(circ_hist_raw)

        c_form = con_recent.get(con, [])
        if not c_form and con:
            for k, v in con_recent.items():
                if k.lower() in con.lower() or con.lower() in k.lower():
                    c_form = v
                    break

        gaps = recent_gaps.get(drv, [])
        valid_gaps = [g for g in gaps if g < 300]
        r_pts = (recent_pts or {}).get(drv, [])

        rows.append({
            'driver': drv,
            'constructor': con,
            'grid': grid,
            'driver_pts_before': dp,
            'constructor_pts_before': cp,
            'recent_avg_3': float(np.mean(recent[-3:])) if recent else 10.0,
            'recent_avg_5': float(np.mean(recent[-5:])) if recent else 10.0,
            'form_momentum': _form_slope(recent),
            'dnf_rate': di[0] / di[1] if di[1] > 0 else 0.05,
            'circuit_avg_finish': circ_avg_finish,
            'circuit_win_rate': circ_win_rate,
            'teammate_delta': 0.0,
            'season_progress': round_num / max(total_rounds, 1),
            'constructor_form_6': float(np.mean(c_form[-6:])) if c_form else 10.0,
            'circuit_speed': circuit_chars[0],
            'circuit_downforce': circuit_chars[1],
            'circuit_braking': circuit_chars[2],
            'circuit_overtaking': circuit_chars[3],
            'car_circuit_fit': _car_circuit_fit(con, circuit_chars[0], circuit_chars[1], circuit_chars[2]),
            # Display-only stats (not model features)
            'gap_avg_3': float(np.mean(valid_gaps[-3:])) if valid_gaps else -1.0,
            'gap_avg_5': float(np.mean(valid_gaps[-5:])) if valid_gaps else -1.0,
            'pts_avg_3': float(np.mean(r_pts[-3:])) if r_pts else -1.0,
            'pts_avg_5': float(np.mean(r_pts[-5:])) if r_pts else -1.0,
            '_circ_hist': circ_positions,
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Teammate delta — mean finish delta vs others on same constructor
    def _mate_delta(row):
        same = df[df['constructor'] == row['constructor']]
        others = same.loc[same.index != row.name, 'recent_avg_3']
        return float(row['recent_avg_3'] - others.mean()) if not others.empty else 0.0

    df['teammate_delta'] = df.apply(_mate_delta, axis=1)

    # Blend static car_circuit_fit with actual constructor gap to leader this season.
    # Prevents static CONSTRUCTOR_CHARS from over/under-rating teams that changed form.
    df['con_avg_gap'] = -1.0
    if recent_gaps:
        con_gap_data: dict = {}
        for _, prow in df.iterrows():
            g_list = (recent_gaps or {}).get(prow['driver'], [])
            valid_g = [g for g in g_list[-6:] if g < 300]
            if valid_g:
                con_gap_data.setdefault(prow['constructor'], []).extend(valid_g)

        if con_gap_data:
            con_mean_gap = {c: float(np.mean(gs)) for c, gs in con_gap_data.items() if gs}
            gap_vals = list(con_mean_gap.values())
            gmin, gmax = min(gap_vals), max(gap_vals)
            grange = max(gmax - gmin, 1.0)

            def _adj_fit(prow):
                c = prow['constructor']
                sf = prow['car_circuit_fit']
                if c not in con_mean_gap:
                    return sf
                norm = 1.0 - (con_mean_gap[c] - gmin) / grange  # 0=worst, 1=best
                dyn = 1.0 + norm * 4.0  # 1–5 scale
                return 0.4 * sf + 0.6 * dyn

            df['car_circuit_fit'] = df.apply(_adj_fit, axis=1)
            df['con_avg_gap'] = df['constructor'].map(lambda c: con_mean_gap.get(c, -1.0))

    return df


# ── Visualisation helpers ─────────────────────────────────────────────────────

def _form_delta(row) -> float:
    """Positive = improving. Primary signal: pts_avg_3 > pts_avg_5 (scoring more lately).
    Falls back to gap-to-winner delta, then position delta."""
    p3 = float(row.get('pts_avg_3', -1.0))
    p5 = float(row.get('pts_avg_5', -1.0))
    if p3 >= 0 and p5 >= 0:
        return p3 - p5  # pts: positive = scoring more recently = improving
    g3 = float(row.get('gap_avg_3', -1.0))
    g5 = float(row.get('gap_avg_5', -1.0))
    if g3 >= 0 and g5 >= 0:
        return (g5 - g3) / 4.0  # scale seconds → ~points range
    r3 = float(row.get('recent_avg_3', 10.0))
    r5 = float(row.get('recent_avg_5', 10.0))
    return (r5 - r3) * 0.5  # scale positions → ~points range


def _form_arrow(delta: float) -> str:
    if delta > 5.0:
        return "↑↑"
    if delta > 2.0:
        return "↑"
    if delta < -5.0:
        return "↓↓"
    if delta < -2.0:
        return "↓"
    return "→"


def _form_color(delta: float) -> str:
    if delta > 2.0:
        return "#22aa44"
    if delta < -2.0:
        return "#cc3322"
    return "#888888"


def _pred_X(pred_df, feature_cols):
    X = pd.DataFrame(index=pred_df.index, columns=feature_cols, dtype=float)
    for col in feature_cols:
        if col in pred_df.columns:
            X[col] = pred_df[col].astype(float)
        else:
            X[col] = 0.0
    return X.fillna(X.median())


# ── Page renders ──────────────────────────────────────────────────────────────

def show_predictions(pred_df, event_name, has_quali, circuit_hist_multi=None):
    st.subheader(f"🔮 {event_name} — Predictions")

    if not has_quali:
        st.info("Qualifying hasn't happened yet — using championship standings order as estimated grid.")

    pred_df = pred_df.sort_values('win_probability', ascending=False).reset_index(drop=True)

    # Top-3 podium cards
    c1, c2, c3 = st.columns(3)
    medals = ["🥇", "🥈", "🥉"]
    for i, col in enumerate([c1, c2, c3]):
        if i >= len(pred_df):
            break
        r = pred_df.iloc[i]
        color = _team_color(r['constructor'])
        delta = _form_delta(r)
        arrow = _form_arrow(delta)
        arrow_color = _form_color(delta)
        circ_hist_list = _extract_positions((circuit_hist_multi or {}).get(r['driver'], []))
        circ_info = f"Best here (last 6y): P{int(min(circ_hist_list))}, avg P{np.mean(circ_hist_list):.1f}" if circ_hist_list else "No prior history at this circuit"
        pod_pct = r.get('podium_probability', r['win_probability'] * 3)

        with col:
            st.markdown(f"""
                <div style="border-left:5px solid {color}; background:#f8f4ff; padding:14px 18px;
                            border-radius:8px; margin-bottom:8px;">
                  <div style="font-size:1.4rem; font-weight:800;">{medals[i]} {r['driver']}</div>
                  <div style="color:#555; font-size:0.88rem; margin-bottom:6px;">{r['constructor']}</div>
                  <div style="font-size:1.2rem; color:#6C3DE8; font-weight:700;">{r['win_probability']:.1%} win chance</div>
                  <div style="font-size:0.95rem; color:#9b59b6; font-weight:600;">{min(pod_pct, 1.0):.1%} podium chance</div>
                  <div style="color:#888; font-size:0.82rem; margin-top:4px;">
                    Grid P{int(r['grid'])} &nbsp;·&nbsp;
                    Form <span style="color:{arrow_color}; font-weight:bold;">{arrow}</span>
                  </div>
                  <div style="color:#aaa; font-size:0.78rem; margin-top:2px;">{circ_info}</div>
                </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Dual bar chart: win + podium probability
    colors = [_team_color(c) for c in pred_df['constructor']]
    driver_labels = [
        f"{r['driver']} {_form_arrow(_form_delta(r))}"
        for _, r in pred_df.iterrows()
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Win %',
        x=driver_labels,
        y=pred_df['win_probability'],
        marker_color=colors,
        text=[f"{p:.1%}" for p in pred_df['win_probability']],
        textposition='outside',
        hovertemplate="<b>%{x}</b><br>Win: %{y:.1%}<br>Grid: P%{customdata[0]}<br>Circuit hist avg: P%{customdata[1]:.1f}<extra></extra>",
        customdata=list(zip(pred_df['grid'], pred_df['circuit_avg_finish'])),
    ))
    if 'podium_probability' in pred_df.columns:
        fig.add_trace(go.Bar(
            name='Podium %',
            x=driver_labels,
            y=pred_df['podium_probability'],
            marker_color=colors,
            marker_line_color=colors,
            marker_line_width=1.5,
            opacity=0.45,
            text=[f"{p:.1%}" for p in pred_df['podium_probability']],
            textposition='outside',
            hovertemplate="<b>%{x}</b><br>Podium: %{y:.1%}<extra></extra>",
        ))
    fig.update_layout(
        barmode='group',
        title=dict(text="Win & Podium Probabilities", font_size=24, x=0.5),
        xaxis_title="Driver",
        yaxis_title="Probability",
        yaxis_tickformat=".0%",
        height=480,
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', y=1.05, x=0.5, xanchor='center'),
        margin=dict(t=80, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Full table
    st.subheader("Full Rankings")
    tbl = pred_df[['driver', 'constructor', 'grid', 'driver_pts_before',
                    'recent_avg_3', 'circuit_avg_finish', 'dnf_rate',
                    'form_momentum', 'win_probability']].copy()
    if 'podium_probability' in pred_df.columns:
        tbl['podium_probability'] = pred_df['podium_probability']

    tbl['Form'] = [_form_arrow(_form_delta(pred_df.iloc[i])) for i in range(len(pred_df))]
    tbl.drop(columns=['form_momentum'], inplace=True)

    rename = {
        'driver': 'Driver', 'constructor': 'Constructor', 'grid': 'Grid',
        'driver_pts_before': 'Pts (before)', 'recent_avg_3': 'Avg Finish (3r)',
        'circuit_avg_finish': 'Circuit Hist.', 'dnf_rate': 'DNF Rate',
        'win_probability': 'Win Prob.', 'podium_probability': 'Podium Prob.',
    }
    tbl.rename(columns=rename, inplace=True)
    tbl['Win Prob.'] = tbl['Win Prob.'].map(lambda x: f"{x:.2%}")
    if 'Podium Prob.' in tbl.columns:
        tbl['Podium Prob.'] = tbl['Podium Prob.'].map(lambda x: f"{x:.2%}")
    tbl['Avg Finish (3r)'] = tbl['Avg Finish (3r)'].map(lambda x: f"{x:.1f}")
    tbl['Circuit Hist.'] = tbl['Circuit Hist.'].map(lambda x: f"P{x:.1f}" if x < 19.9 else "—")
    tbl['DNF Rate'] = tbl['DNF Rate'].map(lambda x: f"{x:.0%}")
    tbl.index = range(1, len(tbl) + 1)
    st.dataframe(tbl, use_container_width=True)

    # Per-driver score explanation
    with st.expander("🔍 Driver Score Breakdown"):
        for _, r in pred_df.iterrows():
            color = _team_color(r['constructor'])
            delta = _form_delta(r)
            g = int(r['grid'])

            grid_label = (
                "Pole position — maximum grid advantage" if g == 1 else
                f"P{g} — front row" if g == 2 else
                f"P{g} — top 3 start" if g <= 3 else
                f"P{g} — top 5" if g <= 5 else
                f"P{g} — top 10" if g <= 10 else
                f"P{g} — midfield" if g <= 15 else
                f"P{g} — back of grid"
            )

            p3 = float(r.get('pts_avg_3', -1.0))
            p5 = float(r.get('pts_avg_5', -1.0))
            g3 = float(r.get('gap_avg_3', -1.0))
            g5 = float(r.get('gap_avg_5', -1.0))
            r3 = float(r.get('recent_avg_3', 10.0))
            trend_word = (
                "strong upswing" if delta > 5 else
                "improving" if delta > 2 else
                "sharp decline" if delta < -5 else
                "declining" if delta < -2 else
                "stable"
            )
            if p3 >= 0 and p5 >= 0:
                form_label = f"Avg pts: last 3r = {p3:.1f}, last 5r = {p5:.1f} — {trend_word}"
            elif g3 >= 0 and g5 >= 0:
                form_label = f"Avg gap to leader: last 3r = +{g3:.1f}s, last 5r = +{g5:.1f}s — {trend_word}"
            else:
                form_label = f"Avg P{r3:.1f} finish in last 3 races — {trend_word}"

            ca = float(r.get('circuit_avg_finish', -1.0))
            cw = float(r.get('circuit_win_rate', 0.05))
            circ_hist_list = _extract_positions((circuit_hist_multi or {}).get(r['driver'], []))
            if circ_hist_list:
                best = int(min(circ_hist_list))
                wins = sum(1 for p in circ_hist_list if p == 1)
                circ_label = f"Avg P{np.mean(circ_hist_list):.1f}, best P{best}, {wins} win(s) in {len(circ_hist_list)} race(s) here"
            else:
                circ_label = "No prior races at this circuit"

            dnf = float(r.get('dnf_rate', 0.05))
            dnf_label = (
                f"{dnf:.0%} DNF rate — " +
                ("low reliability risk" if dnf < 0.07 else
                 "moderate reliability risk" if dnf < 0.15 else
                 "high reliability risk")
            )

            fit = float(r.get('car_circuit_fit', 3.0))
            con_gap = float(r.get('con_avg_gap', -1.0))
            fit_quality = ("excellent match" if fit >= 4.0 else
                           "good match" if fit >= 3.2 else
                           "average match" if fit >= 2.5 else
                           "poor match")
            if con_gap >= 0:
                fit_label = f"{fit:.1f}/5.0 — {fit_quality} (adjusted from static chars + {con_gap:.1f}s avg gap to leader this season)"
            else:
                fit_label = f"{fit:.1f}/5.0 — {fit_quality}"

            mate = float(r.get('teammate_delta', 0.0))
            mate_label = (
                f"{abs(mate):.1f} pos {'ahead of' if mate < 0 else 'behind'} teammate on avg"
                if abs(mate) > 0.3 else "similar pace to teammate"
            )

            pod_pct = r.get('podium_probability', r['win_probability'] * 3)
            st.markdown(f"""
<div style="border-left:4px solid {color}; padding:8px 14px; margin:6px 0;
            background:#fafafa; border-radius:5px;">
  <b style="font-size:1rem;">{r['driver']}</b>
  <span style="color:#555; font-size:0.85rem;"> · {r['constructor']}</span>
  &nbsp;
  <span style="color:#6C3DE8; font-weight:700;">{r['win_probability']:.1%} win</span>
  <span style="color:#9b59b6; font-size:0.9rem;"> · {min(float(pod_pct), 1.0):.1%} podium</span>
  <ul style="margin:5px 0 2px 0; font-size:0.82rem; color:#444; line-height:1.7;">
    <li>🏁 <b>Grid:</b> {grid_label}</li>
    <li>📈 <b>Form:</b> {form_label} {_form_arrow(delta)}</li>
    <li>🗺️ <b>Circuit history:</b> {circ_label}</li>
    <li>🔧 <b>Car-circuit fit:</b> {fit_label}</li>
    <li>👥 <b>vs Teammate:</b> {mate_label}</li>
    <li>⚠️ <b>Reliability:</b> {dnf_label}</li>
  </ul>
</div>""", unsafe_allow_html=True)


def show_model_info(win_model, pod_model, win_auc, pod_auc, win_brier,
                    n_races, n_wins, start_year, end_year, feature_cols):
    st.subheader("📊 Model Details")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Win AUC-ROC", f"{win_auc:.3f}",
              help="0.5 = random, 1.0 = perfect. Win prediction is good above ~0.80.")
    c2.metric("Podium AUC-ROC", f"{pod_auc:.3f}",
              help="Podium (top-3) prediction quality.")
    c3.metric("Brier Score", f"{win_brier:.4f}",
              help="Calibration quality — lower is better.")
    c4.metric("Training Rows", f"{n_races:,}")
    c5.metric("Seasons Used", f"{end_year - start_year + 1}")

    # Feature importances from the win model
    try:
        cal_clf = win_model.calibrated_classifiers_[0]
        base_pipeline = cal_clf.estimator
        clf = base_pipeline.named_steps['clf']
        importances = clf.feature_importances_
    except Exception:
        try:
            clf = win_model.named_steps['clf']
            importances = clf.feature_importances_
        except Exception:
            importances = None

    if importances is not None:
        labels = []
        for f in feature_cols:
            try:
                labels.append(FEATURE_LABELS[FEATURES.index(f)])
            except (ValueError, IndexError):
                labels.append(f)

        feat_df = pd.DataFrame({'Feature': labels, 'Importance': importances}).sort_values('Importance')
        fig = go.Figure(go.Bar(
            x=feat_df['Importance'],
            y=feat_df['Feature'],
            orientation='h',
            marker_color='#6C3DE8',
            hovertemplate="%{y}: %{x:.4f}<extra></extra>",
        ))
        fig.update_layout(
            title=dict(text="Win Model — Feature Importance", font_size=20, x=0.5),
            xaxis_title="Importance",
            height=max(320, len(feat_df) * 22),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(t=50, b=30, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"""
**Algorithm**: Histogram Gradient Boosting (sklearn) + Isotonic Calibration
**Features**: {len(feature_cols)} — grid position, championship points, form slope (5r), circuit history, DNF rate, teammate comparison, season progress, constructor rolling form
**Training split**: 70% train / 15% calibrate / 15% test (chronological — no data leakage)
**Class balancing**: `class_weight='balanced'` — corrects for ~5% win base rate
**Output**: Calibrated win & podium probabilities per driver, each normalised to 100%

> **AUC-ROC {win_auc:.3f}**: Separates winners from non-winners (0.5 = coin flip, 1.0 = perfect).
> **Brier {win_brier:.4f}**: Probability calibration error — lower means tighter, more trustworthy probabilities.
> Relative ranking matters more than absolute values — use the probability order, not the raw numbers.
    """)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    nav_bar()

    st.markdown("# 🔮 Race Winner Predictor")
    st.caption(
        "Calibrated gradient boosting trained on historical F1 data — "
        "grid position, championship standings, form momentum, circuit history, and more."
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

    with st.spinner(f"Training models on {start_year}–{end_year} data (cached after first load)..."):
        win_model, pod_model, feature_cols, win_auc, pod_auc, win_brier, n_races, n_wins = \
            get_trained_model(start_year, end_year)

    if win_model is None:
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

    with st.spinner("Fetching standings, gap data and form..."):
        d_pts, c_pts, d_con, recent_form, circuit_hist, dnf_info, con_recent, recent_gaps, recent_pts, total_rounds = \
            get_standings_and_form(year, round_num)

    event_short = event_name.replace(' Grand Prix', '')

    with st.spinner(f"Loading {event_short} circuit history (last 6 seasons)..."):
        circuit_hist_multi = get_circuit_history(event_short, year)

    circuit_chars = CIRCUIT_CHARS.get(event_short, _DEFAULT_CHARS)
    pred_df = _build_pred_df(
        grid_df, d_pts, c_pts, d_con, recent_form, circuit_chars,
        circuit_name=event_short, circuit_hist=circuit_hist,
        dnf_info=dnf_info, con_recent=con_recent,
        recent_gaps=recent_gaps, circuit_hist_multi=circuit_hist_multi,
        recent_pts=recent_pts,
        round_num=round_num, total_rounds=total_rounds,
    )

    if pred_df.empty:
        st.error("No prediction data available.")
        return

    X = _pred_X(pred_df, feature_cols)

    win_probs = win_model.predict_proba(X)[:, 1]
    win_probs = win_probs / win_probs.sum()
    pred_df['win_probability'] = win_probs

    if pod_model is not None:
        pod_probs = pod_model.predict_proba(X)[:, 1]
        pod_probs = pod_probs / pod_probs.sum()
        pred_df['podium_probability'] = pod_probs

    tab1, tab2 = st.tabs(["🔮 Prediction", "📊 Model Info"])

    with tab1:
        show_predictions(pred_df, event_name, has_quali,
                         circuit_hist_multi=circuit_hist_multi)

    with tab2:
        show_model_info(win_model, pod_model, win_auc, pod_auc, win_brier,
                        n_races, n_wins, start_year, end_year, feature_cols)


if __name__ == "__main__":
    main()
