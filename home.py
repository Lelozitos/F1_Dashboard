# python -m streamlit run ./home.py

import streamlit as st

def set_streamlit_page_config_once():
    try:
        st.set_page_config(page_title="F1", page_icon="🏎", layout="wide")
    except st.errors.StreamlitAPIException as e:
        if "can only be called once per app" in e.__str__(): return
        raise e

def nav_bar():
    set_streamlit_page_config_once()
    st.header("F1 CONSULTING", divider="rainbow")
    cols = st.columns(5)
    cols[0].page_link("home.py", label="**Home**", icon="🏡")
    cols[1].page_link("pages/sessions.py", label="**Sessions**", icon="🏎")
    cols[2].page_link("pages/teams.py", label="**Teams**", icon="👨‍👨‍👧‍👦")
    cols[3].page_link("pages/drivers.py", label="**Drivers**", icon="🙍‍♂️")
    cols[4].page_link("pages/contact.py", label="**Contact**", icon="📞")

def credits():
    st.title("📜 Credits")
    st.info(
        """
        Developed by: **Leandro Fabre**  

        [**LinkedIn**](https://linkedin.com/in/leandrofabre)  
        [**Email**](mailto:lm.fabre@hotmail.com)  
        [**GitHub**](https://github.com/Lelozitos)  
        
        Special thanks to the Formula 1 data community for their contributions.
        """
    )

    st.info("""
    **Application Version**  
    v0.8.2
    """)

def main():
    nav_bar()
    
    st.write("")
    cols = st.columns(3, border=True)
    cols[0].title("🏎 Sessions")
    cols[0].write("Access in-depth data from individual race sessions, including practice, qualifying, and the Grand Prix. Review telemetry data, track conditions, tire strategies, and session-specific performance metrics. This section is perfect for uncovering key moments and understanding how each session impacts the overall race weekend.")
    cols[1].title("👨‍👨‍👧‍👦 Teams")
    cols[1].write("Dive into the performance and strategies of Formula 1 teams. This section provides detailed insights into each team's statistics, including points, rankings, pit stop efficiency, and car development trends throughout the season. Compare teams side-by-side to uncover strengths, weaknesses, and their battle for the Constructors' Championship.")
    cols[2].title("🙍‍♂️ Drivers")
    cols[2].write("Explore the stats and performance of Formula 1 drivers. Analyze lap times, sector performance, overtakes, and driving consistency. Visualize driver comparisons, study their progression over the season, and discover how they stack up against their rivals in the fight for the Drivers' Championship.")

    # TODO add next race
    # st.components.v1.iframe("https://example.com", height=500, scrolling=True)
    for _ in range(6): st.write("")
    
    st.markdown("# ![F1](https://media.formula1.com/image/upload/f_auto,c_limit,w_200,q_auto/f_auto/q_auto/content/dam/fom-website/subscribe-to-f1/f1_logo_fallback) About the project")
    st.write("Unleashing the power of data-driven insights for Formula 1 enthusiasts.")
    st.write("This program is designed to provide comprehensive and interactive visualizations of Formula 1 data. From telemetry analysis to driver and team performance comparisons, it offers users the ability to explore and understand the intricate details of the sport. Whether you’re tracking lap times, analyzing speed differentials, or studying historical race data, this tool delivers an engaging and intuitive experience. Perfect for fans, analysts, and engineers looking to deepen their understanding of F1 dynamics.")
    st.markdown("#### [Project Repo](https://github.com/Lelozitos/F1_Dashboard)")

    st.markdown("## Inspirations")
    st.markdown("[F1 Analysis](https://f1-analysis.com)")
    st.markdown("[Formula Data Analysis](https://www.instagram.com/fdataanalysis/)")

main()

# https://public.tableau.com/app/profile/mateusz.karmalski/viz/F1ResultsTracker/Results 