"""
test_app.py
===========
Run ALL functions to verify everything works before launching.
Usage:  python test_app.py
"""
import streamlit as st

# ✅ Mock session state for testing
if not hasattr(st, "session_state"):
    st.session_state = {}

if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = []
print("=" * 55)
print("  CineMatch Pro — Full Function Test")
print("=" * 55)

errors = []

# ── Test 1: Imports ───────────────────────────────────────
print("\n📦 Testing imports...")
try:
    from utils import (load_movies, load_ratings, init_watchlist,
                       add_to_watchlist, remove_from_watchlist,
                       in_watchlist, clear_watchlist,
                       chart_top_genres, chart_movies_per_year,
                       chart_rating_distribution, chart_top_movies,
                       star_display, genre_tags, truncate)
    print("  ✅ utils.py  — OK")
except Exception as e:
    print(f"  ❌ utils.py  — FAILED: {e}")
    errors.append("utils")

try:
    from recommender import build_recommender, MOOD_GENRE_MAP
    print("  ✅ recommender.py — OK")
except Exception as e:
    print(f"  ❌ recommender.py — FAILED: {e}")
    errors.append("recommender")

try:
    from api import get_poster_url, fetch_trending, fetch_movie_details
    print("  ✅ api.py — OK")
except Exception as e:
    print(f"  ❌ api.py — FAILED: {e}")
    errors.append("api")

try:
    from ui import inject_css, render_sidebar, movie_card, movie_grid
    print("  ✅ ui.py — OK")
except Exception as e:
    print(f"  ❌ ui.py — FAILED: {e}")
    errors.append("ui")

if errors:
    print(f"\n❌ Fix these files first: {errors}")
    exit(1)

# ── Test 2: Data loading ──────────────────────────────────
print("\n📂 Testing data loading...")
try:
    movies = load_movies()
    print(f"  ✅ movies.csv loaded — {len(movies):,} movies")
except Exception as e:
    print(f"  ❌ movies.csv FAILED: {e}")
    exit(1)

try:
    ratings = load_ratings()
    if len(ratings) == 0:
        print("  ⚠️  ratings.csv not found — collaborative filtering disabled (OK)")
    else:
        print(f"  ✅ ratings.csv loaded — {len(ratings):,} ratings")
except Exception as e:
    print(f"  ❌ ratings.csv FAILED: {e}")
    ratings = None

# ── Test 3: Model training ────────────────────────────────
print("\n🧠 Testing model training...")
try:
    model = build_recommender(movies, ratings if ratings is not None else None)
    print("  ✅ Model trained successfully")
except Exception as e:
    print(f"  ❌ Model training FAILED: {e}")
    exit(1)

# ── Test 4: Recommendations ───────────────────────────────
print("\n🎬 Testing recommendations...")
sample_title = movies["title"].iloc[0]
print(f"  Using seed movie: '{sample_title}'")

try:
    recs, explanation = model.recommend_by_movie(sample_title, n=5)
    if hasattr(recs, '__len__') and len(recs) > 0:
        print(f"  ✅ recommend_by_movie — {len(recs)} results")
        print(f"     Explanation: {explanation}")
    else:
        print("  ⚠️  recommend_by_movie returned 0 results")
except Exception as e:
    print(f"  ❌ recommend_by_movie FAILED: {e}")
    errors.append("recommend_by_movie")

# ── Test 5: Taste profile ─────────────────────────────────
try:
    top3 = movies["title"].head(3).tolist()
    taste_recs, taste_exp = model.recommend_by_taste(top3, n=5)
    print(f"  ✅ recommend_by_taste — {len(taste_recs)} results")
    print(f"     Seeds: {top3}")
except Exception as e:
    print(f"  ❌ recommend_by_taste FAILED: {e}")
    errors.append("recommend_by_taste")

# ── Test 6: Mood ──────────────────────────────────────────
print("\n🎭 Testing mood recommendations...")
for mood in list(MOOD_GENRE_MAP.keys())[:3]:
    try:
        mood_recs = model.recommend_by_mood(mood, n=5)
        print(f"  ✅ {mood} — {len(mood_recs)} movies")
    except Exception as e:
        print(f"  ❌ {mood} FAILED: {e}")
        errors.append(f"mood_{mood}")

