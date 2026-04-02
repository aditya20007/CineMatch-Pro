import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings

warnings.filterwarnings("ignore")

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

    def _soup(self, row):
        genres   = str(row.get("genres", "")).replace("|", " ")
        overview = str(row.get("overview", ""))[:100]
        title    = str(row.get("title", ""))
        return f"{genres} {genres} {genres} {title} {overview}"

    def fit(self, movies_df):
        print("  [Content] Building TF-IDF ...")
        self.movies_df   = movies_df.copy().reset_index(drop=True)
        soup             = self.movies_df.apply(self._soup, axis=1)
        self.tfidf_matrix = self.vectorizer.fit_transform(soup)
        self.movie_index  = {
            str(t).lower().strip(): i
            for i, t in enumerate(self.movies_df["title"])
        }
        print(f"  [Content] Done — {self.tfidf_matrix.shape}")

    def _idx(self, title):
        key = str(title).lower().strip()
        if key in self.movie_index:
            return self.movie_index[key]
        for k, v in self.movie_index.items():
            if key in k or k in key:
                return v
        return None

    def similar_to(self, title, n=5):
        idx = self._idx(title)
        if idx is None:
            return pd.DataFrame()
        scores    = cosine_similarity(self.tfidf_matrix[idx], self.tfidf_matrix).flatten()
        scores[idx] = -1
        top       = np.argsort(scores)[::-1][:n]
        result    = self.movies_df.iloc[top].copy()
        result["score"] = scores[top]
        return result

    def similar_to_many(self, titles, n=5):
        acc  = np.zeros(len(self.movies_df))
        excl = set()
        for title in titles:
            idx = self._idx(title)
            if idx is None:
                continue
            scores = cosine_similarity(self.tfidf_matrix[idx], self.tfidf_matrix).flatten()
            acc   += scores
            excl.add(idx)
        for i in excl:
            acc[i] = -1
        top    = np.argsort(acc)[::-1][:n]
        result = self.movies_df.iloc[top].copy()
        result["score"] = acc[top]
        return result

    def mood_movies(self, mood, n=8):
        genres  = MOOD_GENRE_MAP.get(mood, [])
        pattern = "|".join(genres) if genres else ""
        if not pattern:
            return self.movies_df.sample(n)
        mask     = self.movies_df["genres"].str.contains(pattern, case=False, na=False)
        filtered = self.movies_df[mask]
        if filtered.empty:
            return self.movies_df.sample(n)
        if "vote_average" in filtered.columns:
            return filtered.nlargest(n, "vote_average")
        return filtered.head(n)

    def search(self, query, n=10):
        q    = str(query).lower()
        mask = self.movies_df["title"].str.lower().str.contains(q, na=False)
        return self.movies_df[mask].head(n)

    def chat_recommend(self, user_text, n=5):
        user_lower = user_text.lower()
        ref  = self.search(user_text, n=1)
        seed = ref.iloc[0]["title"] if not ref.empty else None

        found = [g for g in ALL_GENRES if g in user_lower]
        extra = []
        for tone, mapped in TONE_GENRE_MAP.items():
            if tone in user_lower:
                extra.extend(mapped)
        genres_to_use = list(set([g.title() for g in found] + extra))

        if seed:
            recs = self.similar_to(seed, n=n * 2)
            if not recs.empty:
                if genres_to_use:
                    pat      = "|".join(genres_to_use)
                    filtered = recs[recs["genres"].str.contains(pat, case=False, na=False)]
                    if not filtered.empty:
                        return filtered.head(n), seed, genres_to_use
                return recs.head(n), seed, genres_to_use

        if genres_to_use:
            pat      = "|".join(genres_to_use)
            mask     = self.movies_df["genres"].str.contains(pat, case=False, na=False)
            filtered = self.movies_df[mask]
            if "vote_average" in filtered.columns:
                filtered = filtered.nlargest(n * 2, "vote_average")
            return filtered.head(n), None, genres_to_use

        qvec   = self.vectorizer.transform([user_text])
        scores = cosine_similarity(qvec, self.tfidf_matrix).flatten()
        top    = np.argsort(scores)[::-1][:n]
        return self.movies_df.iloc[top], None, []

class HybridRecommender:
    def __init__(self):
        self.cb        = ContentBasedRecommender()
        self.movies_df = None

    def fit(self, movies_df, ratings_df=None):
        print("\n[Recommender] Training ...")
        self.movies_df = movies_df.copy()
        self.cb.fit(movies_df)
        print("[Recommender] Ready\n")

    def recommend_by_movie(self, title, n=5):
        result = self.cb.similar_to(title, n=n)
        if result.empty:
            return pd.DataFrame(), f'"{title}" not found.'
        row    = self.movies_df[self.movies_df["title"].str.lower() == title.lower()]
        genres = row.iloc[0]["genres"] if not row.empty else "Similar"
        return result, f'Because you liked **{title}** ({genres})'

    def recommend_by_taste(self, titles, n=5):
        result    = self.cb.similar_to_many(titles, n=n)
        taste_str = "  .  ".join(titles)
        return result, f'Based on your taste in: **{taste_str}**'

    def recommend_by_mood(self, mood, n=8):
        return self.cb.mood_movies(mood, n=n)

    def chat_recommend(self, user_text, n=5):
        return self.cb.chat_recommend(user_text, n=n)

    def trending(self, n=12):
        df = self.movies_df
        if "vote_average" in df.columns:
            top50 = df[df["vote_average"] > 0].nlargest(50, "vote_average")
            return top50.sample(min(n, len(top50)))
        return df.sample(min(n, len(df)))

    def surprise_me(self):
        df = self.movies_df
        if "vote_average" in df.columns:
            good = df[df["vote_average"] >= 7.5]
            if not good.empty:
                return good.sample(1).iloc[0].to_dict()
        return df.sample(1).iloc[0].to_dict()

    def search(self, query, n=10):
        return self.cb.search(query, n)

def build_recommender(movies_df, ratings_df=None):
    model = HybridRecommender()
    model.fit(movies_df, ratings_df)
    return model