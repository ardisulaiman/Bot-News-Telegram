"""
Multi-Topic News Curator Bot (No-AI Version)
--------------------------------------------
1 bot, 1 GRUP Telegram (pakai fitur Topics), 4 topik:
1 bot, 1 GRUP Telegram (pakai fitur Topics), 6 topik:
  - AI
  - Crypto
  - Viral Indonesia
  - Entertainment Indonesia
  - Entertainment Indonesia
  - Viral Global
  - Politik Indonesia

Tiap topik ambil dari sumbernya sendiri, kurasi ketat (cuma yang skornya
tinggi/menarik), lalu dikirim ke topic Telegram masing-masing (pakai
SIGNATURES_FILE = "sent_signatures.json"
MAX_ITEMS_PER_TOPIC = int(os.getenv("MAX_ITEMS_PER_TOPIC", 6))
AI_TOOLS_MAX_ITEMS = int(os.getenv("AI_TOOLS_MAX_ITEMS", 10))
POLITICS_MAX_ITEMS = int(os.getenv("POLITICS_MAX_ITEMS", 15))
DEDUPE_HOURS = int(os.getenv("DEDUPE_HOURS", 72))
TRANSLATE_SOURCE_LANG = os.getenv("TRANSLATE_SOURCE_LANG", "en")
TELEGRAM_OFFSET_FILE = "telegram_update_offset.json"
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
        ],
        "extra_keywords": GLOBAL_VIRAL_KEYWORDS,
    },
    {
        "key": "ai_tools",
        "label": "\U0001F6E0\uFE0F AI Tools & Tutorial",
        "thread_id": _get_thread_id("TOPIC_AI_TOOLS_THREAD_ID"),
    {
        "key": "politics_id",
        "label": "\U0001F3DB\uFE0F Politik Indonesia",
        # Pakai variable baru jika ada; fallback ke thread AI Tools lama.
        "thread_id": _get_thread_id("TOPIC_POLITICS_THREAD_ID") or _get_thread_id("TOPIC_AI_TOOLS_THREAD_ID"),
        "min_score": 10,
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
        "extra_keywords": AI_TOOLS_KEYWORDS,
        "max_items": AI_TOOLS_MAX_ITEMS,
        "extra_keywords": INDO_VIRAL_KEYWORDS | CONTROVERSY_KEYWORDS,
        "max_items": POLITICS_MAX_ITEMS,
    },
]

    if not active_profiles:
        log.error(
            "Gak ada satupun THREAD_ID topik yang diisi di .env! "
            "Isi minimal 1 (TOPIC_AI_THREAD_ID, TOPIC_CRYPTO_THREAD_ID, dst)."
            "Isi minimal 1 (TOPIC_AI_THREAD_ID, TOPIC_CRYPTO_THREAD_ID, "
            "TOPIC_POLITICS_THREAD_ID, dst)."
        )
        return
