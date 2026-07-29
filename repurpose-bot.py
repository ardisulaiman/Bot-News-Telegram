"""
Multi-Topic News Curator Bot (No-AI Version)
--------------------------------------------
1 bot, 1 GRUP Telegram (pakai fitur Topics), 6 topik:
  - AI
  - Crypto
  - Viral Indonesia
  - Entertainment Indonesia
  - Viral Global
  - Politik Indonesia

Tiap topik ambil dari sumbernya sendiri, kurasi ketat (cuma yang skornya
tinggi/menarik), lalu dikirim ke topic Telegram masing-masing (pakai
message_thread_id), semua di 1 grup yang sama.

Gak pake AI sama sekali. Judul & preview dikirim APA ADANYA dari sumber asli.
Lo yang baca & tulis ulang manual buat di-post ke platform lo.
"""

import os
import json
import time
import logging
import re
import unicodedata
import threading
import html
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# KONFIGURASI UMUM
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # 1 grup buat semua topic
TWITTERAPI_KEY = os.getenv("TWITTERAPI_KEY", "")

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", 1800))
TEST_MODE = os.getenv("TEST_MODE", "0") == "1"
MAX_AGE_HOURS = float(os.getenv("MAX_AGE_HOURS", 5))
MIN_SCORE_TO_SEND_DEFAULT = int(os.getenv("MIN_SCORE_TO_SEND", 30))
SEEN_FILE = "seen_items.json"
SIGNATURES_FILE = "sent_signatures.json"
MAX_ITEMS_PER_TOPIC = int(os.getenv("MAX_ITEMS_PER_TOPIC", 6))
AI_TOOLS_MAX_ITEMS = int(os.getenv("AI_TOOLS_MAX_ITEMS", 10))
POLITICS_MAX_ITEMS = int(os.getenv("POLITICS_MAX_ITEMS", 15))
DEDUPE_HOURS = int(os.getenv("DEDUPE_HOURS", 72))
TRANSLATE_SOURCE_LANG = os.getenv("TRANSLATE_SOURCE_LANG", "en")
TELEGRAM_OFFSET_FILE = "telegram_update_offset.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("news-bot")


def _get_thread_id(env_key):
    """Ambil thread_id dari .env, return None kalau kosong (biar gampang dicek)."""
    val = os.getenv(env_key)
    if val is None or val.strip() == "":
        return None
    try:
        return int(val)
    except ValueError:
        log.warning(f"{env_key} isinya bukan angka: {val!r}, dianggap kosong.")
        return None


# ============================================================
# KATA KUNCI BUAT SCORING
# ============================================================

STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "will", "have",
    "yang", "dan", "atau", "untuk", "dari", "dengan", "ini", "itu", "akan",
    "into", "over", "about", "after", "before", "says", "said",
}

TOPIC_RELEVANCE = {
    "ai": {
        "ai", "artificial intelligence", "chatgpt", "openai", "anthropic",
        "claude", "gemini", "llm", "machine learning", "deepmind", "grok",
        "generative ai", "neural network", "model",
    },
    "crypto": {
        "crypto", "bitcoin", "btc", "ethereum", "eth", "blockchain",
        "token", "stablecoin", "defi", "web3", "solana", "binance", "coinbase",
    },
    "ai_tools": {
        "ai", "artificial intelligence", "chatgpt", "openai", "claude",
        "gemini", "llm", "model", "agent", "generative",
    },
    "politics_id": {
        "politik", "pemerintah", "presiden", "wakil presiden", "menteri",
        "dpr", "mpr", "dpd", "partai", "pemilu", "pilkada", "kpu",
        "bawaslu", "kabinet", "ruu", "undang undang", "kebijakan",
        "koalisi", "oposisi", "legislatif", "eksekutif", "mahkamah konstitusi",
        "korupsi", "kpk", "demonstrasi", "istana", "gubernur", "kepala daerah",
    },
}

LOW_VALUE_PATTERNS = {
    "price prediction", "price analysis", "technical analysis", "daily horoscope",
    "weekly roundup", "morning brief", "live updates", "what we know",
    "watch now", "photos", "photo gallery", "full list", "recap",
}

NOT_PUBLIC_PATTERNS = {
    "waitlist", "invite only", "closed beta", "private beta", "limited preview",
    "selected users", "select users", "not yet available", "coming soon",
    "early access applicants", "internal testing", "plans to launch",
}

