"""Shared Plotly styling, so every page looks like part of one product."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go

# Colour-blind safe, consistent across all pages.
SEQ = px.colors.sequential.Blues
CLUSTER_COLOURS = {
    "High-traffic hub, elevated delays": "#d62728",
    "High-traffic hub, well-managed": "#1f77b4",
    "Smaller airport, elevated delays": "#ff7f0e",
    "Smaller airport, reliable": "#2ca02c",
}
GOOD, BAD, NEUTRAL = "#2ca02c", "#d62728", "#1f77b4"


def style(fig: go.Figure, height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=legend,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
        hovermode="closest",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.2)")
    return fig


def bar(df, x, y, title, color=None, orientation="v", **kw):
    fig = px.bar(df, x=x, y=y, title=title, color=color, orientation=orientation, **kw)
    return style(fig, legend=color is not None)


def line(df, x, y, title, color=None, markers=True, **kw):
    fig = px.line(df, x=x, y=y, title=title, color=color, markers=markers, **kw)
    return style(fig, legend=color is not None)


def scatter(df, x, y, title, size=None, color=None, hover_name=None, **kw):
    fig = px.scatter(df, x=x, y=y, size=size, color=color, title=title,
                     hover_name=hover_name, **kw)
    return style(fig)


def delay_scale(values):
    """Red for high delay, green for low -- used consistently for delay metrics."""
    return dict(color=values, colorscale="RdYlGn_r", showscale=True)
