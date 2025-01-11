<a name="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a align="center" href="https://github.com/Lelozitos/F1_Dashboard" style="font-size:100px"> 🏎 </a>

<h3 align="center">F1 Dashboard</h3>

  <p align="center">
    Unleashing the power of data-driven insights for Formula 1 enthusiasts.
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
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->

<a name="about"></a>

## ✨ About The Project

[![F1 Dashboard v0.8.2](https://img.youtube.com/vi/K-KOvKbXpBs/maxresdefault.jpg)](https://www.youtube.com/watch?v=K-KOvKbXpBs 'F1 Dashboard v0.8.2')

This program is designed to provide comprehensive and interactive visualizations of Formula 1 data. From telemetry analysis to driver and team performance comparisons, it offers users the ability to explore and understand the intricate details of the sport. Whether you’re tracking lap times, analyzing speed differentials, or studying historical race data, this tool delivers an engaging and intuitive experience. Perfect for fans, analysts, and engineers looking to deepen their understanding of F1 dynamics.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<a name="built-with"></a>

### Built With

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

   - Open `InstallRequirements.bat` or
   - Install with pip
     ```sh
     python -m pip install -r requirements.txt
     ```

1. Running the app
   ```sh
   python -m streamlit run ./home.py
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE -->

<a name="usage"></a>

## 🔧 Usage

Once the website is open, you can navigate through diffent tabs in the navigation bar above, which contains (for now)

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

[Streamlit-img]: https://img.shields.io/badge/Streamlit-35495E?style=for-the-badge&logo=streamlit&logoColor=4FC08D
[Streamlit.com]: https://streamlit.io
[FastF1-img]: https://img.shields.io/badge/FastF1-4A4A55?style=for-the-badge&logo=F1&logoColor=FF3E00
[FastF1.com]: https://docs.fastf1.dev
[OpenF1-img]: https://img.shields.io/badge/OpenF1-DD0031?style=for-the-badge&logo=f1&logoColor=white
[OpenF1.com]: https://openf1.org