BIG_UPDATE_KEYWORDS = {
    "launches", "launch", "launched", "unveils", "unveil", "unveiled",
    "announces", "announced", "announcement", "release", "released",
    "releases", "debut", "debuts", "introduces", "introduced", "rolls out",
    "breakthrough", "revolutionary", "first-ever", "record", "milestone",
    "acquires", "acquisition", "billion", "million", "funding", "valuation",
    "ipo", "merger", "shuts down", "shutdown", "discontinued",
}

CONTROVERSY_KEYWORDS = {
    "lawsuit", "sues", "sued", "banned", "ban", "bans", "backlash",
    "controversy", "controversial", "scandal", "fired", "resigns",
    "resignation", "warns", "warning", "concerns", "criticized", "slams",
    "accuses", "accused", "fraud", "hack", "hacked", "breach", "leaked",
    "leak", "fake", "misleading", "fails", "failure", "shut down",
    "safety concerns", "risk", "danger", "dangerous", "exposed",
}

INDO_VIRAL_KEYWORDS = {
    "viral", "heboh", "geger", "gempar", "netizen", "ramai", "trending",
    "dihujat", "kecam", "murka", "kontroversi", "skandal", "bongkar",
    "terungkap", "mengejutkan", "gegerkan", "kecaman", "protes", "demo",
}

# Buat topic "Viral Global" — campur EN+ID, semua sektor (bukan cuma politik)
GLOBAL_VIRAL_KEYWORDS = {
    "viral", "trending", "goes viral", "internet reacts", "internet is",
    "everyone is talking", "sparks debate", "sparks outrage", "reacts",
    "meme", "went viral", "took over the internet",
    "heboh", "geger", "gempar", "netizen", "ramai", "bikin heboh",
    "jadi sorotan", "curi perhatian", "mendadak viral",
}

# Buat topic "AI Tools & Tutorial" — nyakup SEMUA tools & model AI (open-source
# maupun berbayar), rilis baru, sampai tutorial/cara pakainya. Gak dibatesin
# ke 1 angle doang (misal "alternatif tools berbayar" itu cuma salah satu jenis).
AI_TOOLS_KEYWORDS = {
    # rilis/model/tools baru (segala jenis, open-source atau bukan)
    "new ai tool", "new model", "new ai model", "ai tool launch", "launches ai",
    "introduces ai", "ai app", "ai platform", "ai assistant", "new feature",
    "update", "released", "now available", "beta", "public release",
    # pola "alternatif ke tools berbayar" — tetep relevan tapi bukan satu2nya
    "open source alternative", "free alternative to", "alternative to",
    "vs chatgpt", "vs midjourney", "vs runway", "vs notion", "cheaper than",
    "save money on ai", "ditch your subscription", "cancel your subscription",
    # self-host / local / open-source
    "open source", "open-source", "self-hosted", "self hosted", "self-host",
    "run locally", "local model", "no subscription", "unlimited generation",
    # tutorial/how-to angle (semua tools, bukan cuma open-source)
    "how to use", "how to set up", "tutorial", "step by step", "walkthrough",
    "setup guide", "install guide", "workflow", "automation workflow",
    "tips and tricks", "best practices", "prompt guide",
    # versi Indonesia — lebih umum
    "tools ai baru", "model ai baru", "rilis ai", "fitur baru ai",
    "gratis", "tanpa langganan", "alternatif gratis", "alternatif open-source",
    "hemat biaya", "gak usah bayar", "gausah bayar", "cara pakai",
    "cara install", "cara setup", "tutorial lengkap", "panduan lengkap",
    "workflow otomatis", "tips ai", "trik ai",
}

def keyword_boost(text, extra_keywords=None):
    boost = 0
    if contains_phrase(text, BIG_UPDATE_KEYWORDS):
        boost += 20
    if contains_phrase(text, CONTROVERSY_KEYWORDS):
        boost += 25
    if extra_keywords and contains_phrase(text, extra_keywords):
        boost += 25
    return boost


# ============================================================
# DEFINISI 4 PROFIL/TOPIK
# (semua share 1 chat_id grup, beda-beda cuma thread_id topic-nya)
# ============================================================

