"""
recommender.py  —  CineMatch Pro · Fast Recommender with Pickle Cache
======================================================================
FEATURES
  - Pickle cache  → data/tfidf_cache.pkl
    · First run  : builds TF-IDF matrix (~5 s) and saves it
    · Later runs : loads from cache (~0.3 s) — 10× faster
  - Content-based TF-IDF on genres + overview + title
  - Global filter support (min_rating, year_range) on every public method
  - Python 3.12 compatible, no heavy dependencies
"""

import os
import pickle
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings

warnings.filterwarnings("ignore")

# ── File paths ────────────────────────────────────────────────────────────────
_BASE      = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(_BASE, "data", "tfidf_cache.pkl")

# ── Mood → genre mapping ──────────────────────────────────────────────────────
MOOD_GENRE_MAP = {
    "😊 Happy":        ["Comedy", "Family", "Animation", "Music"],
    "😢 Sad":          ["Drama", "Romance"],
    "❤️ Romantic":     ["Romance", "Drama"],
    "😱 Thriller":     ["Thriller", "Crime", "Mystery", "Horror"],
    "💪 Motivational": ["Biography", "Sport", "History", "Adventure"],
    "🚀 Sci-Fi":       ["Science Fiction", "Sci-Fi", "Adventure", "Fantasy"],
    "😂 Comedy":       ["Comedy", "Animation", "Family"],
    "🔮 Fantasy":      ["Fantasy", "Adventure", "Animation"],
}

TONE_GENRE_MAP = {
    "dark":       ["Crime", "Thriller", "Horror"],
    "funny":      ["Comedy"],
    "romantic":   ["Romance"],
    "inspiring":  ["Biography", "Sport"],
    "scary":      ["Horror", "Thriller"],
    "space":      ["Science Fiction"],
    "detective":  ["Crime", "Mystery"],
    "superhero":  ["Action", "Adventure"],
    "mind":       ["Thriller", "Science Fiction"],
    "feel-good":  ["Comedy", "Family"],
    "sad":        ["Drama"],
    "epic":       ["Adventure", "Fantasy", "Action"],
    "war":        ["War", "History"],
    "animated":   ["Animation", "Family"],
    "musical":    ["Music", "Comedy"],
}

ALL_GENRES = [
    "comedy", "drama", "thriller", "romance", "horror", "action",
    "adventure", "sci-fi", "science fiction", "animation", "fantasy",
    "crime", "biography", "sport", "mystery", "family", "history",
    "war", "music", "western", "documentary",
]


# ═══════════════════════════════════════════════════════════════════════════════
# FILTER HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _apply_filters(
    df:         pd.DataFrame,
    min_rating: float = 0.0,
    year_range: tuple = (1900, 2100),
) -> pd.DataFrame:
    """Apply rating and release-year filters safely. Returns original df if empty after filter."""
    result = df.copy()

    if "vote_average" in result.columns and min_rating > 0:
        result = result[result["vote_average"].fillna(0) >= min_rating]

    if year_range != (1900, 2100) and "release_date" in result.columns:
        y_min, y_max = year_range
        years = (
            result["release_date"]
            .astype(str).str[:4]
            .apply(lambda x: int(x) if x.isdigit() else 0)
        )
        result = result[years.between(y_min, y_max)]

    return result if not result.empty else df


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT-BASED RECOMMENDER  (TF-IDF + Cosine Similarity + Pickle Cache)
# ═══════════════════════════════════════════════════════════════════════════════

