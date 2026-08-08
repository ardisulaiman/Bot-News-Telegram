# -*- coding: utf-8 -*-
"""Functional test for the upgraded bot logic.

Bukan pytest — script manual yang nge-assert perilaku penting dan exit
non-zero kalau ada yang gagal. Jalankan: .venv/Scripts/python test_upgrade.py
"""
import io
import importlib.util
import os
import sys

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO_DIR)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

FAILURES = []

# repurpose-bot.py punya strip (-) di nama, jadi gak bisa di-import biasa.
_spec = importlib.util.spec_from_file_location("repurpose_bot", os.path.join(REPO_DIR, "repurpose-bot.py"))
rb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rb)


def check(name, cond, detail=""):
    status = "OK  " if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)

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
check("fetch feed baru ada isi", len(items) > 0, f"{len(items)} item")

print()
print("=" * 60)
print("5) PROFIL VIRAL (Sosmed) - ganti viral_id + viral_global")
print("=" * 60)
profiles = {p["key"]: p for p in rb.PROFILES}
viral = profiles.get("viral", {})
check("5 profil total", len(profiles) == 5, f"keys={sorted(profiles)}")
check("viral_id hilang", "viral_id" not in profiles)
check("viral_global hilang", "viral_global" not in profiles)
check("entertainment_id aman", "entertainment_id" in profiles)
check("profil viral min_score 35", viral.get("min_score") == 35)
check("profil viral max_age 2 jam", viral.get("max_age_hours") == 2)
check("profil viral max_items 5", viral.get("max_items") == rb.VIRAL_MAX_ITEMS)

print()
print("=" * 60)
print("6) PREVIEW LINK DIMATIKAN (disable_web_page_preview=True)")
print("=" * 60)
captured = {}


class FakeResp:
    def raise_for_status(self):
        pass


def fake_post(url, data=None, timeout=None, **kwargs):
    captured["data"] = data
    return FakeResp()


orig_post = rb.requests.post
rb.requests.post = fake_post
try:
    ok = rb.send_telegram_message(12345, "<b>x</b>", thread_id=678)
finally:
    rb.requests.post = orig_post
payload = captured.get("data") or {}
check("kirim sukses", ok is True)
check("disable_web_page_preview True", payload.get("disable_web_page_preview") is True)
check("parse_mode HTML", payload.get("parse_mode") == "HTML")
check("thread_id kepassing", payload.get("message_thread_id") == 678)

print()
if FAILURES:
    print(f"RESULT: {len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("RESULT: ALL CHECKS PASSED")