PROFILES = [
    {
        "key": "ai",
        "label": "\U0001F916 AI",
        "thread_id": _get_thread_id("TOPIC_AI_THREAD_ID"),
        "min_score": 10,
        "rss_feeds": {
            "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
            "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
            "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            "Ars Technica AI": "https://arstechnica.com/tag/artificial-intelligence/feed/",
            "Wired AI": "https://www.wired.com/feed/tag/ai/latest/rss",
            "MIT Tech Review AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
            "DailySocial (ID)": "https://dailysocial.id/feed",
            "Google News (AI)": (
                "https://news.google.com/rss/search?q=%22artificial+intelligence%22"
                "+OR+AI+OR+chatgpt+OR+llm&hl=id&gl=ID&ceid=ID:id"
            ),
        },
        "twitter_queries": [
            "(\"artificial intelligence\" OR AI OR chatgpt OR llm OR openai) min_faves:300 lang:en",
        ],
        "extra_keywords": None,
    },
    {
        "key": "crypto",
        "label": "\U0001F4B0 Crypto",
        "thread_id": _get_thread_id("TOPIC_CRYPTO_THREAD_ID"),
        "min_score": 10,
        "rss_feeds": {
            "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "Cointelegraph": "https://cointelegraph.com/rss",
            "Decrypt": "https://decrypt.co/feed",
            "The Block": "https://www.theblock.co/rss.xml",
            "CryptoSlate": "https://cryptoslate.com/feed/",
            "Bitcoin Magazine": "https://bitcoinmagazine.com/feed",
            "NewsBTC": "https://www.newsbtc.com/feed/",
            "Google News (Crypto)": (
                "https://news.google.com/rss/search?q=crypto+OR+bitcoin+OR+"
                "ethereum&hl=id&gl=ID&ceid=ID:id"
            ),
        },
        "twitter_queries": [
            "(crypto OR bitcoin OR ethereum) min_faves:300 lang:en",
        ],
        "extra_keywords": None,
    },
    {
        "key": "viral_id",
        "label": "\U0001F1EE\U0001F1E9 Viral Indonesia",
        "thread_id": _get_thread_id("TOPIC_VIRAL_THREAD_ID"),
        "min_score": 15,
        "rss_feeds": {
            "Tribunnews": "https://www.tribunnews.com/rss",
            "Liputan6 News": "https://feed.liputan6.com/rss/news",
            "Viva News": "https://www.viva.co.id/get/all",
            "Antara (EN)": "https://en.antaranews.com/rss/news.xml",
        },
        "twitter_queries": [],
        "extra_keywords": INDO_VIRAL_KEYWORDS,
    },
    {
        "key": "entertainment_id",
        "label": "\U0001F3AC Entertainment Indonesia",
        "thread_id": _get_thread_id("TOPIC_ENTERTAINMENT_THREAD_ID"),
        "min_score": 20,
        "rss_feeds": {
            "KapanLagi": "https://www.kapanlagi.com/feed",
            "Liputan6 Showbiz": "https://feed.liputan6.com/rss/showbiz",
            "Viva Showbiz": "https://www.viva.co.id/get/showbiz",
        },
        "twitter_queries": [],
        "extra_keywords": INDO_VIRAL_KEYWORDS,
    },
    {
        "key": "viral_global",
        "label": "\U0001F30D Viral Global",
        "thread_id": _get_thread_id("TOPIC_VIRAL_GLOBAL_THREAD_ID"),
        "min_score": 20,
        "rss_feeds": {
            "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
            "Reuters World": "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
            "AP News": "https://rsshub.app/apnews/topics/ap-top-news",
            "Google News (Global Viral, EN)": (
                "https://news.google.com/rss/search?q=viral+OR+%22goes+viral%22+"
                "OR+trending&hl=en-US&gl=US&ceid=US:en"
            ),
            "Google News (Global Viral, ID)": (
                "https://news.google.com/rss/search?q=viral+OR+heboh+OR+"
                "trending&hl=id&gl=ID&ceid=ID:id"
            ),
            "Detik News": "https://rss.detik.com/index.php/detikcom",
            "Kompas News": "https://rss.kompas.com/index.php/tag/-",
        },
        "twitter_queries": [
            "(viral OR trending) min_faves:1000 lang:en",
        ],
        "extra_keywords": GLOBAL_VIRAL_KEYWORDS,
    },
    {
        "key": "politics_id",
        "label": "\U0001F3DB\uFE0F Politik Indonesia",
        # Pakai variable baru jika ada; fallback ke thread AI Tools lama.
        "thread_id": _get_thread_id("TOPIC_POLITICS_THREAD_ID") or _get_thread_id("TOPIC_AI_TOOLS_THREAD_ID"),
        "min_score": 35,
        "max_age_hours": 2,
        "rss_feeds": {
            "ANTARA Politik": "https://www.antaranews.com/rss/politik.xml",
            "CNN Indonesia Nasional": "https://www.cnnindonesia.com/nasional/rss",
            "Tempo Nasional": "https://rss.tempo.co/nasional",
            "Liputan6 News": "https://feed.liputan6.com/rss/news",
            "Tribunnews Nasional": "https://www.tribunnews.com/rss",
            "Viva Politik": "https://www.viva.co.id/get/politik",
            "CNBC Indonesia News": "https://www.cnbcindonesia.com/news/rss",
            "Republika": "https://www.republika.co.id/rss",
            "Suara News": "https://www.suara.com/rss/news",
            "Google News - Politik Indonesia": (
                "https://news.google.com/rss/search?q=politik+Indonesia+when%3A1d&hl=id&gl=ID&ceid=ID:id"
            ),
            "Google News - Pemerintah & Kabinet": (
                "https://news.google.com/rss/search?q=%28pemerintah+OR+presiden+OR+menteri+OR+kabinet%29+Indonesia+when%3A1d&hl=id&gl=ID&ceid=ID:id"
            ),
            "Google News - DPR & RUU": (
                "https://news.google.com/rss/search?q=%28DPR+OR+MPR+OR+RUU+OR+undang-undang%29+when%3A1d&hl=id&gl=ID&ceid=ID:id"
            ),
            "Google News - Partai & Pemilu": (
                "https://news.google.com/rss/search?q=%28partai+OR+pemilu+OR+pilkada+OR+KPU+OR+Bawaslu%29+Indonesia+when%3A1d&hl=id&gl=ID&ceid=ID:id"
            ),
            "Google News - KPK & Politik Hukum": (
                "https://news.google.com/rss/search?q=%28KPK+OR+korupsi+OR+MK%29+politik+Indonesia+when%3A1d&hl=id&gl=ID&ceid=ID:id"
            ),
            "Google News - DPR RI Resmi": (
                "https://news.google.com/rss/search?q=site%3Adpr.go.id+when%3A3d&hl=id&gl=ID&ceid=ID:id"
            ),
            "Google News - KPU/Bawaslu Resmi": (
                "https://news.google.com/rss/search?q=%28site%3Akpu.go.id+OR+site%3Abawaslu.go.id%29+when%3A3d&hl=id&gl=ID&ceid=ID:id"
            ),
        },
        "twitter_queries": [],
        "extra_keywords": INDO_VIRAL_KEYWORDS | CONTROVERSY_KEYWORDS,
        "max_items": POLITICS_MAX_ITEMS,
    },
]