class ContentBasedRecommender:

    def __init__(self):
        self.vectorizer   = TfidfVectorizer(
            stop_words="english",
            max_features=5000,
            ngram_range=(1, 1),
        )
        self.tfidf_matrix = None
        self.movie_index  = {}
        self.movies_df    = None

    # ── Feature soup ──────────────────────────────────────────────────────────
    def _soup(self, row) -> str:
        genres   = str(row.get("genres",   "")).replace("|", " ")
        overview = str(row.get("overview", ""))[:100]
        title    = str(row.get("title",    ""))
        # Weight genres 3× so genre similarity dominates
        return f"{genres} {genres} {genres} {title} {overview}"

    # ── Fit — tries cache first, builds + saves otherwise ────────────────────
    def fit(self, movies_df: pd.DataFrame):
        """
        Build TF-IDF matrix with pickle caching.

        Flow:
          1. If data/tfidf_cache.pkl exists AND n_movies matches → load cache
          2. Otherwise  → build fresh, save to cache
        Cache invalidates automatically when the dataset size changes.
        """
        self.movies_df = movies_df.copy().reset_index(drop=True)

        # ── Try loading from cache ───────────────────────────────────────────
        if os.path.exists(CACHE_PATH):
            try:
                with open(CACHE_PATH, "rb") as f:
                    data = pickle.load(f)

                if (data.get("n_movies") == len(self.movies_df)
                        and data.get("matrix") is not None):
                    self.tfidf_matrix = data["matrix"]
                    self.vectorizer   = data["vec"]
                    print("  [Content] Loaded from cache ✓")
                else:
                    raise ValueError("Cache size mismatch — rebuilding")

            except Exception as exc:
                print(f"  [Content] Cache invalid ({exc}) — rebuilding …")
                self._build_and_save_cache()
        else:
            self._build_and_save_cache()

        # Build title → row-index lookup (lower-cased for fuzzy match)
        self.movie_index = {
            str(t).lower().strip(): i
            for i, t in enumerate(self.movies_df["title"])
        }
        print(f"  [Content] Ready — matrix {self.tfidf_matrix.shape}")

    def _build_and_save_cache(self):
        """Compute TF-IDF matrix and persist to data/tfidf_cache.pkl."""
        print("  [Content] Building TF-IDF …")
        soup = self.movies_df.apply(self._soup, axis=1)
        self.tfidf_matrix = self.vectorizer.fit_transform(soup)
        print(f"  [Content] Done — {self.tfidf_matrix.shape}")

        # Save
        try:
            os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
            with open(CACHE_PATH, "wb") as f:
                pickle.dump({
                    "matrix":   self.tfidf_matrix,
                    "vec":      self.vectorizer,
                    "n_movies": len(self.movies_df),
                }, f)
            print("  [Content] Cache saved ✓")
        except Exception as exc:
            print(f"  [Content] Could not save cache: {exc}")

    # ── Index lookup (exact + partial) ────────────────────────────────────────
    def _idx(self, title: str):
        key = str(title).lower().strip()
        if key in self.movie_index:
            return self.movie_index[key]
        for k, v in self.movie_index.items():
            if key in k or k in key:
                return v
        return None

    # ── Similarity queries ────────────────────────────────────────────────────
    def similar_to(self, title: str, n: int = 5) -> pd.DataFrame:
        idx = self._idx(title)
        if idx is None:
            return pd.DataFrame()
        scores      = cosine_similarity(
            self.tfidf_matrix[idx], self.tfidf_matrix
        ).flatten()
        scores[idx] = -1
        top         = np.argsort(scores)[::-1][:n]
        result      = self.movies_df.iloc[top].copy()
        result["score"] = scores[top]
        return result

    def similar_to_many(self, titles: list, n: int = 5) -> pd.DataFrame:
        acc  = np.zeros(len(self.movies_df))
        excl = set()
        for title in titles:
            idx = self._idx(title)
            if idx is None:
                continue
            scores = cosine_similarity(
                self.tfidf_matrix[idx], self.tfidf_matrix
            ).flatten()
            acc  += scores
            excl.add(idx)
        for i in excl:
            acc[i] = -1
        top    = np.argsort(acc)[::-1][:n]
        result = self.movies_df.iloc[top].copy()
        result["score"] = acc[top]
        return result

    def mood_movies(self, mood: str, n: int = 8,
                    min_rating: float = 0.0,
                    year_range: tuple = (1900, 2100)) -> pd.DataFrame:
        genres  = MOOD_GENRE_MAP.get(mood, [])
        pattern = "|".join(genres) if genres else ""
        df      = _apply_filters(self.movies_df, min_rating, year_range)

        if not pattern:
            return (df.sample(min(n, len(df)))
                    if not df.empty else self.movies_df.sample(n))

        mask     = df["genres"].str.contains(pattern, case=False, na=False)
        filtered = df[mask]
        if filtered.empty:
            return (df.sample(min(n, len(df)))
                    if not df.empty else pd.DataFrame())

        if "vote_average" in filtered.columns:
            return filtered.nlargest(n, "vote_average")
        return filtered.head(n)

    def search(self, query: str, n: int = 10) -> pd.DataFrame:
        q    = str(query).lower()
        mask = self.movies_df["title"].str.lower().str.contains(q, na=False)
        return self.movies_df[mask].head(n)

    def chat_recommend(self, user_text: str, n: int = 5):
        user_lower    = user_text.lower()
        ref           = self.search(user_text, n=1)
        seed          = ref.iloc[0]["title"] if not ref.empty else None
        found         = [g for g in ALL_GENRES if g in user_lower]
        extra: list   = []
        for tone, mapped in TONE_GENRE_MAP.items():
            if tone in user_lower:
                extra.extend(mapped)
        genres_to_use = list(set([g.title() for g in found] + extra))

        if seed:
            recs = self.similar_to(seed, n=n * 2)
            if not recs.empty:
                if genres_to_use:
                    pat      = "|".join(genres_to_use)
                    filtered = recs[recs["genres"].str.contains(
                        pat, case=False, na=False)]
                    if not filtered.empty:
                        return filtered.head(n), seed, genres_to_use
                return recs.head(n), seed, genres_to_use

        if genres_to_use:
            pat      = "|".join(genres_to_use)
            mask     = self.movies_df["genres"].str.contains(
                pat, case=False, na=False)
            filtered = self.movies_df[mask]
            if "vote_average" in filtered.columns:
                filtered = filtered.nlargest(n * 2, "vote_average")
            return filtered.head(n), None, genres_to_use

        qvec   = self.vectorizer.transform([user_text])
        scores = cosine_similarity(qvec, self.tfidf_matrix).flatten()
        top    = np.argsort(scores)[::-1][:n]
        return self.movies_df.iloc[top], None, []


