"""
ui.py  —  CineMatch Pro · Production UI  (Portfolio Edition)
=============================================================
FEATURES IN THIS VERSION
  1. Global Sidebar Filters  — min rating slider + year range select_slider
  2. Developer Profile Card  — name, GitHub, LinkedIn links
  3. App Features Expander   — lists all capabilities for recruiters
  4. ▶ Trailer Button        — YouTube search link on every card (no API key)
  5. Watchlist saves overview — all 6 fields passed to add_to_watchlist()
  6. No DuplicateWidgetID    — global atomic counter for button keys
  7. Handles movieId / movie_id column names in movie_grid
"""

import streamlit as st
from api   import get_poster_url, PLACEHOLDER
from utils import star_display, genre_tags, truncate, add_to_watchlist, in_watchlist


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL ATOMIC COUNTER  —  guarantees unique widget keys every run
# Streamlit resets module globals on every script execution, so _CARD_COUNTER
# always starts at 0 and increments once per card rendered.
# ═══════════════════════════════════════════════════════════════════════════════

_CARD_COUNTER = 0

def _next_key() -> int:
    global _CARD_COUNTER
    _CARD_COUNTER += 1
    return _CARD_COUNTER

def reset_card_counter():
    """
    Call this at the TOP of every app.py rerun (before any page renders).
    ui.py is an imported module — Python caches it in sys.modules, so
    _CARD_COUNTER is NOT automatically reset between Streamlit reruns.
    Without this reset, button keys change every rerun and Streamlit
    cannot match click events → buttons appear to do nothing.
    """
    global _CARD_COUNTER
    _CARD_COUNTER = 0


# ═══════════════════════════════════════════════════════════════════════════════
# GENRE COLORS
# ═══════════════════════════════════════════════════════════════════════════════

GENRE_COLORS = {
    "Action":          "#FF4500",
    "Adventure":       "#FF8C00",
    "Animation":       "#FFD700",
    "Comedy":          "#32CD32",
    "Crime":           "#DC143C",
    "Documentary":     "#87CEEB",
    "Drama":           "#9370DB",
    "Family":          "#FF69B4",
    "Fantasy":         "#00CED1",
    "History":         "#DAA520",
    "Horror":          "#FF2020",
    "Music":           "#FF1493",
    "Mystery":         "#AA77FF",
    "Romance":         "#FF6EB4",
    "Science Fiction": "#00BFFF",
    "Sci-Fi":          "#00BFFF",
    "Sport":           "#7CFC00",
    "Thriller":        "#FF6347",
    "War":             "#AAAAAA",
    "Western":         "#D2691E",
    "Biography":       "#20B2AA",
}

def _genre_color(genre: str) -> str:
    for key, color in GENRE_COLORS.items():
        if key.lower() in genre.lower():
            return color
    return "#E50914"

def _genre_chips_html(genres_raw: str, max_n: int = 3) -> str:
    if not genres_raw or str(genres_raw).strip() in ("", "nan", "N/A"):
        return ""
    parts = [g.strip() for g in
             str(genres_raw).replace("|", ",").split(",")
             if g.strip()][:max_n]
    chips = "".join(
        f"<span class='genre-chip' style='"
        f"color:{_genre_color(g)};border-color:{_genre_color(g)}55;"
        f"background:{_genre_color(g)}18;'>{g}</span>"
        for g in parts
    )
    return f"<div class='card-genres'>{chips}</div>"


# ═══════════════════════════════════════════════════════════════════════════════
# CSS — Full cinematic dark theme
# ═══════════════════════════════════════════════════════════════════════════════

def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Outfit:wght@300;400;500;600;700&family=DM+Mono:wght@300;400;500&display=swap');

:root {
    --bg:    #04040C;
    --surf:  #0C0C18;
    --surf2: #121224;
    --card:  #0E0E1C;
    --pri:   #E50914;
    --acc:   #F5C518;
    --teal:  #00D4FF;
    --txt:   #F2F2FF;
    --txt2:  #BBBBDD;
    --muted: #7777AA;
    --r:     16px;
    --r2:    10px;
}

/* ── Hide leaked Streamlit icon ── */
[class*="keyboard"],[data-icon*="keyboard"],
span.material-icons,span.material-symbols-outlined { display:none !important; }

