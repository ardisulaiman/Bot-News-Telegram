# -*- coding: utf-8 -*-
"""Functional test for the upgraded bot logic."""
import io
import importlib.util
import os
import sys

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO_DIR)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# repurpose-bot.py punya strip (-) di nama, jadi gak bisa di-import biasa.
_spec = importlib.util.spec_from_file_location("repurpose_bot", os.path.join(REPO_DIR, "repurpose-bot.py"))
rb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rb)

print("=" * 60)
print("1) GENERATOR IDE KONTEN - 6 tema berbeda, 3 judul contoh")
print("=" * 60)
samples = [
    "How to build a RAG pipeline with Claude in 20 minutes",
    "ChatGPT vs Gemini vs Claude: which is worth the subscription in 2026",
    "OpenAI announces GPT-6 with record-breaking benchmark results",
]
for title in samples:
    for theme in rb.AI_TOOLS_THEMES + [None]:
        idea = rb.build_ai_tools_content_idea({"title": title, "preview": ""}, theme=theme)
        print(f"  [{theme or 'no-theme':>9}] {title[:45]}")
        print(f"           -> {idea['angle']} | {idea['hook'][:60]}")

print()
print("=" * 60)
print("2) FILTER KONTEN ai_tools")
print("=" * 60)
profile = {"key": "ai_tools"}
tests = [
    ("OpenAI launches new model", "harus lolos (berita AI)"),
    ("How to use Cursor AI for coding", "harus lolos (tutorial)"),
    ("Join the waitlist for our new AI app", "harus DITOLAK (coming soon)"),
    ("Secret AI tool invite only for select users", "harus DITOLAK (invite only)"),
]
for title, expect in tests:
    passed, reason = rb.passes_content_filter(profile, {"title": title, "preview": ""})
    print(f"  {'LOLOS ' if passed else 'TOLAK '} | {title}  [{expect}]" + (f" ({reason})" if not passed else ""))

print()
print("=" * 60)
print("3) SCORING - item tools/tutorial dapat boost dari AI_TOOLS_KEYWORDS")
print("=" * 60)
items = [
    {"id": "a", "title": "New open source AI tool launches for free", "preview": "open-source alternative to paid tools", "link": "x", "source": "TechCrunch AI", "score": None},
    {"id": "b", "title": "Researcher publishes paper on neural attention", "preview": "study of model internals", "link": "y", "source": "Ars Technica AI", "score": None},
]
rb.compute_viral_scores(items, rb.AI_TOOLS_KEYWORDS)
for it in items:
    print(f"  {it['viral_score']:>5} | {it['title']}")

print()
print("=" * 60)
print("4) FETCH FEED BARU (timeout 12s per feed)")
print("=" * 60)
feeds = {
    "Kompas via GN": "https://news.google.com/rss/search?q=site%3Akompas.com+when%3A1d&hl=id&gl=ID&ceid=ID:id",
    "Simon Willison": "https://simonwillison.net/atom/everything/",
    "GN AI Tools ID": "https://news.google.com/rss/search?q=%28AI+tools+OR+ChatGPT+tips+OR+AI+tutorial%29+when%3A1d&hl=id&gl=ID&ceid=ID:id",
}
items = rb.fetch_rss_items(feeds, max_age_hours=48)
print(f"  Total item tertarik: {len(items)}")
for it in items[:5]:
    print(f"   - [{it['source']}] {it['title'][:70]}")
