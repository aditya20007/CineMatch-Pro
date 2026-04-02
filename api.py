"""
api.py
======
OMDB API integration — fetches real movie posters, ratings, and plot.
API Key is already configured below.
Free OMDB key: http://www.omdbapi.com/apikey.aspx
"""

import requests
import streamlit as st

# ── OMDB Configuration ────────────────────────────────────────────────────────
OMDB_BASE    = "http://www.omdbapi.com/"
OMDB_API_KEY = "68e4b073"   # ✅ Your OMDB API key — already set!
PLACEHOLDER  = "https://via.placeholder.com/300x450/1a1a2e/E50914?text=No+Poster"


# ── Fetch single movie details by title ───────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_movie_details(title: str) -> dict:
    """
    Fetch poster, rating, plot from OMDB by movie title.
    Returns dict with poster_url, rating, plot, year, genre, director, actors.
    Returns empty dict on any error so app never crashes.
    """
    if not title or not title.strip():
        return {}
    try:
        params = {
            "apikey": OMDB_API_KEY,
            "t":      title.strip(),
            "plot":   "short",
            "r":      "json",
        }
        resp = requests.get(OMDB_BASE, params=params, timeout=6)
        if resp.status_code != 200:
            return {}

        data = resp.json()
        if data.get("Response") == "False":
            return {}

        # Parse poster
        poster = data.get("Poster", "")
        if not poster or poster == "N/A":
            poster = PLACEHOLDER

        # Parse IMDb rating safely
        try:
            imdb_rating = float(data.get("imdbRating", "0").replace(",", "."))
        except (ValueError, AttributeError):
            imdb_rating = 0.0

        return {
            "poster_url":  poster,
            "rating":      imdb_rating,
            "plot":        data.get("Plot", "No plot available."),
            "year":        data.get("Year", ""),
            "genre":       data.get("Genre", ""),
            "runtime":     data.get("Runtime", ""),
            "director":    data.get("Director", ""),
            "actors":      data.get("Actors", ""),
            "imdb_rating": imdb_rating,
            "awards":      data.get("Awards", ""),
            "box_office":  data.get("BoxOffice", ""),
        }
    except Exception:
        return {}


# ── Fetch trending (curated list via OMDB) ────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=7200)
def fetch_trending(n: int = 12) -> list:
    """
    OMDB has no trending endpoint, so we fetch a curated list of
    popular movies using their titles. Cached for 2 hours.
    """
    popular_titles = [
        "Inception", "Interstellar", "The Dark Knight", "Avengers: Endgame",
        "Parasite", "Dune", "Oppenheimer", "The Shawshank Redemption",
        "Pulp Fiction", "The Godfather", "Fight Club", "Forrest Gump",
        "The Matrix", "Gladiator", "Joker", "1917",
    ][:n]

    results = []
    for title in popular_titles:
        details = fetch_movie_details(title)
        if details:
            results.append({
                "title":      title,
                "poster_url": details.get("poster_url", PLACEHOLDER),
                "rating":     details.get("imdb_rating", 0),
                "overview":   details.get("plot", "")[:200],
                "genres":     details.get("genre", ""),
                "movie_id":   0,
            })
    return results


# ── Get poster URL ────────────────────────────────────────────────────────────
def get_poster_url(title: str = "", poster_path: str = "") -> str:
    """
    Try to get a real poster from OMDB.
    Falls back to placeholder if not found.
    """
    # Already a full URL from the CSV? Use it directly.
    if poster_path and str(poster_path).startswith("http"):
        return str(poster_path)

    if title:
        details = fetch_movie_details(title)
        poster  = details.get("poster_url", "")
        if poster and poster != PLACEHOLDER:
            return poster

    return PLACEHOLDER