# python -m streamlit run ./home.py

import streamlit as st

def set_streamlit_page_config_once():
    try:
        st.set_page_config(page_title="F1 Consulting", page_icon="🏎", layout="wide")
    except st.errors.StreamlitAPIException as e:
        if "can only be called once per app" in e.__str__(): return
        raise e

# ── Global CSS ──────────────────────────────────────────────────────────────
_CSS = """
<style>
/* Push content below Streamlit's fixed top toolbar.
   Covers the selector used across different Streamlit 1.x versions. */
.block-container,
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"],
section[data-testid="stMain"] > div:first-child {
    padding-top: 5rem !important;
}
</style>
"""

def nav_bar():
    set_streamlit_page_config_once()
    st.markdown(_CSS, unsafe_allow_html=True)
    st.header("F1 CONSULTING", divider="rainbow")
    cols = st.columns(8)
    cols[0].page_link("home.py",              label="**Home**",     icon="🏡")
    cols[1].page_link("pages/sessions.py",    label="**Sessions**", icon="🏎")
    cols[2].page_link("pages/teams.py",       label="**Teams**",    icon="🏗️")
    cols[3].page_link("pages/drivers.py",     label="**Drivers**",  icon="🙍")
    cols[4].page_link("pages/seasons.py",     label="**Seasons**",  icon="📅")
    cols[5].page_link("pages/circuits.py",    label="**Circuits**", icon="🏁")
    cols[6].page_link("pages/predict.py",     label="**Predict**",  icon="🔮")
    cols[7].page_link("pages/contact.py",     label="**Contact**",  icon="📞")

def credits():
    st.title("📜 Credits")
    st.info(
        """
        Developed by **Leandro Fabre**

        [**LinkedIn**](https://linkedin.com/in/leandrofabre) · [**GitHub**](https://github.com/Lelozitos) · [**Email**](mailto:lm.fabre@hotmail.com)

        Special thanks to the Formula 1 data community.
        """
    )
    st.info("**App Version** v0.9.0")

# ── Hero ────────────────────────────────────────────────────────────────────
# Uses the app's own purple (#6C3DE8) so the gradient always renders correctly
# in light mode. All colours carry !important to beat Streamlit's textColor.
_HERO_HTML = """
<div style="
    background: linear-gradient(135deg, #4A1FB8 0%, #6C3DE8 45%, #9B1FE8 100%) !important;
    border-radius: 12px;
    padding: 44px 48px 36px 48px;
    margin: 2px 0 12px 0;
    border-left: 6px solid #E8002D;
    position: relative;
">
  <!-- chequered-flag accent strip (right edge) -->
  <div style="
      position: absolute; top: 0; right: 0; width: 200px; height: 100%;
      background: repeating-conic-gradient(rgba(255,255,255,0.06) 0% 25%, transparent 0% 50%)
                  0 0 / 20px 20px;
      border-radius: 0 12px 12px 0;
      pointer-events: none;
  "></div>

  <div style="display:flex; align-items:center; gap:18px; margin-bottom:20px;">
    <span style="font-size:3rem; line-height:1; filter:drop-shadow(0 2px 4px rgba(0,0,0,0.3));">🏎</span>
    <div>
      <h1 style="color:#FFFFFF !important; font-size:2.5rem !important; font-weight:900 !important;
                 margin:0 !important; letter-spacing:0.07em; text-transform:uppercase;
                 text-shadow: 0 2px 8px rgba(0,0,0,0.35);">
        F1 Consulting
      </h1>
      <p style="color:rgba(255,255,255,0.82) !important; font-size:1.05rem !important;
                margin:6px 0 0 0 !important;">
        Data-driven insights — from raw telemetry to championship standings
      </p>
    </div>
  </div>

  <!-- stat badges -->
  <div style="display:flex; flex-wrap:wrap; gap:12px; margin-top:24px;">
    <div style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.25);
                border-radius:8px; padding:10px 20px; text-align:center; min-width:80px;">
      <div style="color:#FFD700 !important; font-size:1.65rem !important; font-weight:800 !important;
                  line-height:1.15;">15+</div>
      <div style="color:rgba(255,255,255,0.80) !important; font-size:0.75rem !important;
                  margin-top:2px;">Visualizations</div>
    </div>
    <div style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.25);
                border-radius:8px; padding:10px 20px; text-align:center; min-width:80px;">
      <div style="color:#FFD700 !important; font-size:1.65rem !important; font-weight:800 !important;
                  line-height:1.15;">2018–2026</div>
      <div style="color:rgba(255,255,255,0.80) !important; font-size:0.75rem !important;
                  margin-top:2px;">Season Data</div>
    </div>
    <div style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.25);
                border-radius:8px; padding:10px 20px; text-align:center; min-width:80px;">
      <div style="color:#FFD700 !important; font-size:1.65rem !important; font-weight:800 !important;
                  line-height:1.15;">20+</div>
      <div style="color:rgba(255,255,255,0.80) !important; font-size:0.75rem !important;
                  margin-top:2px;">Circuits</div>
    </div>
    <div style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.25);
                border-radius:8px; padding:10px 20px; text-align:center; min-width:80px;">
      <div style="color:#FFD700 !important; font-size:1.65rem !important; font-weight:800 !important;
                  line-height:1.15;">3</div>
      <div style="color:rgba(255,255,255,0.80) !important; font-size:0.75rem !important;
                  margin-top:2px;">Data Sources</div>
    </div>
  </div>
</div>
"""