# ============================================================
# PENYIMPANAN "SUDAH PERNAH DIKIRIM" (per-profile, dalam 1 file)
# ============================================================

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_seen(seen_set):
    trimmed = list(seen_set)[-5000:]
    with open(SEEN_FILE, "w") as f:
        json.dump(trimmed, f)


def load_signatures():
    """Simpen 'sidik jari' keyword tiap berita yang udah dikirim, per topic.
    Dipake buat cegah berita yang MIRIP (walau link/id beda) kekirim lagi."""
    if os.path.exists(SIGNATURES_FILE):
        try:
            with open(SIGNATURES_FILE, "r") as f:
                raw = json.load(f)
            now = time.time()
            result = {}
            for key, entries in raw.items():
                cleaned = []
                for entry in entries:
                    if isinstance(entry, dict):
                        timestamp = float(entry.get("timestamp", now))
                        if now - timestamp <= DEDUPE_HOURS * 3600:
                            cleaned.append(entry)
                    elif isinstance(entry, list):
                        # Migrasi format lama. Dipertahankan satu periode dedupe.
                        cleaned.append({"tokens": entry, "entities": [], "timestamp": now})
                result[key] = cleaned
            return result
        except Exception:
            return {}
    return {}


def save_signatures(sig_dict):
    cutoff = time.time() - DEDUPE_HOURS * 3600
    trimmed = {
        k: [entry for entry in entries if entry.get("timestamp", 0) >= cutoff][-500:]
        for k, entries in sig_dict.items()
    }
    with open(SIGNATURES_FILE, "w") as f:
        json.dump(trimmed, f)


# ============================================================
# UTIL
# ============================================================

def clean_html(raw_html):
    import re
    return re.sub(r"<[^>]+>", "", raw_html or "").strip()


