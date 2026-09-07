<a name="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a align="center" href="https://github.com/Lelozitos/F1_Dashboard" style="font-size:100px"> 🏎️🤖 </a>

<h3 align="center">F1 AI Agent</h3>

  <p align="center">
    Ask anything about Formula 1 — Claude looks up the real data before it answers.
    <br />
    <a href="https://github.com/Lelozitos/F1_Dashboard"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://www.youtube.com/watch?v=K-KOvKbXpBs">View Demo</a>
    ·
    <a href="https://github.com/Lelozitos/F1_Dashboard/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    ·
    <a href="https://github.com/Lelozitos/F1_Dashboard/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#installation">Installation</a>
    </li>
    <li><a href="#ai-agent">AI Agent</a></li>
    <li><a href="#dashboard">Dashboard</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->

<a name="about"></a>

## ✨ About The Project

[![F1 Dashboard v0.8.2](https://img.youtube.com/vi/K-KOvKbXpBs/maxresdefault.jpg)](https://www.youtube.com/watch?v=K-KOvKbXpBs 'F1 Dashboard v0.8.2')

This project's core is a Claude-powered agent that answers F1 questions on demand — results, lap times, standings, pit stops — by calling the same live data sources a human analyst would, instead of guessing from training data. It ships alongside the dashboard that data layer was originally built for: interactive visualizations covering telemetry, driver and team performance, and historical race data, for anyone who wants to explore the numbers directly instead of asking for them.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<a name="built-with"></a>

### Built With

- [![Claude][Claude-img]][Claude.com]
- [![Streamlit][Streamlit-img]][Streamlit.com]
- [![FastF1][FastF1-img]][FastF1.com]
- [![OpenF1][OpenF1-img]][OpenF1.com]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- INSTALLATION -->

<a name="installation"></a>

## ⚙️️️️️ Installation

1. Clone the repo

   ```sh
   git clone https://github.com/Lelozitos/F1_Dashboard.git
   ```

1. Install Requirements

   - For the AI agent:
     ```sh
     python -m pip install -r ai_agent/requirements.txt
     ```
   - For the dashboard — open `InstallRequirements.bat` or:
     ```sh
     python -m pip install -r requirements.txt
     ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- AI AGENT -->

<a name="ai-agent"></a>

## 🤖 AI Agent

```sh
streamlit run ai_agent/app.py
```

Chat interface. Ask it about a session, a driver's lap times, a championship standing, a pit stop — Claude picks the right tool (FastF1, Ergast, or OpenF1) and answers from the real data it gets back, citing the round/session/driver the numbers came from. Needs your own `ANTHROPIC_API_KEY` in the environment; each question costs API tokens.

Runs as its own Streamlit app, independent of the dashboard below — you can run either one alone, or both at once on different ports.

Full setup, architecture and the complete list of tools it can call: [`ai_agent/README.md`](ai_agent/README.md).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- DASHBOARD -->

<a name="dashboard"></a>

## 📊 Dashboard

```sh
python -m streamlit run ./home.py
```

The visualization layer the AI agent's tools are built on top of. Browse it directly through the navigation bar:

- **Session |** See graphs related to a single session in the calendar
- **Teams &nbsp;&nbsp;|** See teams standings and graphs
- **Drivers &nbsp;|** See drivers standings and graphs

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->

<a name="roadmap"></a>

## 🚀 Roadmap

- [x] Add demo
- [x] Finish Home
- [x] Finish Contact
- [x] Add AI Agent with tool use over FastF1/Ergast/OpenF1
- [ ] Add more Graphs
  - [ ] Session
    - [ ] Light mode compatibility
    - [ ] Qualifying deleted laps to analyze
    - [ ] Overtake graph, with close distances to ahead
    - [ ] Choose the curve and give statistics of it
    - [ ] Join every practice data
    - [x] Wind graph
  - [ ] Teams
  - [ ] Drivers
    - [ ] Add nationality flags
- [ ] Improve UI
  - [x] Sessions with a podium like UI
  - [x] More obvious starting grid
  - [x] Format Time in graphs
  - [x] There is no way of knowing driver's name by abbreviation
  - [x] Increase contrast in light mode (haas and hard tyre)
  - [ ] Change _hover_data_ with manual _hovertemplate_
- [ ] Videos
  - [ ] Embed video of highlights by F1 YT (https://www.youtube.com/@Formula1)
  - [ ] Add a way to see a video simultaneously (break and acceleration in curves)
- [ ] Bug Fixes
  - [x] Albon in São Paulo 2024 giving error (maybe he didn't start?)
  - [ ] Fix old drivers colors
  - [x] Fix new year without races
  - [ ] Sometimes graphs titles don't show up (couldn't reproduce it)
  - [x] Driver and Compound color deprecated, however new alternative doesn't suit me
  - [ ] If it starts raining in the middle of the race, quicklaps doesn't work and wo_laps suck (monaco 2023)
- [ ] Add Circuits page
- [ ] Change files of graphs logic
- [ ] Make an API and Database
- [ ] Hate the fact that it recalculates most of telemetries and colors for every graph

See the [open issues](https://github.com/Lelozitos/F1_Dashboard/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->

<a name="contact"></a>

## 📞 Contact

Leandro Fabre - [LinkedIn](https://www.linkedin.com/in/leandrofabre/)  
Leandro Fabre - [Email](mailto:lm.fabre@hotmail.com)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->

[Claude-img]: https://img.shields.io/badge/Claude-D97757?style=for-the-badge&logo=anthropic&logoColor=white
[Claude.com]: https://www.anthropic.com/claude
[Streamlit-img]: https://img.shields.io/badge/Streamlit-35495E?style=for-the-badge&logo=streamlit&logoColor=4FC08D
[Streamlit.com]: https://streamlit.io
[FastF1-img]: https://img.shields.io/badge/FastF1-4A4A55?style=for-the-badge&logo=F1&logoColor=FF3E00
[FastF1.com]: https://docs.fastf1.dev
[OpenF1-img]: https://img.shields.io/badge/OpenF1-DD0031?style=for-the-badge&logo=f1&logoColor=white
[OpenF1.com]: https://openf1.org