# ── Test 7: AI Chat ───────────────────────────────────────
print("\n🤖 Testing AI chat...")
for query in ["dark thriller like Inception", "feel good comedy", "romantic movies"]:
    try:
        result  = model.chat_recommend(query, n=5)
        recs_df = result[0] if isinstance(result, tuple) else result
        count   = len(recs_df) if hasattr(recs_df, '__len__') else 0
        print(f"  ✅ '{query}' — {count} results")
    except Exception as e:
        print(f"  ❌ '{query}' FAILED: {e}")
        errors.append("chat")

# ── Test 8: Surprise Me ───────────────────────────────────
print("\n🎲 Testing Surprise Me...")
try:
    surprise = model.surprise_me()
    title    = surprise.get("title", "Unknown") if isinstance(surprise, dict) else str(surprise)
    print(f"  ✅ Surprise Me — '{title}'")
except Exception as e:
    print(f"  ❌ Surprise Me FAILED: {e}")
    errors.append("surprise_me")

# ── Test 9: Search ────────────────────────────────────────
print("\n🔍 Testing search...")
try:
    results = model.search("dark", n=5)
    print(f"  ✅ Search 'dark' — {len(results)} results")
except Exception as e:
    print(f"  ❌ Search FAILED: {e}")
    errors.append("search")

# ── Test 10: Charts ───────────────────────────────────────
print("\n📊 Testing charts...")
for name, fn in [
    ("chart_top_genres",          lambda: chart_top_genres(movies)),
    ("chart_movies_per_year",     lambda: chart_movies_per_year(movies)),
    ("chart_rating_distribution", lambda: chart_rating_distribution(movies)),
    ("chart_top_movies",          lambda: chart_top_movies(movies)),
]:
    try:
        fn()
        print(f"  ✅ {name} — OK")
    except Exception as e:
        print(f"  ❌ {name} FAILED: {e}")
        errors.append(name)

# ── Test 11: Watchlist ────────────────────────────────────
print("\n📌 Testing watchlist...")
try:
    import streamlit as st

    # ── FIX: Manually initialise session_state for test context ──────────────
    # When running outside `streamlit run`, session_state exists but is empty.
    # We seed the watchlist key directly so the watchlist functions work.
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = []

    # Now run the same logic as the real app
    add_to_watchlist(999, "Test Movie", "http://test.com/p.jpg", 8.5, "Action")
    assert in_watchlist(999), "Should be in watchlist after add"

    remove_from_watchlist(999)
    assert not in_watchlist(999), "Should not be in watchlist after remove"

    print("  ✅ Watchlist add/remove — OK")
except Exception as e:
    print(f"  ❌ Watchlist FAILED: {e}")
    errors.append("watchlist")

# ── Test 12: OMDB API ─────────────────────────────────────
print("\n🌐 Testing OMDB API...")
try:
    import requests
    r    = requests.get("http://www.omdbapi.com/",
                        params={"apikey": "68e4b073", "t": "Inception"}, timeout=6)
    data = r.json()
    if data.get("Response") == "True":
        print(f"  ✅ OMDB API — '{data['Title']}' poster fetched")
    else:
        print(f"  ⚠️  OMDB API responded but movie not found: {data.get('Error')}")
except Exception as e:
    print(f"  ⚠️  OMDB API — Could not connect (check internet): {e}")

# ── Test 13: Helper functions ─────────────────────────────
print("\n🔧 Testing helper functions...")
try:
    assert star_display(7.5) == "⭐ 7.5 / 10"
    assert star_display(0)   == "Not rated"
    assert genre_tags("Action|Drama|Comedy") == "Action  ·  Drama  ·  Comedy"
    assert truncate("A" * 200, 160).endswith("…")
    print("  ✅ star_display   — OK")
    print("  ✅ genre_tags     — OK")
    print("  ✅ truncate       — OK")
except Exception as e:
    print(f"  ❌ Helper functions FAILED: {e}")
    errors.append("helpers")

# ── Final Report ──────────────────────────────────────────
print("\n" + "=" * 55)
if not errors:
    print("  🎉 ALL TESTS PASSED — App is ready!")
    print("  Run:  streamlit run app.py")
else:
    print(f"  ❌ {len(errors)} issue(s) found:")
    for e in errors:
        print(f"     • {e}")
    print("\n  Fix these and run test again.")
print("=" * 55)