def is_recent_enough(published_struct, max_hours=MAX_AGE_HOURS):
    if not published_struct:
        return True
    try:
        published_dt = datetime(*published_struct[:6], tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - published_dt
        return age <= timedelta(hours=max_hours)
    except Exception:
        return True


def parse_twitter_date(created_at_str):
    try:
        import time as time_module
        return time_module.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
    except Exception:
        return None


# ============================================================
# AMBIL BERITA DARI RSS
# ============================================================

def fetch_rss_items(rss_feeds, max_age_hours=MAX_AGE_HOURS):
    items = []
    for source_name, url in rss_feeds.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if not is_recent_enough(published, max_hours=max_age_hours):
                    continue
                preview = clean_html(entry.get("summary", ""))[:200]
                items.append({
                    "id": entry.get("link", entry.get("id", "")),
                    "title": entry.get("title", "(tanpa judul)"),
                    "preview": preview,
                    "link": entry.get("link", ""),
                    "source": source_name,
                    "score": None,
                })
        except Exception as e:
            log.warning(f"Gagal ambil RSS dari {source_name}: {e}")
    return items


# ============================================================
# AMBIL TWEET DARI X/TWITTER
# ============================================================

def fetch_twitter_items(queries):
    items = []
    if not TWITTERAPI_KEY or not queries:
        return items

    headers = {"X-API-Key": TWITTERAPI_KEY}
    for query in queries:
        url = "https://api.twitterapi.io/twitter/tweet/advanced_search"
        params = {"query": query, "queryType": "Latest"}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            for tweet in data.get("tweets", [])[:15]:
                created_at = parse_twitter_date(tweet.get("createdAt", ""))
                if not is_recent_enough(created_at):
                    continue
                tweet_id = tweet.get("id", "")
                author = tweet.get("author", {}).get("userName", "unknown")
                text = tweet.get("text", "(tanpa teks)")
                likes = tweet.get("likeCount", 0)
                retweets = tweet.get("retweetCount", 0)
                items.append({
                    "id": f"tw_{tweet_id}",
                    "title": text[:100],
                    "preview": text[:250],
                    "link": f"https://twitter.com/{author}/status/{tweet_id}",
                    "source": "X/Twitter",
                    "score": likes + retweets,
                })
        except Exception as e:
            log.warning(f"Gagal ambil dari X/Twitter (query: {query[:30]}...): {e}")
        time.sleep(2)
    return items


# ============================================================
# SISTEM SCORING VIRAL (0-100)
# ============================================================

def normalize_text(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def get_keywords(title):
    words = normalize_text(title).split()
    return {w for w in words if len(w) >= 3 and w not in STOPWORDS}


def get_entities(title):
    """Angka dan nama/proyek yang relatif khas membantu mengenali parafrasa."""
    raw_words = re.findall(r"\b[A-Z][A-Za-z0-9.-]{2,}\b|\b\d+(?:[.,]\d+)?%?\b", title or "")
    return {normalize_text(word) for word in raw_words if normalize_text(word)}


def make_signature(title):
    return {
        "tokens": sorted(get_keywords(title)),
        "entities": sorted(get_entities(title)),
        "timestamp": time.time(),
    }


def signature_similarity(left, right):
    left_tokens, right_tokens = set(left.get("tokens", [])), set(right.get("tokens", []))
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = left_tokens & right_tokens
    jaccard = len(overlap) / len(left_tokens | right_tokens)
    containment = len(overlap) / min(len(left_tokens), len(right_tokens))
    left_entities, right_entities = set(left.get("entities", [])), set(right.get("entities", []))
    entity_match = bool(left_entities & right_entities)
    return max(jaccard, containment * (0.9 if entity_match else 0.72))


def is_duplicate_signature(candidate, previous):
    return signature_similarity(candidate, previous) >= 0.56


def contains_phrase(text, phrases):
    normalized = f" {normalize_text(text)} "
    return any(f" {normalize_text(phrase)} " in normalized for phrase in phrases)


def passes_content_filter(profile, item):
    key = profile["key"]
    text = f"{item['title']} {item.get('preview', '')}"
    normalized = normalize_text(text)

    required = TOPIC_RELEVANCE.get(key)
    if required and not contains_phrase(normalized, required):
        return False, "tidak relevan dengan topic"

    if key == "ai_tools":
        if contains_phrase(normalized, NOT_PUBLIC_PATTERNS):
            return False, "belum tersedia untuk publik"
        tool_signal = contains_phrase(normalized, AI_TOOLS_KEYWORDS) or contains_phrase(
            normalized, {"github", "tool", "app", "tutorial", "workflow", "api", "open source", "self hosted"}
        )
        if not tool_signal:
            return False, "bukan tools/tutorial"

    return True, ""


def build_ai_tools_content_idea(item):
    """Bikin arahan konten sederhana tanpa AI/generative API."""
    title = item["title"].strip()
    text = f"{title} {item.get('preview', '')}"

    if contains_phrase(text, {"open source", "open-source", "self hosted", "self-hosted", "free alternative"}):
        angle = "Alternatif gratis/open-source untuk memangkas biaya subscription"
        hook = f"Gak harus bayar mahal: coba alternatif dari {title}"
        points = "fungsi utama, tool berbayar yang bisa diganti, cara mulai, dan biaya server/API"
    elif contains_phrase(text, {"how to", "tutorial", "guide", "workflow", "step by step", "automation"}):
        angle = "Tutorial praktis yang bisa langsung diikuti"
        hook = f"Cara pakai {title} untuk workflow kerja yang lebih cepat"
        points = "masalah awal, langkah setup, contoh penggunaan, hasil, dan batasannya"
    elif contains_phrase(text, {"vs", "alternative to", "comparison", "cheaper than"}):
        angle = "Perbandingan tool untuk membantu audiens memilih"
        hook = f"Sebelum langganan, bandingkan dulu: {title}"
        points = "fitur, harga, kemudahan, kualitas hasil, privasi, dan target pengguna"
    elif contains_phrase(text, {"launch", "launches", "released", "release", "new feature", "update", "now available"}):
        angle = "Update tool baru dan dampaknya ke workflow pengguna"
        hook = f"Update ini layak dicoba? {title}"
        points = "apa yang berubah, siapa yang terbantu, contoh use case, akses, harga, dan kekurangan"
    else:
        angle = "Eksplorasi tool dan use case nyata"
        hook = f"Tool AI ini bisa dipakai buat apa? {title}"
        points = "fungsi utama, target pengguna, demo singkat, hasil nyata, harga, dan alternatif"

    return {"angle": angle, "hook": hook, "points": points}


def compute_viral_scores(items, extra_keywords=None):
    for item in items:
        item["_kw"] = get_keywords(item["title"])

    for item in items:
        score = 0.0
        source = item["source"]
        raw = item.get("score")

        if source == "X/Twitter":
            score += min((raw or 0) / 20, 40)
        else:
            score += 10

        score += keyword_boost(item["title"] + " " + item.get("preview", ""), extra_keywords)

        matched_sources = {source}
        for other in items:
            if other is item or other["source"] == source:
                continue
            left = {"tokens": item["_kw"], "entities": get_entities(item["title"])}
            right = {"tokens": other["_kw"], "entities": get_entities(other["title"])}
            if signature_similarity(left, right) >= 0.48:
                matched_sources.add(other["source"])

        extra_sources = len(matched_sources) - 1
        score += min(extra_sources * 25, 50)

        item["viral_score"] = round(min(score, 100), 1)
        item["matched_sources"] = matched_sources

    for item in items:
        del item["_kw"]

    return items


def get_tier_label(score):
    if score >= 70:
        return "\U0001F525\U0001F525\U0001F525 SUPER HOT"
    elif score >= 45:
        return "\U0001F525\U0001F525 HOT"
    elif score >= 25:
        return "\U0001F525 Trending"
    else:
        return "\U0001F4F0 Info"


# ============================================================
# KIRIM KE TELEGRAM
# ============================================================

def send_telegram_message(chat_id, text, thread_id=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    if thread_id is not None:
        payload["message_thread_id"] = thread_id
    try:
        resp = requests.post(url, data=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        # Coba tampilin pesan error dari Telegram (biasanya lebih jelas)
        detail = ""
        try:
            detail = f" | Respon Telegram: {resp.text}"
        except Exception:
            pass
        log.error(f"Gagal kirim ke Telegram (chat_id={chat_id}, thread_id={thread_id}): {e}{detail}")
        return False


# ============================================================
# PERINTAH /tr: TERJEMAHKAN PESAN YANG DI-REPLY
# ============================================================

def load_telegram_offset():
    try:
        with open(TELEGRAM_OFFSET_FILE, "r") as f:
            return int(json.load(f).get("offset", 0))
    except Exception:
        return 0


def save_telegram_offset(offset):
    try:
        with open(TELEGRAM_OFFSET_FILE, "w") as f:
            json.dump({"offset": offset}, f)
    except Exception as e:
        log.warning(f"Gagal simpan Telegram update offset: {e}")


def split_translation_chunks(text, max_chars=350):
    words = (text or "").split()
    chunks, current = [], []
    for word in words:
        if current and len(" ".join(current + [word])) > max_chars:
            chunks.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        chunks.append(" ".join(current))
    return chunks


def translate_to_indonesian(text):
    """Terjemahan gratis via MyMemory; URL dipertahankan apa adanya."""
    if not text or not text.strip():
        return ""

    urls = re.findall(r"https?://\S+", text)
    protected = text
    for index, url in enumerate(urls):
        protected = protected.replace(url, f" URLTOKEN{index} ")

    translated_chunks = []
    for chunk in split_translation_chunks(protected):
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": chunk, "langpair": f"{TRANSLATE_SOURCE_LANG}|id"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        translated = data.get("responseData", {}).get("translatedText")
        if not translated or int(data.get("responseStatus", 200)) >= 400:
            raise RuntimeError(data.get("responseDetails") or "Terjemahan kosong")
        translated_chunks.append(translated)

    result = "\n\n".join(translated_chunks)
    for index, url in enumerate(urls):
        result = re.sub(rf"URLTOKEN\s*{index}", url, result, flags=re.IGNORECASE)
    return result


def send_translate_reply(message, text):
    chat_id = message.get("chat", {}).get("id")
    if not chat_id:
        return
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_to_message_id": message.get("message_id"),
        "allow_sending_without_reply": True,
    }
    thread_id = message.get("message_thread_id")
    if thread_id is not None:
        payload["message_thread_id"] = thread_id
    resp = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data=payload,
        timeout=15,
    )
    resp.raise_for_status()


def handle_translate_command(message):
    command = (message.get("text") or "").strip().split()[0].lower()
    if command.split("@")[0] != "/tr":
        return

    replied = message.get("reply_to_message")
    if not replied:
        send_translate_reply(message, "Reply pesan yang mau diterjemahkan, lalu ketik <b>/tr</b>.")
        return

    original = replied.get("text") or replied.get("caption") or ""
    if not original.strip():
        send_translate_reply(message, "Pesan tersebut tidak memiliki teks yang bisa diterjemahkan.")
        return

    try:
        translated = translate_to_indonesian(original[:3500])
        safe_text = html.escape(translated)
        send_translate_reply(message, f"🇮🇩 <b>Terjemahan:</b>\n\n{safe_text}"[:4096])
    except Exception as e:
        log.warning(f"Gagal menerjemahkan pesan: {e}")
        send_translate_reply(message, "Terjemahan sedang gagal. Coba lagi beberapa saat nanti.")


def telegram_command_loop():
    offset = load_telegram_offset()
    log.info("Listener perintah /tr aktif untuk semua Topic.")
    while True:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 25, "allowed_updates": json.dumps(["message"])},
                timeout=35,
            )
            resp.raise_for_status()
            for update in resp.json().get("result", []):
                offset = int(update["update_id"]) + 1
                message = update.get("message")
                if message:
                    handle_translate_command(message)
                save_telegram_offset(offset)
        except Exception as e:
            log.warning(f"Listener /tr error: {e}")
            time.sleep(5)


