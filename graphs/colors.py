import fastf1.plotting

_TEAM_MAPPINGS = [
    ('#3671C6', ['Red Bull Racing', 'Red Bull', 'Red-Bull', 'RBR']),
    ('#E8002D', ['Ferrari', 'FER']),
    ('#27F4D2', ['Mercedes', 'MER']),
    ('#FF8000', ['McLaren', 'MCL']),
    ('#229971', ['Aston Martin', 'Aston-Martin', 'AMR']),
    ('#0093CC', ['Alpine', 'ALP']),
    ('#6692FF', ['RB', 'VCARB']),
    ('#B6BABD', ['Haas', 'Haas F1 Team', 'HAA']),
    ('#64C4FF', ['Williams', 'WIL']),
    ('#FF1A1A', ['Audi', 'Sauber', 'Stake', 'Kick Sauber', 'SAU']),
    ('#FFD700', ['Cadillac', 'CAD'])
]

TEAM_COLORS = {}
for color, aliases in _TEAM_MAPPINGS:
    for alias in aliases:
        TEAM_COLORS[alias] = color

def get_team_color_safe(team, session):
    try:
        color = fastf1.plotting.get_team_color(team, session)
        if not color or color.lower() == '#000000': raise ValueError
        return color
    except:
        return TEAM_COLORS.get(team, TEAM_COLORS.get(team.replace(" ", "-"), "gray"))

def get_driver_color_safe(driver, session):
    try:
        color = fastf1.plotting.get_driver_color(driver, session)
        if not color or color.lower() == '#000000': raise ValueError
        return color
    except:
        try:
            team = session.get_driver(driver)['TeamName']
            return get_team_color_safe(team, session)
        except:
            return TEAM_COLORS.get(driver, "gray")

def get_compound_mapping_safe(session):
    try:
        mapping = fastf1.plotting.get_compound_mapping(session)
        if not mapping: raise ValueError
        return mapping
    except:
        return {
            'SOFT': '#FF3333',
            'MEDIUM': '#FFFF33',
            'HARD': '#F0F0F0',
            'INTERMEDIATE': '#33CC33',
            'WET': '#3366FF',
            'HYPERSOFT': '#FF66FF',
            'ULTRASOFT': '#CC66FF',
            'SUPERSOFT': '#FF3333',
            'SUPERHARD': '#FF8000',
            'TEST-UNKNOWN': '#CBCBCB'
        }

def _get_driver_style_map(session, styles_list):
    """
    Assigns a distinct style from styles_list to drivers within the same team.
    e.g. ['solid', 'dash'] translates to standard style for driver 1, dashed for driver 2.
    """
    map_dict = {}
    
    # Check if we have valid results to order by team correctly
    if hasattr(session, 'results') and not session.results.empty:
        # Group drivers by team
        teams = session.results.groupby("TeamName")
        for team, df in teams:
            # Sort by driver abbreviation alphabetically for consistency across sessions
            drivers = sorted(df["Abbreviation"].tolist())
            for idx, driver in enumerate(drivers):
                map_dict[driver] = styles_list[idx % len(styles_list)]
    else:
        # Fallback if results are somehow entirely missing (e.g., bare Practice session without times)
        try:
            team_dict = {}
            for driver in session.drivers:
                info = session.get_driver(driver)
                team = info["TeamName"]
                abbr = info["Abbreviation"]
                team_dict.setdefault(team, []).append(abbr)
            
            for team, drivers in team_dict.items():
                drivers.sort()
                for idx, driver in enumerate(drivers):
                    map_dict[driver] = styles_list[idx % len(styles_list)]
        except:
             pass
    
    return map_dict

def get_driver_line_dash_map(session):
    return _get_driver_style_map(session, ["solid", "dash"])

def get_driver_pattern_map(session):
    # Plotly bar chart patterns: '' for solid finish, '/' for stripes
    return _get_driver_style_map(session, ["", "/"])

def get_driver_symbol_map(session):
    return _get_driver_style_map(session, ["circle", "x"])


# (speed, downforce, braking, overtaking) — 1–5
CIRCUIT_CHARS = {
    "Bahrain":       (3, 3, 3, 4),
    "Saudi Arabian": (5, 2, 4, 2),
    "Australian":    (3, 3, 3, 2),
    "Japanese":      (4, 4, 3, 2),
    "Chinese":       (3, 3, 3, 3),
    "Miami":         (3, 3, 4, 3),
    "Monaco":        (1, 5, 4, 1),
    "Spanish":       (3, 3, 3, 2),
    "Barcelona":     (3, 4, 3, 2),
    "Canadian":      (3, 2, 5, 4),
    "Austrian":      (4, 2, 4, 4),
    "British":       (4, 3, 3, 3),
    "Hungarian":     (2, 4, 3, 1),
    "Belgian":       (5, 2, 3, 4),
    "Dutch":         (3, 4, 3, 1),
    "Italian":       (5, 1, 5, 5),
    "Azerbaijan":    (4, 2, 4, 4),
    "Singapore":     (1, 5, 4, 2),
    "United States": (3, 3, 4, 3),
    "Mexico City":   (4, 2, 4, 3),
    "São Paulo":     (3, 3, 3, 4),
    "Las Vegas":     (5, 1, 3, 4),
    "Qatar":         (4, 4, 3, 2),
    "Abu Dhabi":     (3, 3, 3, 3),
}

# (speed, downforce, braking, traction) — car strengths, 1–5
CONSTRUCTOR_CHARS = {
    "Red Bull":      (4, 5, 4, 5),
    "McLaren":       (5, 4, 5, 4),
    "Ferrari":       (5, 4, 4, 4),
    "Mercedes":      (4, 3, 5, 4),
    "Aston Martin":  (3, 4, 4, 4),
    "Alpine":        (3, 3, 3, 3),
    "RB":            (3, 3, 4, 3),
    "Racing Bulls":  (3, 3, 4, 3),
    "Haas":          (3, 3, 3, 3),
    "Williams":      (3, 3, 3, 3),
    "Kick Sauber":   (2, 3, 3, 3),
    "Sauber":        (2, 3, 3, 3),
    "Cadillac":      (3, 3, 3, 3),
}
