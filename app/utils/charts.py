"""Shared Plotly styling, so every figure looks like part of one product."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go

from . import ui  # label vocabulary, shared with the tables

INK, MUTED, LINE, SURFACE = "#161A22", "#5A6472", "#E3E8EF", "#FFFFFF"
ACCENT, GOOD, WARN, BAD = "#0F62FE", "#0E8A5F", "#B25E09", "#C21E2B"

# Ordered categorical palette - colour-blind safe, consistent across every page.
SEQUENCE = ["#0F62FE", "#0E8A5F", "#B25E09", "#8A3FFC", "#C21E2B",
            "#007D79", "#D12771", "#4589FF", "#6929C4", "#009D9A"]

CLUSTER_COLOURS = {
    "High-traffic hub, elevated delays": BAD,
    "High-traffic hub, well-managed":    ACCENT,
    "Smaller airport, elevated delays":  WARN,
    "Smaller airport, reliable":         GOOD,
}

# Red = bad (late), green = good (on time). Used for every delay metric.
DELAY_SCALE = "RdYlGn_r"

FONT = dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif",
            size=12, color=INK)


def style(fig: go.Figure, height: int = 360, legend: bool = True) -> go.Figure:
    # Legend below the plot, never above it. A horizontal legend at y=1.0 sits in the
    # same band as a left-anchored title, and as soon as it wraps to a second row it
    # runs straight through the title text -- which is exactly what five delay causes
    # did to "Delay minutes by cause".
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=44, b=52 if legend else 8),
        showlegend=legend,
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font=FONT,
        title=dict(font=dict(size=14, color=INK), x=0.01, xanchor="left", y=0.96),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=LINE, font=FONT),
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="left", x=0,
                    font=dict(size=11), title_text=""),
        colorway=SEQUENCE,
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor=LINE, ticks="outside",
                     tickcolor=LINE, tickfont=dict(size=11, color=MUTED), title_font=dict(size=11))
    fig.update_yaxes(gridcolor=LINE, zeroline=False, showline=False,
                     tickfont=dict(size=11, color=MUTED), title_font=dict(size=11))
    return fig


def _labels(*cols) -> dict:
    """Axis titles from the same vocabulary the tables use, so `pct_of_delay_minutes`
    reads as "Share of delay minutes" on a chart exactly as it does in a column head."""
    out = {}
    for c in cols:
        if isinstance(c, str):
            out[c] = ui.label(c)
        elif isinstance(c, (list, tuple)):
            out.update({v: ui.label(v) for v in c if isinstance(v, str)})
    return out


def bar(df, x, y, title, color=None, orientation="v", height=360, **kw):
    kw.setdefault("labels", _labels(x, y, color))
    fig = px.bar(df, x=x, y=y, title=title, color=color, orientation=orientation,
                 color_discrete_sequence=SEQUENCE, **kw)
    fig.update_traces(marker_line_width=0)
    return style(fig, height, legend=color is not None)


def line(df, x, y, title, color=None, markers=True, height=360, **kw):
    kw.setdefault("labels", _labels(x, y, color))
    fig = px.line(df, x=x, y=y, title=title, color=color, markers=markers,
                  color_discrete_sequence=SEQUENCE, **kw)
    fig.update_traces(line=dict(width=2.4), marker=dict(size=6))
    return style(fig, height, legend=color is not None)


def scatter(df, x, y, title, size=None, color=None, hover_name=None, height=380, **kw):
    kw.setdefault("labels", _labels(x, y, color, size))
    fig = px.scatter(df, x=x, y=y, size=size, color=color, title=title,
                     hover_name=hover_name, color_discrete_sequence=SEQUENCE, **kw)
    fig.update_traces(marker=dict(line=dict(width=0), opacity=0.78))
    return style(fig, height)


def empty(message: str) -> go.Figure:
    """A styled placeholder, so a missing dataset does not render as a broken box."""
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False,
                       font=dict(size=13, color=MUTED), x=0.5, y=0.5, xref="paper", yref="paper")
    fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
    return style(fig, height=200, legend=False)