def format_message(item):
    score_line = f"\u2b06\ufe0f Score: {item['score']}\n" if item.get("score") else ""
    tier = get_tier_label(item.get("viral_score", 0))
    others = item.get("matched_sources", set()) - {item["source"]}
    cross_line = f"\U0001F4E1 Juga muncul di: {', '.join(others)}\n" if others else ""
    preview = item.get("preview", "")
    preview_line = f"\U0001F4AC {preview}...\n" if preview else ""
    idea = item.get("content_idea")
    idea_block = ""
    if idea:
        idea_block = (
            f"\n\U0001F3AF <b>Angle:</b> {idea['angle']}\n"
            f"\U0001F4A1 <b>Ide judul:</b> {idea['hook']}\n"
            f"\U0001F4DD <b>Bahan bahasan:</b> {idea['points']}\n"
        )
    waktu = datetime.now().strftime("%H:%M")
    source_link = html.escape(item.get("link", ""), quote=True)
    return (
        f"{tier} (Skor: {item.get('viral_score', 0)}/100)\n"
        f"\U0001F4CC <b>{item['title']}</b>\n"
        f"{preview_line}"
        f"\U0001F4F0 Sumber: {item['source']}\n"
        f"{score_line}"
        f"{cross_line}"
        f"{idea_block}"
        f'<a href="{source_link}">\U0001F517 Buka sumber</a>\n'
        f"\u23f0 Terdeteksi: {waktu}"
    )


