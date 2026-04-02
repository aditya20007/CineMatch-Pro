"""
utils.py  —  Data loading, charts, watchlist, helpers
"""

import os
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DATA_DIR       = os.path.join(BASE_DIR, "data")
MOVIES_PATH    = os.path.join(DATA_DIR, "movies.csv")
RATINGS_PATH   = os.path.join(DATA_DIR, "ratings.csv")
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")

C = {
    "bg":     "#0A0A0F",
    "surf":   "#111118",
    "surf2":  "#1A1A2E",
    "card":   "#16162A",
    "pri":    "#E50914",
    "acc":    "#F5C518",
    "teal":   "#00D2C6",
    "txt":    "#FFFFFF",
    "muted":  "#9999BB",
    "border": "rgba(229,9,20,0.2)",
}

_PLOT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=C["txt"], family="'Outfit', sans-serif", size=13),
    margin=dict(l=10, r=10, t=40, b=10),
)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def load_movies() -> pd.DataFrame:
    if not os.path.exists(MOVIES_PATH):
        raise FileNotFoundError(
            f"movies.csv not found at:\n{MOVIES_PATH}\n\n"
            "Download from Kaggle and place inside the data/ folder."
        )
    df = pd.read_csv(MOVIES_PATH)
    df["movieId"] = df["movieId"].astype(int)

    if "genres" in df.columns:
        df["genres"] = df["genres"].fillna("").str.replace(",", "|", regex=False)
    if "overview"     not in df.columns: df["overview"]     = ""
    if "vote_average" not in df.columns: df["vote_average"] = 0.0
    if "poster_path"  not in df.columns: df["poster_path"]  = ""

    print(f"  Movies loaded: {len(df):,}")
    return df


@st.cache_data(show_spinner=False)
def load_ratings() -> pd.DataFrame:
    if not os.path.exists(RATINGS_PATH):
        print("  ratings.csv not found — collaborative filtering disabled.")
        return pd.DataFrame(columns=["userId", "movieId", "rating"])

    df = pd.read_csv(RATINGS_PATH)

    # Limit to 200k rows so SVD trains fast
    df = df.sample(min(len(df), 200_000), random_state=42)

    df["userId"]  = df["userId"].astype(int)
    df["movieId"] = df["movieId"].astype(int)
    df["rating"]  = df["rating"].astype(float)

    print(f"  Ratings loaded: {len(df):,}")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# WATCHLIST
# ═══════════════════════════════════════════════════════════════════════════════

# --- utils.py (Modified init_watchlist) ---

def init_watchlist():
    if "watchlist" not in st.session_state:
        if os.path.exists(WATCHLIST_FILE):
            try:
                with open(WATCHLIST_FILE, "r") as f:
                    data = json.load(f)
                    # Ensure data is a list to avoid iterable errors
                    st.session_state["watchlist"] = data if isinstance(data, list) else []
            except Exception:
                st.session_state["watchlist"] = []
        else:
            st.session_state["watchlist"] = []


