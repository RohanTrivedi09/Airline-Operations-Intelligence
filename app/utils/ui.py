"""Shared presentation layer: theme CSS, KPI cards, section headers.

Streamlit's defaults are functional but generic. Everything here is styling only --
it changes how the data looks, never what the data says.
"""

from __future__ import annotations

import streamlit as st

PALETTE = {
    "ink": "#161A22",
    "muted": "#5A6472",
    "line": "#E3E8EF",
    "surface": "#FFFFFF",
    "canvas": "#F4F6FA",
    "accent": "#0F62FE",
    "good": "#0E8A5F",
    "warn": "#B25E09",
    "bad": "#C21E2B",
}

_CSS = """
<style>
  /* ---------- shell ---------- */
  #MainMenu, footer, header [data-testid="stToolbar"] {visibility: hidden;}
  .block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1400px;}

  /* ---------- typography ---------- */
  html, body, [class*="css"] {
      font-feature-settings: "tnum" 1, "cv05" 1;
      color: %(ink)s;
  }
  h1 {font-size: 1.9rem !important; font-weight: 680 !important; letter-spacing: -0.02em;
      margin-bottom: .15rem !important;}
  h2 {font-size: 1.25rem !important; font-weight: 640 !important; letter-spacing: -0.01em;
      margin-top: 2rem !important;}
  h3 {font-size: 1.02rem !important; font-weight: 620 !important; color: %(ink)s;}

  /* ---------- sidebar ---------- */
  section[data-testid="stSidebar"] {
      background: %(canvas)s; border-right: 1px solid %(line)s;
  }
  section[data-testid="stSidebar"] .block-container {padding-top: 1.2rem;}

  /* ---------- KPI cards ---------- */
  .kpi-row {display: flex; gap: .75rem; flex-wrap: wrap; margin: .4rem 0 1.1rem;}
  .kpi {
      /* min-width:0 lets a card shrink below its content width, so a row of five
         stays on one line instead of wrapping the last card onto its own row. */
      flex: 1 1 0; min-width: 0; background: %(surface)s;
      border: 1px solid %(line)s; border-radius: 10px; padding: .85rem .95rem;
      box-shadow: 0 1px 2px rgba(16,24,40,.04);
  }
  .kpi .label {
      font-size: .70rem; font-weight: 600; letter-spacing: .06em;
      text-transform: uppercase; color: %(muted)s; margin-bottom: .3rem;
  }
  .kpi .value {font-size: 1.5rem; font-weight: 660; line-height: 1.1; letter-spacing: -0.02em;
      white-space: nowrap;}
  .kpi .sub {font-size: .73rem; color: %(muted)s; margin-top: .25rem;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;}
  @media (max-width: 900px) {.kpi {flex: 1 1 140px;}}
  .kpi.good .value {color: %(good)s;}
  .kpi.warn .value {color: %(warn)s;}
  .kpi.bad  .value {color: %(bad)s;}

  /* ---------- section header ---------- */
  .sec {margin: 1.9rem 0 .5rem; padding-bottom: .4rem; border-bottom: 1px solid %(line)s;}
  .sec .t {font-size: 1.1rem; font-weight: 640; letter-spacing: -0.01em;}
  .sec .d {font-size: .82rem; color: %(muted)s; margin-top: .12rem;}

  /* ---------- note ---------- */
  .note {
      background: %(canvas)s; border-left: 3px solid %(accent)s;
      border-radius: 0 8px 8px 0; padding: .7rem .9rem; margin: .6rem 0 1rem;
      font-size: .84rem; color: %(muted)s; line-height: 1.5;
  }
  .note strong {color: %(ink)s;}

  /* ---------- tables & charts ---------- */
  [data-testid="stDataFrame"] {border: 1px solid %(line)s; border-radius: 10px;}
  [data-testid="stPlotlyChart"] {
      border: 1px solid %(line)s; border-radius: 10px;
      padding: .35rem; background: %(surface)s;
  }
  [data-testid="stMetricValue"] {font-size: 1.4rem; font-weight: 640;}
  hr {margin: 1.6rem 0; border-color: %(line)s;}
</style>
""" % PALETTE


def setup(title: str, icon: str, subtitle: str = "") -> None:
    """Apply theme CSS and render the page title. Call once, first thing on a page."""
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(f"# {icon} {title}")
    if subtitle:
        st.markdown(
            f"<div style='color:{PALETTE['muted']};font-size:.9rem;margin:-.2rem 0 1.1rem'>"
            f"{subtitle}</div>", unsafe_allow_html=True)


def kpis(cards: list[dict]) -> None:
    """Render a row of KPI cards.

    Each card: {label, value, sub (optional), tone: good|warn|bad|None}
    The `sub` line is what st.metric cannot express -- usually the sample size
    behind the number, which every rate on this dashboard should carry.
    """
    html = ['<div class="kpi-row">']
    for c in cards:
        tone = f" {c['tone']}" if c.get("tone") else ""
        sub = f"<div class='sub'>{c['sub']}</div>" if c.get("sub") else ""
        html.append(
            f"<div class='kpi{tone}'><div class='label'>{c['label']}</div>"
            f"<div class='value'>{c['value']}</div>{sub}</div>")
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def section(title: str, description: str = "") -> None:
    d = f"<div class='d'>{description}</div>" if description else ""
    st.markdown(f"<div class='sec'><div class='t'>{title}</div>{d}</div>",
                unsafe_allow_html=True)


def note(text: str) -> None:
    """A quiet inline caveat -- used for sample-size and fairness notes."""
    st.markdown(f"<div class='note'>{text}</div>", unsafe_allow_html=True)


def tone_for_delay(rate: float) -> str:
    """Colour a delay rate consistently across every page."""
    return "good" if rate < 15 else ("warn" if rate < 22 else "bad")