# ============================================================
# JALANIN 1 PROFIL/TOPIK
# ============================================================

def run_profile(profile, seen, signatures):
    key = profile["key"]
    label = profile["label"]
    thread_id = profile["thread_id"]

    if not TELEGRAM_CHAT_ID:
        log.warning(f"[{label}] TELEGRAM_CHAT_ID belum diisi di .env, skip topik ini.")
        return
    if thread_id is None:
        log.warning(f"[{label}] Thread ID topic belum diisi di .env, skip topik ini.")
        return

    all_items = fetch_rss_items(
        profile["rss_feeds"],
        max_age_hours=profile.get("max_age_hours", MAX_AGE_HOURS),
    ) + fetch_twitter_items(profile["twitter_queries"])
    all_items = compute_viral_scores(all_items, profile.get("extra_keywords"))

    for item in all_items:
        item["_uid"] = f"{key}:{item['id']}"

    candidates = [
        item for item in all_items
        if item["id"] and item["_uid"] not in seen and item["viral_score"] >= profile["min_score"]
    ]
    new_items = []
    rejected_content = 0
    for item in candidates:
        passed, reason = passes_content_filter(profile, item)
        if passed:
            if key == "ai_tools":
                item["content_idea"] = build_ai_tools_content_idea(item)
            new_items.append(item)
        else:
            rejected_content += 1
            log.info(f"[{label}] Ditolak ({reason}): {item['title'][:80]}")
    new_items.sort(key=lambda x: x["viral_score"], reverse=True)

    log.info(
        f"[{label}] Ketemu {len(all_items)} item total, "
        f"{len(new_items)} lolos kurasi (skor >= {profile['min_score']}), "
        f"{rejected_content} ditolak filter konten."
    )

    # --- Filter duplikat: skip kalau judulnya mirip (>=2 keyword sama) sama
    # berita yang UDAH PERNAH dikirim sebelumnya (persisted) atau yang lagi
    # mau dikirim di batch ini juga (misal dari 2 sumber beda, cerita sama).
    sig_list = signatures.setdefault(key, [])
    accepted_this_run = []
    final_items = []
    skipped_dupe = 0

    for item in new_items:
        signature = make_signature(item["title"])
        is_dupe = any(is_duplicate_signature(signature, old) for old in sig_list) or any(
            is_duplicate_signature(signature, old) for old in accepted_this_run
        )
        if is_dupe:
            seen.add(item["_uid"])  # jangan dipertimbangkan lagi ke depannya
            skipped_dupe += 1
            continue
        final_items.append(item)
        accepted_this_run.append(signature)

    if skipped_dupe:
        log.info(f"[{label}] {skipped_dupe} item di-skip karena mirip/duplikat.")

    final_items = final_items[:profile.get("max_items", MAX_ITEMS_PER_TOPIC)]

    for item in final_items:
        success = send_telegram_message(TELEGRAM_CHAT_ID, format_message(item), thread_id=thread_id)
        if success:
            log.info(f"[{label}] Berhasil kirim: {item['title'][:60]}")
            seen.add(item["_uid"])
            sig_list.append(make_signature(item["title"]))
        time.sleep(1)

    # Hanya item yang benar-benar dikirim atau duplikat yang dibuat permanen.
    # Kandidat yang belum cukup kuat boleh dinilai ulang pada siklus berikutnya.


