"""Shared presentation layer: theme CSS, KPI cards, section headers.

Streamlit's defaults are functional but generic. Everything here is styling only --
it changes how the data looks, never what the data says.
"""

from __future__ import annotations

from pathlib import Path

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

  /* Streamlit derives its own nav from the pages/ filenames. We render a grouped one
     with real labels instead, so hide the automatic list rather than show two. */
  [data-testid="stSidebarNav"] {display: none;}

  .nav-group {
      font-size: .66rem; font-weight: 700; letter-spacing: .09em;
      text-transform: uppercase; color: %(muted)s;
      margin: 1.15rem 0 .3rem .2rem;
  }
  .nav-group:first-of-type {margin-top: .35rem;}
  section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
      border-radius: 8px; padding: .34rem .55rem; margin: .08rem 0;
  }
  section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {
      background: rgba(15,98,254,.08);
  }
  .nav-foot {
      margin-top: 1.6rem; padding-top: .8rem; border-top: 1px solid %(line)s;
      font-size: .72rem; color: %(muted)s; line-height: 1.45;
  }

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


_APP_DIR = Path(__file__).resolve().parent.parent

# (section label, page path relative to Home.py, icon, link label)
_NAV = [
    ("", "Home.py", ":material/home:", "Home"),
    ("Explore", "pages/01_Overview.py", ":material/insights:", "Overview"),
    ("Explore", "pages/02_Airlines.py", ":material/flight:", "Airlines"),
    ("Explore", "pages/03_Airports.py", ":material/location_on:", "Airports"),
    ("Explore", "pages/04_Routes.py", ":material/route:", "Routes"),
    ("Explore", "pages/05_Delay_Causes.py", ":material/schedule:", "Delay causes"),
    ("Model", "pages/06_Prediction.py", ":material/model_training:", "Delay prediction"),
    ("Live", "pages/07_Live_Monitor.py", ":material/sensors:", "Live monitor"),
]


def sidebar_nav() -> None:
    """Grouped sidebar navigation.

    `st.page_link` is native and marks the current page itself, so this needs no
    third-party component -- one less thing to pin when the app is deployed.
    """
    with st.sidebar:
        st.markdown(
            "<div style='font-weight:680;font-size:.95rem;letter-spacing:-.01em'>"
            "&#9992;&#65039; Airline Ops Intelligence</div>"
            "<div style='font-size:.72rem;color:#5A6472;margin-bottom:.2rem'>"
            "US domestic flights, 2015</div>", unsafe_allow_html=True)
        seen = None
        for group, page, icon, label in _NAV:
            if group != seen:
                if group:
                    st.markdown(f"<div class='nav-group'>{group}</div>",
                                unsafe_allow_html=True)
                seen = group
            # Skip a link whose page file is genuinely absent, but let anything else
            # (an invalid Material icon name, say) raise -- a nav entry that vanishes
            # silently is harder to notice than one that fails loudly.
            if not (_APP_DIR / page).exists():
                continue
            st.page_link(page, label=label, icon=icon)
        st.markdown(
            "<div class='nav-foot'>Precomputed by Apache Spark.<br>"
            "The dashboard reads documents, never the 5.8M rows.</div>",
            unsafe_allow_html=True)


def setup(title: str, icon: str, subtitle: str = "") -> None:
    """Apply theme CSS, render the sidebar nav and the page title.

    Call once, first thing on a page.
    """
    st.markdown(_CSS, unsafe_allow_html=True)
    sidebar_nav()
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


# Marts follow one naming convention, so column formatting can be inferred from the
# name instead of restated at all eleven call sites: `*_rate`/`*_pct` are percentages
# on a 0-100 scale, `total_*`/`*_flights` are counts, `avg_*`/`median_*` are minutes.
# Marts follow one naming convention, so column formatting can be inferred from the
# name instead of restated at all thirteen call sites. The duration columns are listed
# explicitly rather than matched on an `avg_` prefix: `avg_flights` is a count, and a
# prefix rule renders it as "33525.0 min", which is wrong in a way no exception catches.
_PCT_SUFFIX = ("_rate", "_pct", "_share")
# Bars only for the headline comparative rates. `cancellation_rate` sits at 1-3% and
# would be an invisible sliver on a 0-100 axis; a bar you cannot see is worse than none.
_BAR_COLUMNS = {"delay_rate", "delay_rate_pct", "on_time_pct"}
_MINUTE_COLUMNS = {
    "avg_delay", "avg_dep_delay", "avg_arr_delay", "median_delay",
    "dep_delay", "arr_delay", "prev_arr_delay", "scheduled_turnaround",
}
_COUNT_SUFFIX = ("_flights", "_minutes", "flights", "delayed", "_count")
# Percentage columns whose names carry no suffix to key off.
_PCT_COLUMNS = {"percentage"}
_LABELS = {
    "airline_code": "Code", "airline_name": "Airline", "airport_code": "Code",
    "airport_name": "Airport", "total_flights": "Flights", "on_time_pct": "On time",
    "delay_rate": "Delay rate", "delay_rate_pct": "Delay rate",
    "cancellation_rate": "Cancelled", "avg_dep_delay": "Avg dep delay",
    "avg_arr_delay": "Avg arr delay", "median_delay": "Median delay",
    "routes_served": "Routes", "roc_auc": "ROC-AUC", "f1": "F1",
    "total_minutes": "Total minutes", "origin": "From", "destination": "To",
    "avg_flights": "Avg flights", "airlines_served": "Airlines",
    "pct_of_delay_minutes": "Share of delay minutes",
    "peak_hour_congestion": "Peak congestion", "peak_delay_hour": "Peak delay hour",
}


def _label(col: str) -> str:
    return _LABELS.get(col, col.replace("_", " ").capitalize())


def table(df, *, columns=None, height=None, hide_index=True, overrides=None):
    """Render a DataFrame with formatting inferred from the mart naming convention.

    Percentage columns get a progress bar scaled to a **full 0-100 axis**, not to the
    column's own maximum. Scaling to the max would make a 19%-vs-22% difference fill
    the width and read as dramatic; on a 0-100 axis the bar stays proportional to the
    quantity it represents. This dashboard already refuses to rank on small samples,
    and exaggerating small differences visually would undo that.
    """
    frame = df[columns] if columns else df
    cfg = dict(overrides or {})
    for col in frame.columns:
        if col in cfg:
            continue
        if col in _BAR_COLUMNS:
            cfg[col] = st.column_config.ProgressColumn(
                _label(col), format="%.2f%%", min_value=0, max_value=100)
        elif col.endswith(_PCT_SUFFIX) or col.startswith("pct_") or col in _PCT_COLUMNS:
            cfg[col] = st.column_config.NumberColumn(_label(col), format="%.2f%%")
        elif col in _MINUTE_COLUMNS:
            cfg[col] = st.column_config.NumberColumn(_label(col), format="%.1f min")
        elif col.endswith(_COUNT_SUFFIX) or col.startswith("total_"):
            cfg[col] = st.column_config.NumberColumn(_label(col), format="localized")
        else:
            cfg[col] = st.column_config.Column(_label(col))

    st.dataframe(frame, hide_index=hide_index, width="stretch",
                 column_config=cfg, **({"height": height} if height else {}))