# ── Feature card data: (name, icon, accent_color, page, short_desc) ─────────
_FEATURES = [
    ("Sessions",  "🏎",  "#E8002D",  "pages/sessions.py",
     "Telemetry, tyre strategies, race positions, engine clipping, launch analysis, weather & wind."),
    ("Teams",     "🏗️",  "#3671C6",  "pages/teams.py",
     "Constructor standings with team colors, points progression chart, and car & logo previews."),
    ("Drivers",   "🙍",  "#FF8000",  "pages/drivers.py",
     "Driver standings with title-chance analysis, team colors, and per-race points heatmap."),
    ("Seasons",   "📅",  "#229971",  "pages/seasons.py",
     "Full season overview with race-by-race points heatmap across an entire championship year."),
    ("Circuits",  "🏁",  "#6C3DE8",  "pages/circuits.py",
     "Season calendar, lap records, circuit facts, race winners, and historical win counts."),
    ("Predict",   "🔮",  "#E8A020",  "pages/predict.py",
     "ML-powered win probability predictions using grid position, standings, and recent form."),
    ("Contact",   "📞",  "#64C4FF",  "pages/contact.py",
     "Get in touch with the developer or explore the project on GitHub."),
]

def _card_header(icon, name, color, desc):
    return f"""
    <div style="border-top: 4px solid {color}; border-radius: 4px 4px 0 0;
                margin: -1px -1px 12px -1px; padding: 18px 18px 0 18px;">
      <span style="font-size:2rem;">{icon}</span>
      <span style="font-size:1.15rem; font-weight:700; color:#1A1A2E;
                   margin-left:8px; vertical-align:middle;">{name}</span>
    </div>
    <p style="color:#444; font-size:0.9rem; line-height:1.55; margin:0 0 14px 0;">{desc}</p>
    """

def feature_cards():
    st.markdown("### Explore the Dashboard")
    for i in range(0, len(_FEATURES), 3):
        cols = st.columns(3, gap="medium")
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(_FEATURES):
                break
            name, icon, color, page, desc = _FEATURES[idx]
            with col.container(border=True):
                st.markdown(_card_header(icon, name, color, desc), unsafe_allow_html=True)
                st.page_link(page, label=f"Open {name} →")

# ── Tech stack badges ────────────────────────────────────────────────────────
_STACK_HTML = """
<div style="margin: 8px 0 0 0;">
  <span style="font-size:0.8rem; font-weight:700; color:#888;
               text-transform:uppercase; letter-spacing:0.1em;">Built with</span>
  <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">
    <span style="background:#F0EBFC; color:#6C3DE8; border:1px solid #D0C0F8;
                 border-radius:20px; padding:4px 14px; font-size:0.85rem; font-weight:600;">
      Streamlit
    </span>
    <span style="background:#FFF3E0; color:#E65100; border:1px solid #FFCC80;
                 border-radius:20px; padding:4px 14px; font-size:0.85rem; font-weight:600;">
      FastF1
    </span>
    <span style="background:#E8F5E9; color:#2E7D32; border:1px solid #A5D6A7;
                 border-radius:20px; padding:4px 14px; font-size:0.85rem; font-weight:600;">
      Plotly
    </span>
    <span style="background:#E3F2FD; color:#1565C0; border:1px solid #90CAF9;
                 border-radius:20px; padding:4px 14px; font-size:0.85rem; font-weight:600;">
      Pandas
    </span>
    <span style="background:#FCE4EC; color:#C62828; border:1px solid #EF9A9A;
                 border-radius:20px; padding:4px 14px; font-size:0.85rem; font-weight:600;">
      Ergast API
    </span>
    <span style="background:#F3E5F5; color:#6A1B9A; border:1px solid #CE93D8;
                 border-radius:20px; padding:4px 14px; font-size:0.85rem; font-weight:600;">
      OpenF1 API
    </span>
  </div>
</div>
"""

def about_section():
    st.divider()
    st.markdown("## About the Project")
    c1, c2 = st.columns([3, 1], gap="large")

    with c1:
        st.write(
            "This dashboard harnesses **FastF1** telemetry, the **Ergast** historical API, and "
            "**OpenF1** live data to deliver interactive Formula 1 analysis. Every chart is built "
            "with Plotly — hover, zoom, and filter in the browser with no extra setup."
        )
        st.write(
            "Track lap-time deltas between teammates, study tyre degradation curves, review "
            "championship permutations, or explore the season circuit-by-circuit. "
            "Each page loads data on demand so heavy calculations never block your workflow."
        )
        st.markdown(_STACK_HTML, unsafe_allow_html=True)
        st.write("")
        st.markdown("[**GitHub Repository →**](https://github.com/Lelozitos/F1_Dashboard)")

    with c2:
        st.markdown("#### Inspirations")
        st.markdown(
            """
- [F1 Analysis](https://f1-analysis.com)
- [Formula Data Analysis](https://www.instagram.com/fdataanalysis/)
            """
        )
        st.markdown("#### Version")
        st.markdown(
            "<span style='background:#E8002D; color:white; border-radius:6px;"
            " padding:3px 10px; font-weight:700; font-size:0.9rem;'>v0.9.0</span>",
            unsafe_allow_html=True,
        )

_CARD_HOVER_CSS = """
<style>
/* Hover lift only for the feature cards on this page */
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 6px 20px rgba(108,61,232,0.18);
    transform: translateY(-2px);
    transition: box-shadow 0.18s ease, transform 0.18s ease;
}
</style>
"""

def main():
    nav_bar()
    st.markdown(_CARD_HOVER_CSS, unsafe_allow_html=True)
    st.markdown(_HERO_HTML, unsafe_allow_html=True)
    st.write("")
    feature_cards()
    about_section()

if __name__ == "__main__":
    main()