# ============================================================
# LOOP UTAMA
# ============================================================

def run_once():
    seen = load_seen()
    signatures = load_signatures()
    for profile in PROFILES:
        try:
            run_profile(profile, seen, signatures)
        except Exception as e:
            log.error(f"[{profile['label']}] Error gak terduga: {e}")
    save_seen(seen)
    save_signatures(signatures)


def main():
    if not TELEGRAM_BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN belum diisi di file .env!")
        return
    if not TELEGRAM_CHAT_ID:
        log.error("TELEGRAM_CHAT_ID belum diisi di file .env!")
        return

    active_profiles = [p["label"] for p in PROFILES if p["thread_id"] is not None]
    if not active_profiles:
        log.error(
            "Gak ada satupun THREAD_ID topik yang diisi di .env! "
            "Isi minimal 1 (TOPIC_AI_THREAD_ID, TOPIC_CRYPTO_THREAD_ID, "
            "TOPIC_POLITICS_THREAD_ID, dst)."
        )
        return

    command_thread = threading.Thread(target=telegram_command_loop, daemon=True)
    command_thread.start()

    log.info(f"Bot mulai jalan... Topik aktif: {', '.join(active_profiles)}")

    if TEST_MODE:
        log.info("Mode TEST: bot cuma jalan sekali terus berhenti.")
        run_once()
        return

    while True:
        try:
            run_once()
        except Exception as e:
            log.error(f"Ada error di siklus ini, tapi bot lanjut jalan: {e}")

        log.info(f"Istirahat {CHECK_INTERVAL_SECONDS} detik dulu...")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