/* ── Base ── */
html,body,.stApp {
    background:var(--bg) !important;
    color:var(--txt) !important;
    font-family:'Outfit',sans-serif !important;
}
.stApp {
    background:
        radial-gradient(ellipse 120% 60% at 15% 10%,rgba(229,9,20,0.05) 0%,transparent 55%),
        radial-gradient(ellipse 80% 50% at 85% 85%,rgba(0,212,255,0.025) 0%,transparent 55%),
        #04040C !important;
}
.stApp::before {
    content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.022'/%3E%3C/svg%3E");
    opacity:0.4;animation:grain 0.5s steps(3) infinite;
}
@keyframes grain {
    0%  { transform:translate(0,0); }
    33% { transform:translate(-2px,1px); }
    66% { transform:translate(1px,-2px); }
    100%{ transform:translate(-1px,2px); }
}
.stApp>header { background:transparent !important; }
#MainMenu,footer,.stDeployButton,[data-testid="stToolbar"] { display:none !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background:linear-gradient(180deg,#020208 0%,#050510 50%,#07070E 100%) !important;
    border-right:1px solid rgba(229,9,20,0.12) !important;
    box-shadow:6px 0 40px rgba(0,0,0,0.8) !important;
}
[data-testid="stSidebar"]::before {
    content:'';position:absolute;top:0;left:0;right:0;height:3px;
    background:linear-gradient(90deg,#E50914,#FF8C00,#FFD700,#00D4FF,#E50914);
    background-size:300% 100%;animation:rainbowShift 4s linear infinite;z-index:999;
}
@keyframes rainbowShift { 100% { background-position:300% center; } }
[data-testid="stSidebar"] * { color:var(--txt) !important; }

/* Nav radio */
[data-testid="stSidebar"] .stRadio>label { display:none; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
    display:flex;flex-direction:column;gap:3px;padding:0 10px;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    background:transparent !important;border:1px solid transparent !important;
    border-radius:var(--r2) !important;padding:13px 18px !important;
    cursor:pointer !important;font-size:0.97rem !important;font-weight:500 !important;
    color:var(--muted) !important;transition:all 0.22s cubic-bezier(.4,0,.2,1) !important;
    display:flex !important;align-items:center !important;
    position:relative !important;overflow:hidden !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label::before {
    content:'';position:absolute;left:0;top:50%;transform:translateY(-50%);
    width:3px;height:0;background:linear-gradient(180deg,#FF2030,var(--acc));
    border-radius:0 3px 3px 0;transition:height 0.22s;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
    color:var(--txt) !important;border-color:rgba(229,9,20,0.18) !important;
    transform:translateX(5px) !important;background:rgba(229,9,20,0.06) !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover::before { height:55%; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-checked="true"] {
    background:linear-gradient(135deg,rgba(229,9,20,0.2),rgba(229,9,20,0.06)) !important;
    color:var(--txt) !important;border-color:rgba(229,9,20,0.32) !important;
    font-weight:700 !important;box-shadow:0 0 20px rgba(229,9,20,0.1) !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-checked="true"]::before { height:65%; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] input { display:none !important; }

/* ── Divider ── */
.divider {
    height:1px;
    background:linear-gradient(90deg,transparent,rgba(229,9,20,0.4),rgba(245,197,24,0.3),transparent);
    margin:1.5rem 0;
}

/* ── Section header ── */
.sec-hdr {
    font-family:'Bebas Neue',sans-serif !important;
    font-size:1.75rem !important;letter-spacing:0.14em !important;
    color:var(--txt) !important;padding-left:16px !important;
    margin:0.4rem 0 1.2rem !important;position:relative !important;
}
.sec-hdr::before {
    content:'';position:absolute;left:0;top:8%;bottom:8%;width:4px;
    background:linear-gradient(180deg,var(--pri),var(--acc));
    border-radius:2px;box-shadow:0 0 10px rgba(229,9,20,0.5);
}
.sec-hdr::after {
    content:'';position:absolute;bottom:-6px;left:0;right:0;height:1px;
    background:linear-gradient(90deg,rgba(229,9,20,0.35),transparent 50%);
}

/* ── Hero ── */
.hero {
    position:relative;border-radius:22px;padding:3rem 3.5rem;
    margin-bottom:2rem;border:1px solid rgba(229,9,20,0.15);overflow:hidden;
    animation:heroEnter 0.7s cubic-bezier(.4,0,.2,1) both;
    background:linear-gradient(135deg,rgba(229,9,20,0.06) 0%,transparent 40%,rgba(0,212,255,0.02) 100%),
               linear-gradient(180deg,#0A0A14 0%,#060610 100%);
}
@keyframes heroEnter { from{opacity:0;transform:translateY(-18px) scale(0.99)} to{opacity:1;transform:translateY(0) scale(1)} }
.hero::before {
    content:'';position:absolute;top:0;left:0;right:0;height:6px;
    background:repeating-linear-gradient(90deg,transparent 0px,transparent 14px,rgba(229,9,20,0.45) 14px,rgba(229,9,20,0.45) 22px);
}
.hero::after {
    content:'';position:absolute;bottom:0;left:0;right:0;height:6px;
    background:repeating-linear-gradient(90deg,transparent 0px,transparent 14px,rgba(229,9,20,0.25) 14px,rgba(229,9,20,0.25) 22px);
}
.hero-glow {
    position:absolute;top:-40%;right:-5%;width:480px;height:480px;
    background:radial-gradient(circle,rgba(229,9,20,0.1) 0%,rgba(229,9,20,0.03) 40%,transparent 70%);
    pointer-events:none;animation:glowFloat 8s ease-in-out infinite alternate;
}
@keyframes glowFloat { 0%{transform:translate(0,0) scale(1)} 100%{transform:translate(-30px,25px) scale(1.15)} }
.hero-content { position:relative;z-index:2; }
.hero-eyebrow {
    font-family:'DM Mono',monospace !important;font-size:0.7rem !important;
    letter-spacing:0.22em !important;color:#FF2030 !important;
    text-transform:uppercase !important;margin-bottom:0.6rem !important;display:block !important;
}
.hero-title {
    font-family:'Bebas Neue',sans-serif !important;
    font-size:clamp(2.8rem,5.5vw,5.5rem) !important;
    letter-spacing:0.1em !important;line-height:0.92 !important;margin-bottom:0.7rem !important;
    background:linear-gradient(130deg,#FFFFFF 0%,#FFE8E8 30%,#FF6060 65%,#E50914 100%) !important;
    -webkit-background-clip:text !important;-webkit-text-fill-color:transparent !important;
    background-clip:text !important;
    filter:drop-shadow(0 0 30px rgba(229,9,20,0.35)) !important;
    animation:titlePulse 4s ease-in-out infinite alternate;
}
@keyframes titlePulse {
    0%  { filter:drop-shadow(0 0 20px rgba(229,9,20,0.3)); }
    100%{ filter:drop-shadow(0 0 50px rgba(229,9,20,0.6)); }
}
.hero-sub {
    font-family:'Outfit',sans-serif !important;font-size:1.05rem !important;
    font-weight:300 !important;color:var(--txt2) !important;
    max-width:540px !important;line-height:1.65 !important;
}
.hero-divider {
    width:0;height:2px;
    background:linear-gradient(90deg,var(--pri),var(--acc),transparent);
    border-radius:1px;margin:0.9rem 0 1rem;
    animation:lineGrow 0.8s cubic-bezier(.4,0,.2,1) 0.3s both;
}
@keyframes lineGrow { to { width:120px; } }

/* ── Movie card ── */
.movie-card {
    background:linear-gradient(180deg,#111120 0%,#0D0D1A 100%);
    border:1px solid rgba(255,255,255,0.06);border-radius:var(--r);
    overflow:hidden;position:relative;
    transition:transform 0.32s cubic-bezier(.4,0,.2,1),border-color 0.32s,box-shadow 0.32s;
    cursor:pointer;animation:cardEnter 0.55s cubic-bezier(.4,0,.2,1) both;height:100%;
}
@keyframes cardEnter { from{opacity:0;transform:translateY(28px) scale(0.95)} to{opacity:1;transform:translateY(0) scale(1)} }
.movie-card::before {
    content:'';position:absolute;top:0;left:-80%;width:60%;height:100%;
    background:linear-gradient(105deg,transparent 40%,rgba(255,255,255,0.055) 50%,transparent 60%);
    transition:left 0.55s ease;z-index:4;pointer-events:none;
}
.movie-card:hover::before { left:120%; }
.movie-card::after {
    content:'';position:absolute;top:0;left:0;right:0;height:2px;
    background:linear-gradient(90deg,transparent,var(--pri),var(--acc),transparent);
    opacity:0;transition:opacity 0.3s;z-index:5;
}
.movie-card:hover::after { opacity:1; }
.movie-card:hover {
    transform:translateY(-12px) scale(1.03) !important;
    border-color:rgba(229,9,20,0.55) !important;
    box-shadow:0 25px 70px rgba(229,9,20,0.3),0 0 0 1px rgba(229,9,20,0.2) !important;
    z-index:10 !important;
}
.movie-card img {
    width:100%;aspect-ratio:2/3;object-fit:cover;display:block;
    transition:transform 0.45s ease,filter 0.3s;
    background:linear-gradient(160deg,#111120 0%,#1A0A14 100%);
    min-height:200px;
}
.movie-card:hover img { transform:scale(1.07);filter:brightness(1.12) saturate(1.1); }
.card-body { padding:0.85rem 1rem 1rem;position:relative;z-index:2;background:linear-gradient(180deg,#111120 0%,#0D0D1A 100%); }
.card-title { font-weight:700 !important;font-size:0.93rem !important;color:var(--txt) !important;margin:0 0 4px !important;white-space:nowrap !important;overflow:hidden !important;text-overflow:ellipsis !important; }
.card-rating { font-family:'DM Mono',monospace !important;font-size:0.78rem !important;color:var(--acc) !important;margin-bottom:6px !important; }
.card-genres { display:flex !important;flex-wrap:wrap !important;gap:4px !important;margin-bottom:8px !important; }
.genre-chip { display:inline-block;font-size:0.62rem !important;font-weight:700 !important;letter-spacing:0.07em !important;text-transform:uppercase !important;border-radius:4px !important;padding:2px 7px !important;border:1px solid !important;transition:all 0.18s !important; }
.genre-chip:hover { transform:scale(1.08) !important; }
.card-overview { font-size:0.77rem !important;font-weight:300 !important;color:#8888AA !important;line-height:1.48 !important;font-style:italic !important;display:-webkit-box !important;-webkit-line-clamp:3 !important;-webkit-box-orient:vertical !important;overflow:hidden !important; }
.wl-badge { position:absolute;top:10px;right:10px;z-index:6;background:linear-gradient(135deg,#C50000,#E50914);color:#fff;border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-size:0.75rem;font-weight:800;box-shadow:0 0 15px rgba(229,9,20,0.6);animation:badgePop 0.35s cubic-bezier(.4,0,.2,1); }
@keyframes badgePop { 0%{transform:scale(0) rotate(-30deg)} 80%{transform:scale(1.15) rotate(5deg)} 100%{transform:scale(1) rotate(0)} }

/* ── Trailer button ── */
.trailer-btn {
    display:flex;align-items:center;justify-content:center;
    background:rgba(255,255,255,0.04);
    color:#FF4040 !important;
    border:1px solid rgba(255,32,32,0.35);
    border-radius:8px;padding:5px 8px;
    font-size:0.8rem;font-weight:700;
    text-decoration:none !important;
    transition:all 0.2s;height:33px;gap:5px;letter-spacing:0.04em;
    cursor:pointer;
}
.trailer-btn:hover {
    background:rgba(229,9,20,0.15) !important;
    border-color:rgba(229,9,20,0.6) !important;
    color:#FF6060 !important;
    box-shadow:0 0 12px rgba(229,9,20,0.2);
}

/* ── Pill ── */
.pill { background:linear-gradient(135deg,rgba(245,197,24,0.1),rgba(245,197,24,0.04));border:1px solid rgba(245,197,24,0.28);border-radius:var(--r2);padding:0.8rem 1.2rem 0.8rem 1.5rem;font-size:0.92rem;font-weight:500;color:var(--acc);margin-bottom:1.3rem;position:relative;overflow:hidden;animation:pillSlide 0.4s cubic-bezier(.4,0,.2,1) both; }
.pill::before { content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:linear-gradient(180deg,var(--acc),rgba(245,197,24,0.3)); }
@keyframes pillSlide { from{opacity:0;transform:translateX(-14px)} to{opacity:1;transform:translateX(0)} }

/* ── Chat ── */
.chat-user { background:linear-gradient(135deg,rgba(229,9,20,0.15),rgba(229,9,20,0.06));border:1px solid rgba(229,9,20,0.28);border-radius:18px 18px 4px 18px;padding:0.85rem 1.15rem;margin:0.5rem 0 0.5rem 18%;font-size:0.95rem;color:var(--txt);animation:bubbleIn 0.3s ease both; }
.chat-bot { background:linear-gradient(135deg,var(--surf2),var(--surf));border:1px solid rgba(0,212,255,0.15);border-radius:18px 18px 18px 4px;padding:0.85rem 1.15rem;margin:0.5rem 18% 0.5rem 0;font-size:0.95rem;color:var(--txt);animation:bubbleIn 0.3s ease both; }
@keyframes bubbleIn { from{opacity:0;transform:translateY(12px) scale(0.97)} to{opacity:1;transform:translateY(0) scale(1)} }
.chat-bot .lbl { font-family:'DM Mono',monospace !important;font-size:0.68rem;color:var(--teal);letter-spacing:0.16em;text-transform:uppercase;margin-bottom:5px;display:block; }

/* ── Metrics ── */
[data-testid="stMetric"] { background:linear-gradient(135deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01)) !important;border-radius:var(--r) !important;padding:1.3rem 1.5rem !important;border:1px solid rgba(255,255,255,0.06) !important;backdrop-filter:blur(10px) !important;transition:transform 0.22s,box-shadow 0.22s !important;animation:cardEnter 0.5s ease both !important;position:relative !important;overflow:hidden !important; }
[data-testid="stMetric"]:hover { transform:translateY(-4px) !important;border-color:rgba(229,9,20,0.25) !important;box-shadow:0 15px 40px rgba(229,9,20,0.15) !important; }
[data-testid="stMetric"]::after { content:'';position:absolute;bottom:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--pri),var(--acc),var(--teal)); }
[data-testid="stMetricLabel"] { font-family:'DM Mono',monospace !important;color:var(--muted) !important;font-size:0.72rem !important;letter-spacing:0.12em !important;text-transform:uppercase !important; }
[data-testid="stMetricValue"] { font-family:'Bebas Neue',sans-serif !important;color:var(--acc) !important;font-size:2.4rem !important;letter-spacing:0.06em !important;line-height:1.1 !important; }

/* ── Buttons ── */
.stButton>button { background:linear-gradient(135deg,#B50000 0%,#E50914 60%,#FF2020 100%) !important;color:#fff !important;border:none !important;border-radius:var(--r2) !important;font-weight:700 !important;font-size:0.9rem !important;letter-spacing:0.06em !important;padding:0.52rem 1.3rem !important;transition:all 0.22s cubic-bezier(.4,0,.2,1) !important;box-shadow:0 5px 18px rgba(229,9,20,0.35) !important; }
.stButton>button:hover { transform:translateY(-3px) scale(1.02) !important;box-shadow:0 10px 30px rgba(229,9,20,0.55) !important; }
.stButton>button:active { transform:translateY(0) scale(0.98) !important; }

/* ── Form elements ── */
div[data-testid="stSelectbox"]>div,div[data-testid="stMultiSelect"]>div { background:var(--surf2) !important;border:1px solid rgba(255,255,255,0.08) !important;border-radius:var(--r2) !important;color:var(--txt) !important; }
div[data-testid="stSelectbox"]>div:focus-within { border-color:rgba(229,9,20,0.5) !important;box-shadow:0 0 0 3px rgba(229,9,20,0.1) !important; }
.stTextInput input,.stTextArea textarea { background:var(--surf2) !important;border:1px solid rgba(255,255,255,0.08) !important;border-radius:var(--r2) !important;color:var(--txt) !important;font-size:0.95rem !important;transition:border-color 0.2s,box-shadow 0.2s !important; }
.stTextInput input:focus,.stTextArea textarea:focus { border-color:rgba(229,9,20,0.5) !important;box-shadow:0 0 0 3px rgba(229,9,20,0.1) !important;outline:none !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { gap:4px !important;background:transparent !important;border-bottom:1px solid rgba(255,255,255,0.06) !important; }
.stTabs [data-baseweb="tab"] { background:transparent !important;border-radius:10px 10px 0 0 !important;color:var(--muted) !important;font-weight:600 !important;font-size:0.95rem !important;padding:0.65rem 1.3rem !important;transition:all 0.2s !important;border:1px solid transparent !important;border-bottom:none !important; }
.stTabs [data-baseweb="tab"]:hover { color:var(--txt) !important;background:rgba(229,9,20,0.07) !important; }
.stTabs [aria-selected="true"] { background:linear-gradient(180deg,rgba(229,9,20,0.15),rgba(229,9,20,0.06)) !important;color:var(--txt) !important;border-color:rgba(229,9,20,0.25) !important;border-bottom:2px solid var(--pri) !important; }

/* ── Sliders ── */
.stSlider [data-baseweb="slider"] [role="slider"] { background:var(--pri) !important;box-shadow:0 0 8px rgba(229,9,20,0.5) !important; }

/* ── Expander ── */
[data-testid="stExpander"] { background:rgba(255,255,255,0.02) !important;border:1px solid rgba(255,255,255,0.06) !important;border-radius:var(--r2) !important; }
[data-testid="stExpander"] summary { font-size:0.85rem !important;font-weight:600 !important;color:var(--muted) !important; }

/* ── Misc ── */
::-webkit-scrollbar { width:5px;height:5px; }
::-webkit-scrollbar-track { background:var(--bg); }
::-webkit-scrollbar-thumb { background:linear-gradient(180deg,var(--pri),var(--acc));border-radius:3px; }
.stSpinner>div { border-top-color:var(--pri) !important; }
p,span,div,label { font-family:'Outfit',sans-serif !important; }
h1,h2,h3,h4,h5,h6 { font-family:'Bebas Neue',sans-serif !important;letter-spacing:0.1em !important; }
code,pre { font-family:'DM Mono',monospace !important; }
.stAlert { border-radius:var(--r2) !important;border:1px solid rgba(229,9,20,0.2) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   RESPONSIVE — MOBILE & TABLET  (CSS only, zero functionality changes)
   Strategy:
     • Allow Streamlit's column flex containers to wrap on small screens
     • Tablet ≤768px  → 2-column movie grid, smaller hero/fonts
     • Phone  ≤480px  → 1-column movie grid, compact everything
   ═══════════════════════════════════════════════════════════════════════════ */

/* Let columns wrap on any screen size — required for media queries to work */
section[data-testid="stMain"] [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
}

/* ── Tablet: ≤ 768px ─────────────────────────────────────────────────────── */
@media screen and (max-width: 768px) {

    /* Content padding */
    .main .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* Hero */
    .hero {
        padding: 1.8rem 1.4rem !important;
        border-radius: 14px !important;
    }
    .hero-title { font-size: 2.8rem !important; }
    .hero-sub   { font-size: 0.9rem !important; }

    /* Section header */
    .sec-hdr { font-size: 1.4rem !important; }

    /* Movie grid — 2 columns on tablet */
    section[data-testid="stMain"] [data-testid="stHorizontalBlock"]
        > [data-testid="column"] {
        min-width: calc(50% - 0.5rem) !important;
        flex: 1 1 calc(50% - 0.5rem) !important;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        padding: 1rem 1.1rem !important;
    }

    /* Chat bubbles — less extreme margins */
    .chat-user { margin-left: 4% !important; }
    .chat-bot  { margin-right: 4% !important; }

    /* Genre tabs — horizontal scroll on small screens */
    .stTabs [data-baseweb="tab-list"] {
        overflow-x: auto !important;
        flex-wrap: nowrap !important;
        -webkit-overflow-scrolling: touch !important;
        scrollbar-width: none !important;
    }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none !important; }

    /* Sidebar developer card links — stack vertically */
    [data-testid="stSidebar"] a { display: block !important; margin-bottom: 4px !important; }
}

/* ── Phone: ≤ 480px ──────────────────────────────────────────────────────── */
@media screen and (max-width: 480px) {

    /* Content padding tighter */
    .main .block-container {
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
    }

    /* Hero compact */
    .hero {
        padding: 1.2rem 1rem !important;
        border-radius: 10px !important;
        margin-bottom: 1rem !important;
    }
    .hero-title   { font-size: 2rem !important; line-height: 1 !important; }
    .hero-sub     { font-size: 0.82rem !important; max-width: 100% !important; }
    .hero-eyebrow { font-size: 0.58rem !important; letter-spacing: 0.14em !important; }
    .hero-glow    { width: 200px !important; height: 200px !important; }

    /* Section header */
    .sec-hdr { font-size: 1.15rem !important; }

    /* Movie grid — 1 column on phone */
    section[data-testid="stMain"] [data-testid="stHorizontalBlock"]
        > [data-testid="column"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }

    /* Movie card — full-width image on phone */
    .movie-card img { aspect-ratio: 16/9 !important; min-height: 160px !important; }
    .card-title     { font-size: 0.88rem !important; }
    .card-rating    { font-size: 0.72rem !important; }
    .card-overview  { font-size: 0.73rem !important; -webkit-line-clamp: 2 !important; }
    .genre-chip     { font-size: 0.57rem !important; padding: 2px 5px !important; }
    .card-body      { padding: 0.7rem 0.8rem 0.9rem !important; }

    /* Trailer / watchlist buttons */
    .stButton > button {
        font-size: 0.78rem !important;
        padding: 0.4rem 0.7rem !important;
        letter-spacing: 0.02em !important;
    }
    .trailer-btn { font-size: 0.73rem !important; height: 30px !important; }

    /* Metric values — smaller on phone */
    [data-testid="stMetricValue"] { font-size: 1.7rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.62rem !important; }
    [data-testid="stMetric"]      { padding: 0.8rem 0.9rem !important; }

    /* Chat bubbles — nearly full width */
    .chat-user { margin-left: 2% !important; }
    .chat-bot  { margin-right: 2% !important; }
    .chat-user, .chat-bot { font-size: 0.88rem !important; padding: 0.7rem 0.9rem !important; }

    /* Explanation pill */
    .pill { font-size: 0.8rem !important; padding: 0.65rem 0.9rem 0.65rem 1.1rem !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        font-size: 0.8rem !important;
        padding: 0.5rem 0.75rem !important;
        letter-spacing: 0 !important;
    }

    /* Divider spacing */
    .divider { margin: 1rem 0 !important; }

    /* Surprise card — stack on phone */
    [data-testid="stHorizontalBlock"]:has(.movie-card) > [data-testid="column"]:first-child {
        min-width: 100% !important;
    }
}

/* ── Touch devices — disable hover card lift to prevent sticky hover ──────── */
@media (hover: none) and (pointer: coarse) {
    .movie-card:hover {
        transform: none !important;
        border-color: rgba(255,255,255,0.06) !important;
        box-shadow: none !important;
    }
    .movie-card:hover img { transform: none !important; filter: none !important; }
    .movie-card:hover::before { left: -80% !important; }
    .movie-card:hover::after  { opacity: 0 !important; }
    .stButton > button:hover  {
        transform: none !important;
        box-shadow: 0 5px 18px rgba(229,9,20,0.35) !important;
    }
}

</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR  —  Navigation · Watchlist · Filters · Dev Card · Feature List
# ═══════════════════════════════════════════════════════════════════════════════

NAV_ITEMS = [
    "🏠  Home",
    "🎬  Recommend",
    "🎭  Mood",
    "🤖  AI Chat",
    "📊  Dashboard",
    "📌  Watchlist",
]

def render_sidebar() -> str:
    """
    Render full sidebar.
    Returns selected page string.
    Stores filter_rating + filter_years in session_state for all pages.
    """
    with st.sidebar:

        # ── Logo ──────────────────────────────────────────────────────────────
        st.markdown("""
<div style="padding:2.5rem 0.8rem 0.4rem;">
    <div style="font-family:'Bebas Neue',sans-serif;font-size:2.3rem;
        letter-spacing:0.14em;
        background:linear-gradient(135deg,#E50914 0%,#FF5050 100%);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
        background-clip:text;
        filter:drop-shadow(0 0 18px rgba(229,9,20,0.45));
        line-height:1.0;">🎬 CineMatch</div>
    <div style="font-family:'DM Mono',monospace;font-size:0.66rem;
        color:#555588;letter-spacing:0.2em;text-transform:uppercase;
        margin-top:5px;padding-left:3px;">PRO · AI POWERED</div>
</div>
""", unsafe_allow_html=True)

        st.markdown(
            "<div class='divider' style='margin:0.5rem 0 0.8rem;'></div>",
            unsafe_allow_html=True,
        )

        # ── Navigation ────────────────────────────────────────────────────────
        page = st.radio("nav", NAV_ITEMS, label_visibility="collapsed")

        # ── Watchlist counter ─────────────────────────────────────────────────
        wl = len(st.session_state.get("watchlist", []))
        st.markdown(f"""
<div style="margin:1.2rem 0.5rem 0.8rem;padding:0.85rem 1.1rem;
    background:linear-gradient(135deg,rgba(229,9,20,0.1),rgba(229,9,20,0.03));
    border:1px solid rgba(229,9,20,0.2);border-radius:10px;
    display:flex;align-items:center;justify-content:space-between;">
    <span style="font-family:'DM Mono',monospace;font-size:0.7rem;
        letter-spacing:0.12em;text-transform:uppercase;color:#7777AA;">WATCHLIST</span>
    <span style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;
        line-height:1;color:#F5C518;
        text-shadow:0 0 12px rgba(245,197,24,0.45);">{wl}</span>
</div>
""", unsafe_allow_html=True)

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        # ── ⚙️ GLOBAL FILTERS ─────────────────────────────────────────────────
        st.markdown("""
<div style="font-family:'Bebas Neue',sans-serif;font-size:1rem;
    letter-spacing:0.12em;color:#9999BB;padding:0 0.3rem 0.5rem;">
    ⚙️ GLOBAL FILTERS
</div>
""", unsafe_allow_html=True)

        min_rating = st.slider(
            "Minimum Rating ⭐",
            min_value=0.0, max_value=10.0,
            value=float(st.session_state.get("filter_rating", 0.0)),
            step=0.5,
            help="Only show movies rated this or higher",
        )

        year_range = st.select_slider(
            "Release Year",
            options=list(range(1950, 2026)),
            value=st.session_state.get("filter_years", (1990, 2025)),
            help="Filter movies by release year range",
        )

        # Persist filters to session_state so every page can read them
        st.session_state["filter_rating"] = min_rating
        st.session_state["filter_years"]  = year_range

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        # ── 📋 APP FEATURES EXPANDER ──────────────────────────────────────────
        with st.expander("📋 App Features", expanded=False):
            st.markdown("""
<div style="font-size:0.78rem;color:#BBBBDD;line-height:2;">
✅ AI Recommendations (TF-IDF & Cosine Similarity)<br>
✅ Pickle Cache — 10× faster restarts<br>
✅ Real-time Mood-based Discovery<br>
✅ Natural Language AI Chat Bot<br>
✅ Persistent JSON Watchlist<br>
✅ OMDB API — Live Poster Integration<br>
✅ Global Rating &amp; Year Filters<br>
✅ ▶ YouTube Trailer Links (No API Key)<br>
✅ CSV Watchlist Export<br>
✅ Cinematic Dark Theme UI<br>
</div>
""", unsafe_allow_html=True)

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        # ── 👤 DEVELOPER CARD ─────────────────────────────────────────────────
        st.markdown("""
<div style="background:linear-gradient(135deg,#0E0E1E,#0A0A14);
    padding:16px 18px;border-radius:12px;
    border:1px solid rgba(229,9,20,0.28);margin:0 0.3rem 1rem;">
    <div style="font-family:'DM Mono',monospace;font-size:0.6rem;
        color:#555588;letter-spacing:0.16em;text-transform:uppercase;
        margin-bottom:5px;">DEVELOPED BY</div>
    <div style="font-family:'Bebas Neue',sans-serif;font-size:1.2rem;
        letter-spacing:0.1em;color:#F2F2FF;margin-bottom:4px;">
        Aditya Kumar
    </div>
    <div style="font-family:'DM Mono',monospace;font-size:0.65rem;
        color:#7777AA;margin-bottom:12px;letter-spacing:0.06em;">
        Data Scientist · ML Engineer
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <a href="https://github.com/aditya20007" target="_blank"
           style="text-decoration:none;display:flex;align-items:center;gap:5px;
           background:rgba(255,255,255,0.06);
           border:1px solid rgba(255,255,255,0.14);
           border-radius:7px;padding:5px 12px;font-size:0.74rem;
           color:#F2F2FF;font-weight:600;letter-spacing:0.04em;
           transition:all 0.2s;">🚀 GitHub</a>
        <a href="https://www.linkedin.com/in/aditya-singh-bab941258/" target="_blank"
           style="text-decoration:none;display:flex;align-items:center;gap:5px;
           background:rgba(0,119,181,0.15);
           border:1px solid rgba(0,119,181,0.32);
           border-radius:7px;padding:5px 12px;font-size:0.74rem;
           color:#60B0FF;font-weight:600;letter-spacing:0.04em;
           transition:all 0.2s;">👔 LinkedIn</a>
    </div>
</div>
<div style="text-align:center;padding-bottom:0.8rem;
    font-family:'DM Mono',monospace;font-size:0.58rem;
    color:#2A2A3A;letter-spacing:0.08em;">
    PORTFOLIO PROJECT · 2025
</div>
""", unsafe_allow_html=True)

    return page


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════

def hero_banner(title: str, subtitle: str):
    st.markdown(f"""
<div class="hero">
    <div class="hero-glow"></div>
    <div class="hero-content">
        <span class="hero-eyebrow">🎬 AI · POWERED · RECOMMENDATIONS</span>
        <div class="hero-title">{title}</div>
        <div class="hero-divider"></div>
        <div class="hero-sub">{subtitle}</div>
    </div>
</div>
""", unsafe_allow_html=True)


def section_header(title: str, subtitle: str = ""):
    sub = (f"<div style='font-size:0.82rem;color:#666688;margin-top:3px;"
           f"font-weight:300;'>{subtitle}</div>") if subtitle else ""
    st.markdown(f"<div class='sec-hdr'>{title}</div>{sub}",
                unsafe_allow_html=True)


def divider():
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)


def explanation_pill(text: str):
    st.markdown(f"<div class='pill'>💡 {text}</div>",
                unsafe_allow_html=True)


def movie_card(movie: dict, show_wl_btn: bool = True, delay: int = 0):
    """
    Render one movie card.

    Bottom action row has two columns:
      Col 1 → + Watchlist / ✓ Saved  (Streamlit button)
      Col 2 → ▶ Trailer              (YouTube search link — no API key needed)

    Key format:  btn_wl_{mid}_{_next_key()}  — globally unique every run.
    Overview is stored in watchlist so the Watchlist page works offline.
    """
    title         = str(movie.get("title", "Unknown"))
    mid_raw       = movie.get("movie_id") or movie.get("movieId", 0)
    try:
        mid = int(float(mid_raw))
    except (ValueError, TypeError):
        mid = 0
    # FIX: mid=0 means no real ID (e.g. all OMDB trending cards).
    # Use a stable title hash so every card gets a unique non-zero id.
    # This makes buttons render AND watchlist de-dup work correctly.
    if mid == 0:
        mid = abs(hash(title)) % 999_999 or 1

    rating        = movie.get("rating") or movie.get("vote_average", 0)
    genres        = str(movie.get("genres", ""))
    overview      = truncate(str(movie.get("overview", "")), 130)
    overview_full = str(movie.get("overview", ""))

    try:
        in_wl = in_watchlist(mid)
    except Exception:
        in_wl = False

    poster = movie.get("poster_url", "")
    if not poster or poster == PLACEHOLDER:
        poster = get_poster_url(
            title=title,
            poster_path=movie.get("poster_path", ""),
        )

    badge      = "<div class='wl-badge'>✓</div>" if in_wl else ""
    genre_html = _genre_chips_html(genres)
    delay_css  = f"animation-delay:{delay * 0.07}s;" if delay else ""

    # ── Card HTML ──────────────────────────────────────────────────────────────
    st.markdown(
        f"<div class='movie-card' style='{delay_css}'>"
        f"  {badge}"
        f"  <img src='{poster}' alt='{title}' loading='lazy'"
        f"       onerror=\"this.onerror=null;this.src='{PLACEHOLDER}'\"/>"
        f"  <div class='card-body'>"
        f"    <div class='card-title' title='{title}'>{title}</div>"
        f"    <div class='card-rating'>{star_display(rating)}</div>"
        f"    {genre_html}"
        f"    <div class='card-overview'>{overview}</div>"
        f"  </div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Always render action buttons (mid is guaranteed non-zero after fix above)
    c1, c2 = st.columns(2)

    # ── Col 1: Watchlist button ───────────────────────────────────────────────
    with c1:
        if show_wl_btn:
            btn_label  = "✓ Saved" if in_wl else "+ Watchlist"
            unique_key = f"btn_wl_{mid}_{_next_key()}"
            if st.button(btn_label, key=unique_key,
                         use_container_width=True):
                if not in_wl:
                    added = add_to_watchlist(
                        movie_id   = mid,
                        title      = title,
                        poster_url = poster,
                        rating     = float(rating) if rating else 0.0,
                        genres     = genres,
                        overview   = overview_full,
                    )
                    if added:
                        st.toast(f"✅ **{title}** added to Watchlist!")
                        st.rerun()

    # ── Col 2: Trailer link ───────────────────────────────────────────────────
    with c2:
        safe_query  = title.replace(" ", "+").replace("'", "").replace('"', "")
        trailer_url = (
            f"https://www.youtube.com/results?"
            f"search_query={safe_query}+official+trailer"
        )
        st.markdown(
            f"<a href='{trailer_url}' target='_blank' "
            f"style='text-decoration:none;display:block;'>"
            f"<div class='trailer-btn'>▶ Trailer</div>"
            f"</a>",
            unsafe_allow_html=True,
        )


def movie_grid(movies, cols: int = 4, show_wl_btn: bool = True):
    """
    Render a responsive grid of movie cards.
    Handles DataFrame (movieId column) and list of dicts (movie_id key).
    """
    records = []

    if hasattr(movies, "iterrows"):
        for _, row in movies.iterrows():
            mid = row.get("movieId", row.get("movie_id", 0))
            records.append({
                "movie_id":   mid,
                "title":      row.get("title", ""),
                "poster_url": get_poster_url(
                    title=row.get("title", ""),
                    poster_path=row.get("poster_path", ""),
                ),
                "rating":     row.get("vote_average", 0),
                "genres":     row.get("genres", ""),
                "overview":   row.get("overview", ""),
            })
    else:
        records = [dict(m) for m in movies]

    if not records:
        st.info("No movies to display.")
        return

    grid = st.columns(cols)
    for i, m in enumerate(records):
        with grid[i % cols]:
            movie_card(m, show_wl_btn=show_wl_btn, delay=i)


def surprise_card(movie: dict):
    """Full-width featured card for Surprise Me."""
    title         = str(movie.get("title", "Unknown"))
    mid_raw       = movie.get("movie_id") or movie.get("movieId", 0)
    try:
        mid = int(float(mid_raw))
    except (ValueError, TypeError):
        mid = 0
    if mid == 0:
        mid = abs(hash(title)) % 999_999 or 1

    rating          = movie.get("rating") or movie.get("vote_average", 0)
    genres          = str(movie.get("genres", ""))
    overview        = truncate(str(movie.get("overview", "")), 300)
    overview_full   = str(movie.get("overview", ""))
    poster          = get_poster_url(
        title=title, poster_path=movie.get("poster_path", "")
    )
    genre_chip_html = _genre_chips_html(genres, max_n=5)

    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown(
            f"<div style='animation:cardEnter 0.6s ease both;'>"
            f"<img src='{poster}' loading='lazy' style='width:100%;border-radius:16px;"
            f"box-shadow:0 25px 70px rgba(229,9,20,0.4),0 0 0 1px rgba(229,9,20,0.2);'"
            f" onerror=\"this.onerror=null;this.src='{PLACEHOLDER}'\"/></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div style='animation:cardEnter 0.6s ease 0.12s both;'>"
            f"<div style='font-family:\"Bebas Neue\",sans-serif;font-size:2.8rem;"
            f"letter-spacing:0.1em;color:#fff;line-height:0.95;margin-bottom:10px;"
            f"text-shadow:0 0 30px rgba(229,9,20,0.4);'>{title}</div>"
            f"<div style='font-family:\"DM Mono\",monospace;color:#F5C518;"
            f"font-size:0.95rem;margin-bottom:12px;'>{star_display(rating)}</div>"
            f"{genre_chip_html}"
            f"<div style='color:#BBBBDD;font-size:0.97rem;line-height:1.65;"
            f"margin-top:14px;font-style:italic;font-weight:300;'>{overview}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        bc1, bc2 = st.columns(2)
        with bc1:
            try:
                in_wl = in_watchlist(mid)
            except Exception:
                in_wl = False
            if mid and not in_wl:
                if st.button("+ Watchlist",
                             key=f"btn_sup_wl_{mid}_{_next_key()}"):
                    add_to_watchlist(
                        movie_id   = mid,
                        title      = title,
                        poster_url = poster,
                        rating     = float(rating) if rating else 0.0,
                        genres     = genres,
                        overview   = overview_full,
                    )
                    st.toast(f"✅ **{title}** added to Watchlist!")
                    st.rerun()

        with bc2:
            sq  = title.replace(" ", "+").replace("'", "")
            url = (f"https://www.youtube.com/results?"
                   f"search_query={sq}+official+trailer")
            st.markdown(
                f"<a href='{url}' target='_blank' "
                f"style='text-decoration:none;display:block;'>"
                f"<div class='trailer-btn' "
                f"style='height:38px;font-size:0.88rem;'>▶ Watch Trailer</div>"
                f"</a>",
                unsafe_allow_html=True,
            )