def _persist_watchlist():
    """Save current watchlist to data/watchlist.json."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(st.session_state["watchlist"], f, indent=2)
    except Exception:
        pass


def add_to_watchlist(
    movie_id:  int,
    title:     str,
    poster_url: str  = "",
    rating:    float = 0.0,
    genres:    str   = "",
    overview:  str   = "",          # ← FIX: added overview parameter
) -> bool:
    """
    Add a movie to the watchlist.
    Returns False if it was already saved, True on success.
    Now stores overview so watchlist cards show descriptions.
    """
    init_watchlist()
    if any(m["movie_id"] == movie_id for m in st.session_state["watchlist"]):
        return False
    st.session_state["watchlist"].append({
        "movie_id":   movie_id,
        "title":      title,
        "poster_url": poster_url,
        "rating":     rating,
        "genres":     genres,
        "overview":   overview,     # ← FIX: was not stored before
    })
    _persist_watchlist()
    return True


def remove_from_watchlist(movie_id: int):
    init_watchlist()
    st.session_state["watchlist"] = [
        m for m in st.session_state["watchlist"]
        if m["movie_id"] != movie_id
    ]
    _persist_watchlist()


def in_watchlist(movie_id: int) -> bool:
    init_watchlist()
    return any(m["movie_id"] == movie_id for m in st.session_state["watchlist"])


def clear_watchlist():
    st.session_state["watchlist"] = []
    _persist_watchlist()


# ═══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ═══════════════════════════════════════════════════════════════════════════════

def chart_top_genres(movies_df: pd.DataFrame, n: int = 12) -> go.Figure:
    counts = {}
    for genres in movies_df["genres"].dropna():
        for g in str(genres).split("|"):
            g = g.strip()
            if g and g != "(no genres listed)":
                counts[g] = counts.get(g, 0) + 1
    if not counts:
        return _empty("No genre data")

    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]
    labels, vals = zip(*top)

    fig = go.Figure(go.Bar(
        x=list(vals), y=list(labels), orientation="h",
        marker=dict(
            color=list(vals),
            colorscale=[[0, C["surf2"]], [0.5, C["pri"]], [1, C["acc"]]],
            showscale=False,
            line=dict(color="rgba(255,255,255,0.04)", width=1),
        ),
        text=list(vals), textposition="outside",
        textfont=dict(color=C["txt"], size=11),
        hovertemplate="%{y}: %{x} movies<extra></extra>",
    ))
    fig.update_layout(
        **_PLOT,
        title=dict(text="Top Genres", font=dict(size=15)),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)"),
        yaxis=dict(autorange="reversed"),
        height=420,
    )
    return fig


def chart_movies_per_year(movies_df: pd.DataFrame) -> go.Figure:
    df = movies_df.copy()
    if "year" not in df.columns:
        if "release_date" in df.columns:
            df["year"] = pd.to_datetime(df["release_date"], errors="coerce").dt.year
        else:
            return _empty("No year data")

    yc = df["year"].dropna().astype(int).value_counts().sort_index()
    yc = yc[(yc.index >= 1950) & (yc.index <= 2025)]

    fig = go.Figure(go.Scatter(
        x=yc.index, y=yc.values,
        mode="lines+markers",
        line=dict(color=C["pri"], width=2.5),
        marker=dict(color=C["acc"], size=4),
        fill="tozeroy",
        fillcolor="rgba(229,9,20,0.08)",
        hovertemplate="Year: %{x}<br>Movies: %{y}<extra></extra>",
    ))
    fig.update_layout(
        **_PLOT,
        title=dict(text="Movies Per Year", font=dict(size=15)),
        xaxis=dict(title="Year", showgrid=True, gridcolor="rgba(255,255,255,0.04)"),
        yaxis=dict(title="Count", showgrid=True, gridcolor="rgba(255,255,255,0.04)"),
        height=320,
    )
    return fig


def chart_rating_distribution(movies_df: pd.DataFrame) -> go.Figure:
    if "vote_average" not in movies_df.columns:
        return _empty("No rating data")
    vals = movies_df["vote_average"].dropna()
    vals = vals[vals > 0]

    fig = go.Figure(go.Histogram(
        x=vals, nbinsx=20,
        marker=dict(color=C["pri"],
                    line=dict(color="rgba(255,255,255,0.08)", width=1)),
        hovertemplate="Rating: %{x}<br>Count: %{y}<extra></extra>",
    ))
    fig.update_layout(
        **_PLOT,
        title=dict(text="Rating Distribution", font=dict(size=15)),
        xaxis=dict(title="Rating", showgrid=False),
        yaxis=dict(title="Count", showgrid=True, gridcolor="rgba(255,255,255,0.04)"),
        bargap=0.05, height=320,
    )
    return fig


def chart_top_movies(movies_df: pd.DataFrame, n: int = 10) -> go.Figure:
    if "vote_average" not in movies_df.columns:
        return _empty("No rating data")

    df = movies_df[movies_df["vote_average"] > 0].copy()
    if "vote_count" in df.columns:
        df = df[df["vote_count"] >= 50]
    top     = df.nlargest(n, "vote_average")
    titles  = [t[:34] + ("…" if len(t) > 34 else "") for t in top["title"]]
    ratings = top["vote_average"].round(1)

    fig = go.Figure(go.Bar(
        x=ratings, y=titles, orientation="h",
        marker=dict(
            color=ratings,
            colorscale=[[0, C["surf2"]], [0.5, "#FF6B35"], [1, C["acc"]]],
            showscale=False,
        ),
        text=[f"⭐ {r}" for r in ratings],
        textposition="outside",
        textfont=dict(color=C["acc"], size=11),
        hovertemplate="<b>%{y}</b><br>Rating: %{x}<extra></extra>",
    ))
    fig.update_layout(
        **_PLOT,
        title=dict(text=f"Top {n} Rated Movies", font=dict(size=15)),
        xaxis=dict(range=[0, 11], showgrid=True, gridcolor="rgba(255,255,255,0.04)"),
        yaxis=dict(autorange="reversed"),
        height=420,
    )
    return fig


def _empty(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False,
                       font=dict(size=14, color=C["muted"]))
    fig.update_layout(**_PLOT, xaxis=dict(visible=False),
                      yaxis=dict(visible=False), height=250)
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def star_display(rating) -> str:
    try:
        r = float(rating)
        return f"⭐ {r:.1f} / 10" if r > 0 else "Not rated"
    except Exception:
        return "Not rated"


def genre_tags(genres_str: str, max_n: int = 3) -> str:
    if not genres_str or str(genres_str) in ("nan", "", "N/A"):
        return ""
    parts = [g.strip() for g in str(genres_str).replace("|", ",").split(",")]
    return "  ·  ".join(p for p in parts[:max_n] if p)


def truncate(text: str, n: int = 160) -> str:
    t = str(text) if text else ""
    return t[:n] + "…" if len(t) > n else t