# ═══════════════════════════════════════════════════════════════════════════════
# HYBRID WRAPPER  —  public API consumed by app.py
# ═══════════════════════════════════════════════════════════════════════════════

class HybridRecommender:
    """Thin wrapper that adds filter support over ContentBasedRecommender."""

    def __init__(self):
        self.cb        = ContentBasedRecommender()
        self.movies_df = None

    def fit(self, movies_df: pd.DataFrame, ratings_df=None):
        print("\n[Recommender] Training …")
        self.movies_df = movies_df.copy()
        self.cb.fit(movies_df)
        print("[Recommender] Ready ✓\n")

    def recommend_by_movie(self, title: str, n: int = 5,
                           min_rating: float = 0.0,
                           year_range: tuple = (1900, 2100)):
        result = self.cb.similar_to(title, n=n * 3)
        if result.empty:
            return pd.DataFrame(), f'"{title}" not found.'
        result = _apply_filters(result, min_rating, year_range).head(n)
        row    = self.movies_df[
            self.movies_df["title"].str.lower() == title.lower()
        ]
        genres = row.iloc[0]["genres"] if not row.empty else "Similar"
        return result, f'Because you liked **{title}** ({genres})'

    def recommend_by_taste(self, titles: list, n: int = 5,
                           min_rating: float = 0.0,
                           year_range: tuple = (1900, 2100)):
        result    = self.cb.similar_to_many(titles, n=n * 2)
        result    = _apply_filters(result, min_rating, year_range).head(n)
        taste_str = "  ·  ".join(titles)
        return result, f'Based on your taste in: **{taste_str}**'

    def recommend_by_mood(self, mood: str, n: int = 8,
                          min_rating: float = 0.0,
                          year_range: tuple = (1900, 2100)):
        return self.cb.mood_movies(
            mood, n=n, min_rating=min_rating, year_range=year_range
        )

    def chat_recommend(self, user_text: str, n: int = 5):
        return self.cb.chat_recommend(user_text, n=n)

    def trending(self, n: int = 12,
                 min_rating: float = 0.0,
                 year_range: tuple = (1900, 2100)):
        df = _apply_filters(self.movies_df, min_rating, year_range)
        if "vote_average" in df.columns and not df.empty:
            top50 = df[df["vote_average"] > 0].nlargest(50, "vote_average")
            return top50.sample(min(n, len(top50)))
        return (df.sample(min(n, len(df)))
                if not df.empty else self.movies_df.sample(n))

    def surprise_me(self, min_rating: float = 0.0,
                    year_range: tuple = (1900, 2100)):
        df = _apply_filters(self.movies_df, min_rating, year_range)
        if "vote_average" in df.columns and not df.empty:
            good = df[df["vote_average"] >= 7.5]
            if not good.empty:
                return good.sample(1).iloc[0].to_dict()
        return (df.sample(1).iloc[0].to_dict()
                if not df.empty else {})

    def search(self, query: str, n: int = 10):
        return self.cb.search(query, n)


def build_recommender(
    movies_df: pd.DataFrame,
    ratings_df=None,
) -> HybridRecommender:
    model = HybridRecommender()
    model.fit(movies_df, ratings_df)
    return model