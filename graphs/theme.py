import plotly.graph_objects as go
import plotly.io as pio

_REGISTERED = False


def register_theme():
    """Register the shared brand template as Plotly's default, once.

    One place controls how every chart in the app looks — fonts, gridlines,
    transparent background, hover styling. Individual graph_* functions still
    call update_layout() for their own title/axis text, which layers on top.
    """
    global _REGISTERED
    if _REGISTERED:
        return
    pio.templates["f1_dashboard"] = go.layout.Template(
        layout=go.Layout(
            font=dict(family="Arial, sans-serif", color="#1A1A2E", size=13),
            title=dict(font=dict(size=22, family="Arial, sans-serif", color="#1A1A2E"), x=0.5, xanchor="center"),
            colorway=["#6C3DE8", "#E8002D", "#229971", "#3671C6", "#FF8000",
                      "#64C4FF", "#E8A020", "#B6BABD", "#27F4D2", "#FFD700"],
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(bgcolor="white", font_size=13, font_family="Arial, sans-serif",
                             bordercolor="#6C3DE8"),
            xaxis=dict(gridcolor="#EEEEF2", zerolinecolor="#DDDDE5", linecolor="#CCCCD6", ticks="outside"),
            yaxis=dict(gridcolor="#EEEEF2", zerolinecolor="#DDDDE5", linecolor="#CCCCD6", ticks="outside"),
            legend=dict(bgcolor="rgba(255,255,255,0.85)", bordercolor="#EEEEF2", borderwidth=1),
            margin=dict(t=72, l=48, r=24, b=48),
        )
    )
    pio.templates.default = "f1_dashboard"
    _REGISTERED = True
