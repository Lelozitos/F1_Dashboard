import streamlit as st
from home import nav_bar

import fastf1.ergast
import plotly.express as px # https://dash.plotly.com/minimal-app
import pandas as pd
import numpy as np
import datetime

def calculate_max_points(year, round):
    POINTS_FOR_SPRINT = 8 + 25 + 1
    POINTS_FOR_CONVENTIONAL = 25 + 1

    events = fastf1.events.get_event_schedule(year, backend="ergast")

    events = events[events["RoundNumber"] > round]
    sprint_events = len(events.loc[events["EventFormat"] == "sprint_shootout"])
    conventional_events = len(events.loc[events["EventFormat"] == "conventional"])

    return (sprint_events*POINTS_FOR_SPRINT) + (conventional_events*POINTS_FOR_CONVENTIONAL)

def load_data(year, location):
    ergast = fastf1.ergast.Ergast()
    races = ergast.get_race_schedule(year)
    races = races.loc[:races.index[races["raceName"] == location][0]]
    results = []
    for rnd, race in races["raceName"].items():
        temp = ergast.get_race_results(season=year, round=rnd + 1)
        temp = temp.content[0]

        sprint = ergast.get_sprint_results(season=year, round=rnd + 1)
        if sprint.content and sprint.description['round'][0] == rnd + 1:
            temp = pd.merge(temp, sprint.content[0], on='driverCode', how='left')
            # Add sprint points and race points to get the total
            temp['points'] = temp['points_x'] + temp['points_y']
            temp.drop(columns=['points_x', 'points_y'], inplace=True)

        # Add round no. and grand prix name
        temp['round'] = rnd + 1
        temp['race'] = race.removesuffix(' Grand Prix')
        temp = temp[['round', 'race', 'driverCode', 'points']]  # Keep useful cols.
        results.append(temp)

    results = pd.concat(results)
    races = results['race'].drop_duplicates()

    results = results.pivot(index='driverCode', columns='round', values='points')

    # Rank the drivers by their total points
    results['total_points'] = results.sum(axis=1)
    results = results.sort_values(by='total_points', ascending=False)
    results.drop(columns='total_points', inplace=True)

    # Use race name, instead of round no., as column names
    results.columns = races
    return results

def load_graphs(results, year, location):
    fig = px.imshow(
    results,
    text_auto=True,
    aspect='auto',  # Automatically adjust the aspect ratio
    color_continuous_scale=[[0,    'rgb(198, 219, 239)'],  # Blue scale
                            [0.25, 'rgb(107, 174, 214)'],
                            [0.5,  'rgb(33,  113, 181)'],
                            [0.75, 'rgb(8,   81,  156)'],
                            [1,    'rgb(8,   48,  107)']],
    labels={'x': 'Race',
            'y': 'Driver',
            'color': 'Points'}       # Change hover texts
    )
    fig.update_xaxes(title_text='')      # Remove axis titles
    fig.update_yaxes(title_text='')
    fig.update_yaxes(tickmode='linear')  # Show all ticks, i.e. driver names
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGrey',
                    showline=False,
                    tickson='boundaries')              # Show horizontal grid only
    fig.update_xaxes(showgrid=False, showline=False)    # And remove vertical grid
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)')     # White background
    fig.update_layout(coloraxis_showscale=False)        # Remove legend
    fig.update_layout(xaxis=dict(side='top'))           # x-axis on top
    fig.update_layout(margin=dict(l=0, r=0, b=0, t=0))  # Remove border margins

    print(results)

    st.plotly_chart(fig)

def load_standings(standings, year, round):
    MAX_POINTS = calculate_max_points(year, round)
    LEADER_POINTS = int(standings.iloc[0]["points"])

    cols = st.columns(3)
    for i in range(3):
        driver = standings.iloc[i]
        with cols[i].container(border=True):
            st.markdown(f"{driver['position']} | {driver['givenName']} {driver['familyName']} - {int(driver['points'])} {'Yes' if driver['points'] + MAX_POINTS >= LEADER_POINTS else 'No'} | {driver['constructorNames'][0]}")
            st.markdown(f"[![{driver['driverCode']}](https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/{driver['givenName'][:1]}/{driver['givenName'][:3].upper()}{driver['familyName'][:3].upper()}01_{driver['givenName']}_{driver['familyName']}/{driver['givenName'][:3].lower()}{driver['familyName'][:3].lower()}01.png)]({driver['driverUrl']})") # "https://media.formula1.com/image/upload/f_auto,c_limit,q_75,w_1320/content/dam/fom-website/drivers/{year}Drivers/{driver['familyName'].lower()}"

    for i in range(3, len(standings.index), 4):
        cols = st.columns(4)
        for j in range(4):
            try:
                driver = standings.iloc[i+j]
                with cols[j].container(border=True):
                    st.markdown(f"{driver['position']} | {driver['givenName']} {driver['familyName']} - {int(driver['points'])} {'Yes' if driver['points'] + MAX_POINTS >= LEADER_POINTS else 'No'} | {driver['constructorNames'][0]}")
                    st.markdown(f"[![{driver['driverCode']}](https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/{driver['givenName'][:1]}/{driver['givenName'][:3].upper()}{driver['familyName'][:3].upper()}01_{driver['givenName']}_{driver['familyName']}/{driver['givenName'][:3].lower()}{driver['familyName'][:3].lower()}01.png)]({driver['driverUrl']})") # "https://media.formula1.com/image/upload/f_auto,c_limit,q_75,w_1320/content/dam/fom-website/drivers/{year}Drivers/{driver['familyName'].lower()}"

            except: continue

    st.dataframe(standings)

def main():
    ergast = fastf1.ergast.Ergast()
    nav_bar()

    with st.sidebar:
        year = st.selectbox("Year", range(datetime.date.today().year, 2018-1, -1))
        data = fastf1.events.get_event_schedule(year).query("EventFormat != 'testing'")
        data.set_index("EventName", inplace=True)
        data = data[data["Session5DateUtc"] < (pd.Timestamp.utcnow() - pd.Timedelta("4h")).to_datetime64()]
        location = st.selectbox("Event", data.index[::-1])

        with st.spinner("Loading..."):
            standings = ergast.get_driver_standings(season=year, round=data.loc[location]["RoundNumber"]).content[0]
            # results = load_data(year, location)
        st.success("Success!")

    st.title(f"{year} Drivers Championship | {location}")
    tabs = st.tabs(["👨‍👨‍👧‍👦 :orange[Standings]", ":orange[📈 Graph]"])
    with tabs[0]:
        load_standings(standings, year, data.loc[location]["RoundNumber"])
    with tabs[1]:
        st.write("aaaaaaaaa")
        # load_graphs(results, year, location)

main()