"""
Multi-Topic News Curator Bot (No-AI Version)
--------------------------------------------
1 bot, 1 GRUP Telegram (pakai fitur Topics), 4 topik:
  - AI
  - Crypto
  - Viral Indonesia
  - Entertainment Indonesia

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
    lower = text.lower()
    boost = 0
    if any(kw in lower for kw in BIG_UPDATE_KEYWORDS):
        boost += 20
    if any(kw in lower for kw in CONTROVERSY_KEYWORDS):
        boost += 25
    if extra_keywords and any(kw in lower for kw in extra_keywords):
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
        "min_score": 15,
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
        "min_score": 15,
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
        "min_score": 35,
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
        "min_score": 45,
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
        "min_score": 40,
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
        "key": "ai_tools",
        "label": "\U0001F6E0\uFE0F AI Tools & Tutorial",
        "thread_id": _get_thread_id("TOPIC_AI_TOOLS_THREAD_ID"),
        "min_score": 15,
        "rss_feeds": {
            "Hacker News (AI/tools)": "https://hnrss.org/newest?q=AI+OR+open-source+OR+self-hosted&count=20",
            "GitHub Trending (daily)": "https://rsshub.app/github/trending/daily",
            "Reddit r/selfhosted": "https://www.reddit.com/r/selfhosted/.rss",
            "Reddit r/LocalLLaMA": "https://www.reddit.com/r/LocalLLaMA/.rss",
            "Reddit r/opensource": "https://www.reddit.com/r/opensource/.rss",
            "Reddit r/artificial": "https://www.reddit.com/r/artificial/.rss",
            "There's An AI For That": "https://www.theresanaiforthat.com/feed/",
            "Google News (AI Tools - luas)": (
                "https://news.google.com/rss/search?q=%22AI+tool%22+OR+"
                "%22new+AI+model%22+OR+%22AI+app%22&hl=en-US&gl=US&ceid=US:en"
            ),
            "Google News (AI Tools Open Source)": (
                "https://news.google.com/rss/search?q=%22open+source%22+AI+tool+"
                "OR+%22free+alternative%22+AI&hl=en-US&gl=US&ceid=US:en"
            ),
        },
        "twitter_queries": [],
        "extra_keywords": AI_TOOLS_KEYWORDS,
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
            return {k: [set(kws) for kws in v] for k, v in raw.items()}
        except Exception:
            return {}
    return {}


def save_signatures(sig_dict):
    trimmed = {k: [sorted(s) for s in v[-500:]] for k, v in sig_dict.items()}
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

def fetch_rss_items(rss_feeds):
    items = []
    for source_name, url in rss_feeds.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if not is_recent_enough(published):
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

def get_keywords(title):
    words = title.lower().replace(",", " ").replace(".", " ").split()
    return {w for w in words if len(w) > 4 and w not in STOPWORDS}


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
            score += 15

        score += keyword_boost(item["title"] + " " + item.get("preview", ""), extra_keywords)

        matched_sources = {source}
        for other in items:
            if other is item or other["source"] == source:
                continue
            if len(item["_kw"] & other["_kw"]) >= 2:
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


def format_message(item):
    score_line = f"\u2b06\ufe0f Score: {item['score']}\n" if item.get("score") else ""
    tier = get_tier_label(item.get("viral_score", 0))
    others = item.get("matched_sources", set()) - {item["source"]}
    cross_line = f"\U0001F4E1 Juga muncul di: {', '.join(others)}\n" if others else ""
    preview = item.get("preview", "")
    preview_line = f"\U0001F4AC {preview}...\n" if preview else ""
    waktu = datetime.now().strftime("%H:%M")
    return (
        f"{tier} (Skor: {item.get('viral_score', 0)}/100)\n"
        f"\U0001F4CC <b>{item['title']}</b>\n"
        f"{preview_line}"
        f"\U0001F4F0 Sumber: {item['source']}\n"
        f"{score_line}"
        f"{cross_line}"
        f"\U0001F517 {item['link']}\n"
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

    all_items = fetch_rss_items(profile["rss_feeds"]) + fetch_twitter_items(profile["twitter_queries"])
    all_items = compute_viral_scores(all_items, profile.get("extra_keywords"))

    for item in all_items:
        item["_uid"] = f"{key}:{item['id']}"

    new_items = [
        item for item in all_items
        if item["id"] and item["_uid"] not in seen and item["viral_score"] >= profile["min_score"]
    ]
    new_items.sort(key=lambda x: x["viral_score"], reverse=True)

    log.info(
        f"[{label}] Ketemu {len(all_items)} item total, "
        f"{len(new_items)} lolos kurasi (skor >= {profile['min_score']})."
    )

    # --- Filter duplikat: skip kalau judulnya mirip (>=2 keyword sama) sama
    # berita yang UDAH PERNAH dikirim sebelumnya (persisted) atau yang lagi
    # mau dikirim di batch ini juga (misal dari 2 sumber beda, cerita sama).
    sig_list = signatures.setdefault(key, [])
    accepted_this_run = []
    final_items = []
    skipped_dupe = 0

    for item in new_items:
        kw = get_keywords(item["title"])
        is_dupe = any(len(kw & s) >= 2 for s in sig_list) or any(
            len(kw & s) >= 2 for s in accepted_this_run
        )
        if is_dupe:
            seen.add(item["_uid"])  # jangan dipertimbangkan lagi ke depannya
            skipped_dupe += 1
            continue
        final_items.append(item)
        accepted_this_run.append(kw)

    if skipped_dupe:
        log.info(f"[{label}] {skipped_dupe} item di-skip karena mirip/duplikat.")

    for item in final_items:
        success = send_telegram_message(TELEGRAM_CHAT_ID, format_message(item), thread_id=thread_id)
        if success:
            log.info(f"[{label}] Berhasil kirim: {item['title'][:60]}")
            seen.add(item["_uid"])
            sig_list.append(get_keywords(item["title"]))
        time.sleep(1)

    for item in all_items:
        if item["id"]:
            seen.add(item["_uid"])


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
            "Isi minimal 1 (TOPIC_AI_THREAD_ID, TOPIC_CRYPTO_THREAD_ID, dst)."
        )
        return

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
