"""
app.py
======
CineMatch Pro — Netflix-style AI Movie Recommendation App
Run: streamlit run app.py

Pages:
  🏠 Home        — Trending (OMDB), Browse by genre, Surprise Me
  🎬 Recommend   — By movie title + 3-movie taste profile
  🎭 Mood        — 8 moods → genre → top movies
  🤖 AI Chat     — Natural language movie requests
  📊 Dashboard   — Analytics: genres, year trends, ratings, top movies
  📌 Watchlist   — Saved movies with JSON persistence
"""

import streamlit as st
import pandas as pd

# ── Page config — MUST be first Streamlit call ────────────────────────────────
st.set_page_config(
    page_title="CineMatch Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Local imports ─────────────────────────────────────────────────────────────
from recommender import build_recommender, MOOD_GENRE_MAP
from utils import (
    load_movies, load_ratings, init_watchlist,
    remove_from_watchlist, clear_watchlist, C,
    chart_top_genres, chart_movies_per_year,
    chart_rating_distribution, chart_top_movies,
)
from ui import (
    inject_css, render_sidebar, hero_banner, section_header,
    movie_grid, movie_card, explanation_pill, divider, surprise_card,
)
from api import get_poster_url, fetch_trending, PLACEHOLDER

# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════════

inject_css()
init_watchlist()

# Session state defaults
for _k, _v in {
    "chat_history":   [],
    "selected_mood":  None,
    "surprise_movie": None,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Cached model (trains once, shared across sessions) ────────────────────────
@st.cache_resource(show_spinner=False)
def get_model():
    movies_df  = load_movies()
    ratings_df = load_ratings()
    model      = build_recommender(
        movies_df,
        ratings_df if not ratings_df.empty else None,
    )
    return model, movies_df, ratings_df


try:
    with st.spinner("🎬 Starting CineMatch Pro …"):
        model, movies_df, ratings_df = get_model()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.info(
        "**Fix:**\n"
        "1. Download `movies.csv` and `ratings.csv` from Kaggle.\n"
        "2. Put both files in the `data/` folder.\n"
        "3. Refresh the page."
    )
    st.stop()
except Exception as exc:
    st.error(f"Startup error: {exc}")
    st.stop()

all_titles = sorted(movies_df["title"].dropna().unique().tolist())
page       = render_sidebar()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — HOME
# ═══════════════════════════════════════════════════════════════════════════════

def page_home():
    hero_banner(
        "CineMatch Pro",
        "AI-powered recommendations tailored to your taste. "
        "Discover, explore, and build your personal watchlist.",
    )

    # KPI row
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("🎬 Movies",   f"{len(movies_df):,}")
    with k2: st.metric("⭐ Ratings",  f"{len(ratings_df):,}" if not ratings_df.empty else "N/A")
    with k3:
        genre_set = set()
        for g in movies_df["genres"].dropna():
            genre_set.update(str(g).split("|"))
        st.metric("🎭 Genres", len(genre_set))
    with k4: st.metric("📌 Watchlist", len(st.session_state.get("watchlist", [])))

    divider()

    # Surprise Me
    col_t, col_b = st.columns([4, 1])
    with col_t:
        section_header("🎲 Surprise Me", "One great movie, hand-picked by the AI")
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🎲 Surprise Me!", use_container_width=True):
            st.session_state["surprise_movie"] = model.surprise_me()
            st.rerun()

    if st.session_state["surprise_movie"]:
        surprise_card(st.session_state["surprise_movie"])
        divider()

    # Live trending from OMDB
    omdb_trending = fetch_trending(n=8)
    if omdb_trending:
        section_header("🔥 Trending Now", "Fetched live via OMDB API")
        movie_grid(omdb_trending, cols=4)
        divider()

    # Top-rated from dataset
    section_header("⭐ Top Rated")
    movie_grid(model.trending(n=8), cols=4)
    divider()

    # Browse by genre tabs
    section_header("🎭 Browse by Genre")
    genre_list = ["Action", "Comedy", "Drama", "Thriller",
                  "Science Fiction", "Romance", "Horror", "Animation"]
    tabs = st.tabs(genre_list[:6])
    for tab, genre in zip(tabs, genre_list[:6]):
        with tab:
            mask = movies_df["genres"].str.contains(genre, case=False, na=False)
            gdf  = movies_df[mask]
            if "vote_average" in gdf.columns:
                gdf = gdf.nlargest(8, "vote_average")
            else:
                gdf = gdf.head(8)
            movie_grid(gdf, cols=4)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — RECOMMEND
# ═══════════════════════════════════════════════════════════════════════════════

def page_recommend():
    hero_banner(
        "Movie Recommendations",
        "Choose a movie you love — or share your top 3 — and we find your next obsession.",
    )

    tab1, tab2 = st.tabs(["🎬 By Movie Title", "🎯 3-Movie Taste Profile"])

    # Tab 1 — single movie
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        cs, cn = st.columns([3, 1])
        with cs:
            selected = st.selectbox(
                "Pick a movie:",
                [""] + all_titles,
                format_func=lambda x: "🔍 Type to search…" if x == "" else x,
            )
        with cn:
            n_recs = st.select_slider("Results", [3, 5, 8, 10], value=5)

        if selected:
            with st.spinner(f"Analysing **{selected}** …"):
                result, explanation = model.recommend_by_movie(selected, n=n_recs)

            if isinstance(result, pd.DataFrame) and not result.empty:
                explanation_pill(explanation)
                section_header(f"Because You Watched: {selected}")
                movie_grid(result, cols=4)
            else:
                st.warning(f'"{selected}" not found. Try another title.')

    # Tab 2 — taste profile
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:0.88rem;color:#9999BB;margin-bottom:1rem;'>"
            "Select 3 movies that define your taste. "
            "We'll blend them into a personal profile.</div>",
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            m1 = st.selectbox("Favourite #1", [""] + all_titles, key="t1",
                              format_func=lambda x: "Pick…" if x == "" else x)
        with c2:
            m2 = st.selectbox("Favourite #2", [""] + all_titles, key="t2",
                              format_func=lambda x: "Pick…" if x == "" else x)
        with c3:
            m3 = st.selectbox("Favourite #3", [""] + all_titles, key="t3",
                              format_func=lambda x: "Pick…" if x == "" else x)

        chosen = [x for x in [m1, m2, m3] if x]
        if st.button("🎯 Build My Profile", use_container_width=True) and chosen:
            with st.spinner("Building taste profile …"):
                result, explanation = model.recommend_by_taste(chosen, n=5)
            if not result.empty:
                explanation_pill(explanation)
                section_header("Your Personalised Picks")
                movie_grid(result, cols=4)
            else:
                st.warning("Try different movies.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — MOOD
# ═══════════════════════════════════════════════════════════════════════════════

def page_mood():
    hero_banner(
        "Mood-Based Discovery",
        "Tell us how you feel. We'll match you with the perfect movie.",
    )

    section_header("How Are You Feeling Right Now?")
    moods = list(MOOD_GENRE_MAP.keys())

    btn_cols = st.columns(4)
    for i, mood in enumerate(moods):
        with btn_cols[i % 4]:
            active = st.session_state["selected_mood"] == mood
            label  = f"{'✓ ' if active else ''}{mood}"
            if st.button(label, key=f"mood_{mood}", use_container_width=True):
                st.session_state["selected_mood"] = mood
                st.rerun()

    mood = st.session_state["selected_mood"]
    if not mood:
        st.markdown(
            "<div style='text-align:center;color:#9999BB;"
            "padding:2.5rem;font-size:0.95rem;'>"
            "👆 Choose a mood above</div>",
            unsafe_allow_html=True,
        )
        return

    divider()
    with st.spinner(f"Finding {mood} movies …"):
        mood_movies = model.recommend_by_mood(mood, n=8)

    genres_str = "  ·  ".join(MOOD_GENRE_MAP.get(mood, []))
    explanation_pill(f"**{mood}** → Genres: {genres_str}")
    section_header(f"{mood} Picks For You")
    movie_grid(mood_movies, cols=4)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — AI CHAT
# ═══════════════════════════════════════════════════════════════════════════════

def page_chat():
    hero_banner(
        "AI Movie Chat",
        "Describe what you want in plain English — genre, mood, reference movie. "
        "The AI does the rest.",
    )

    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(
                f"<div class='chat-user'>👤 {msg['text']}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='chat-bot'>"
                f"<div class='lbl'>🤖 CineMatch AI</div>"
                f"{msg['text']}</div>",
                unsafe_allow_html=True,
            )
            if msg.get("movies"):
                movie_grid(msg["movies"], cols=4)

    st.markdown("<br>", unsafe_allow_html=True)
    divider()

    st.markdown(
        "<div style='font-size:0.78rem;color:#9999BB;margin-bottom:6px;'>"
        "💡 Try:</div>",
        unsafe_allow_html=True,
    )
    suggestions = [
        "Dark thriller like Inception",
        "Feel-good comedy for tonight",
        "Epic sci-fi space movies",
        "Romantic movies like Titanic",
    ]
    sc = st.columns(len(suggestions))
    for i, sug in enumerate(suggestions):
        with sc[i]:
            if st.button(sug, key=f"s_{i}", use_container_width=True):
                _process_chat(sug)
                st.rerun()

    ci, cb = st.columns([5, 1])
    with ci:
        user_input = st.text_input(
            "msg", placeholder="e.g. 'Dark thriller like The Dark Knight'…",
            label_visibility="collapsed", key="chat_inp",
        )
    with cb:
        if st.button("Send →", use_container_width=True) and user_input.strip():
            _process_chat(user_input.strip())
            st.rerun()

    if st.session_state["chat_history"]:
        if st.button("🗑 Clear Chat"):
            st.session_state["chat_history"] = []
            st.rerun()


def _process_chat(text: str):
    st.session_state["chat_history"].append({"role": "user", "text": text})

    result = model.chat_recommend(text, n=5)
    recs_df, seed, genres_found = (result if isinstance(result, tuple)
                                   else (result, None, []))

    if seed:
        resp = f"Based on <b>{seed}</b>, here are movies you'll love:"
    elif genres_found:
        resp = f"Great <b>{', '.join(genres_found[:3])}</b> picks for you:"
    else:
        resp = "Here are some movies you might enjoy:"

    movies_list = []
    if hasattr(recs_df, "iterrows"):
        for _, row in recs_df.iterrows():
            movies_list.append({
                "movie_id":   int(row.get("movieId", 0)),
                "title":      row.get("title", ""),
                "poster_url": get_poster_url(
                    title=row.get("title", ""),
                    poster_path=row.get("poster_path", ""),
                ),
                "rating":     row.get("vote_average", 0),
                "genres":     row.get("genres", ""),
                "overview":   row.get("overview", ""),   # ← included for watchlist
            })

    if not movies_list:
        resp = "Sorry, I couldn't find matching movies. Try rephrasing."

    st.session_state["chat_history"].append({
        "role": "bot", "text": resp, "movies": movies_list,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def page_dashboard():
    hero_banner(
        "Analytics Dashboard",
        "Explore the dataset — genres, year trends, ratings, and top-performing movies.",
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Total Movies",  f"{len(movies_df):,}")
    with k2: st.metric("Total Ratings", f"{len(ratings_df):,}" if not ratings_df.empty else "N/A")
    with k3:
        avg = movies_df["vote_average"].mean() if "vote_average" in movies_df.columns else 0
        st.metric("Avg Rating", f"{avg:.2f} ⭐")
    with k4:
        gs = set()
        for g in movies_df["genres"].dropna(): gs.update(str(g).split("|"))
        st.metric("Unique Genres", len(gs))

    divider()

    section_header("Genre & Year Analysis")
    ca, cb_ = st.columns(2)
    with ca:
        st.plotly_chart(chart_top_genres(movies_df),
                        use_container_width=True, config={"displayModeBar": False})
    with cb_:
        st.plotly_chart(chart_movies_per_year(movies_df),
                        use_container_width=True, config={"displayModeBar": False})

    divider()
    section_header("Ratings & Top Movies")
    cc, cd = st.columns(2)
    with cc:
        st.plotly_chart(chart_rating_distribution(movies_df),
                        use_container_width=True, config={"displayModeBar": False})
    with cd:
        st.plotly_chart(chart_top_movies(movies_df),
                        use_container_width=True, config={"displayModeBar": False})

    divider()
    section_header("📋 Dataset Explorer")
    with st.expander("Browse movies", expanded=False):
        cols_show = [c for c in
                     ["title", "genres", "vote_average", "release_date", "overview"]
                     if c in movies_df.columns]
        q  = st.text_input("Search title:", placeholder="e.g. Batman", key="ds_q")
        df = movies_df[cols_show]
        if q:
            df = df[df["title"].str.lower().str.contains(q.lower(), na=False)]
        st.dataframe(df.head(100), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — WATCHLIST
# ═══════════════════════════════════════════════════════════════════════════════

def page_watchlist():
    hero_banner("My Watchlist", "Your personal saved movie collection.")

    wl = st.session_state.get("watchlist", [])

    if not wl:
        st.markdown(
            "<div style='text-align:center;padding:3rem;color:#9999BB;'>"
            "<div style='font-size:3.5rem;'>📌</div>"
            "<div style='font-size:1.1rem;margin-top:0.8rem;'>"
            "Your watchlist is empty.</div>"
            "<div style='font-size:0.82rem;margin-top:0.4rem;'>"
            "Browse movies and click <b>+ Watchlist</b> to save them here.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"<div style='font-size:0.88rem;color:#9999BB;margin-bottom:1.2rem;'>"
        f"📌 {len(wl)} movie{'s' if len(wl) != 1 else ''} saved</div>",
        unsafe_allow_html=True,
    )

    grid = st.columns(4)
    for i, movie in enumerate(wl):
        with grid[i % 4]:
            # movie_card renders the card + ✓ badge; no watchlist button needed
            movie_card(movie, show_wl_btn=False)
            if st.button("🗑 Remove", key=f"rm_{movie['movie_id']}_{i}",
                         use_container_width=True):
                remove_from_watchlist(movie["movie_id"])
                st.toast(f"Removed **{movie['title']}**")
                st.rerun()

    divider()
    if st.button("🗑 Clear Entire Watchlist"):
        clear_watchlist()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

{
    "🏠  Home":      page_home,
    "🎬  Recommend": page_recommend,
    "🎭  Mood":      page_mood,
    "🤖  AI Chat":   page_chat,
    "📊  Dashboard": page_dashboard,
    "📌  Watchlist": page_watchlist,
}.get(page, page_home)()