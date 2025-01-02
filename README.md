<a name="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a align="center" href="https://github.com/Lelozitos/F1_Dashboard" style="font-size:100px"> 🏎 </a>

<h3 align="center">F1 Dashboard</h3>

  <p align="center">
    F1 Dashboard in Browser to Facilitate Access to Graphs
    <br />
    <a href="https://github.com/Lelozitos/F1_Dashboard"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <!--<a href="https://github.com/Lelozitos/F1_Dashboard">View Demo</a>-->
    <!--·-->
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

<!-- ![Demo](aaaaaaaaaaaaaaaaa) -->

A silly F1 Dashboard that I made while watching [Drive to Survive](https://www.netflix.com/title/80204890) and a Finals Week

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<a name="built-with"></a>

### Built With

- [![Streamlit][Streamlit-img]][Streamlit.com]
- [![FastF1][FastF1-img]][FastF1.com]
<!-- - [![OpenF1][OpenF1-img]][OpenF1.com] -->

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
   streamlit run ./home.py
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

- [ ] Add demo
- [ ] Finish Home
- [ ] Finish Contact
- [ ] Add more Graphs
  - [ ] Session
    - [ ] Qualifying deleted laps to analyze
    - [ ] Overtake graph, with close distances to ahead
    - [ ] Choose the curve and give statistics of it
  - [ ] Teams
  - [ ] Drivers
    - [ ] Add nationality flags
- [ ] Improve UI
  - [ ] Sessions with a podium like UI
  - [ ] More obvious starting grid
  - [ ] Format Time in graphs
  - [ ] There is no way of knowing driver's name by abbreviation
- [ ] Videos
  - [ ] Embed video of highlights by F1 YT (https://www.youtube.com/@Formula1)
  - [ ] Add a way to see a video simultaneously (break and acceleration in curves)
- [ ] Bug Fixes
  - [ x ] Albon in São Paulo 2024 giving error (maybe he didn't start?)
  - [ ] Fix old drivers colors
  - [ ] Fix new year without races
  - [ ] Sometimes graphs titles don't show up (couldn't reproduce it)
- [ ] Make an API and Database

See the [open issues](https://github.com/Lelozitos/F1_Dashboard/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->

<a name="contact"></a>

## 📞 Contact

Leandro Fabre - [LinkedIn](https://www.linkedin.com/in/leandrofabre/)

Project Link - [https://github.com/Lelozitos/F1_Dashboard](https://github.com/Lelozitos/F1_Dashboard)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->

[Streamlit-img]: https://img.shields.io/badge/Streamlit-35495E?style=for-the-badge&logo=streamlit&logoColor=4FC08D
[Streamlit.com]: https://streamlit.io
[FastF1-img]: https://img.shields.io/badge/FastF1-4A4A55?style=for-the-badge&logo=F1&logoColor=FF3E00
[FastF1.com]: https://docs.fastf1.dev
[OpenF1-img]: https://img.shields.io/badge/OpenF1-DD0031?style=for-the-badge&logo=f1&logoColor=white
[OpenF1.com]: https://openf1.org
