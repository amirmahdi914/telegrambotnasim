"""
چک کردن سایت‌های کاریابی (مثل jobvision.ir) برای پروژه‌های جدید مرتبط با
کلمات کلیدی مشخص (مثلاً «طراحی سایت»).

⚠️ نکته مهم: قبل از اجرای مداوم روی هر سایتی، فایل robots.txt و شرایط استفاده
(Terms of Service) اون سایت رو بررسی کنید. خیلی از سایت‌های کاریابی API رسمی
دارن (مثلاً برای شرکت‌های همکار) که استفاده ازش به‌جای scraping مستقیم بهتره؛
درخواست‌های مکرر و خودکار به یه سایت می‌تونه IP شما رو مسدود کنه یا با قوانین
سایت در تضاد باشه. selectorهای زیر فقط نمونه هستن و باید متناسب با ساختار
واقعی صفحه (که ممکنه تغییر کنه) به‌روزرسانی بشن.
"""
import json
import logging
import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from config import JOB_KEYWORDS, STATE_FILE

logger = logging.getLogger(__name__)

# نمونه: صفحه جستجوی jobvision برای پروژه‌های فریلنسری/پروژه‌ای
# این URL رو متناسب با دسته‌بندی مدنظرتون تغییر بدید
SEARCH_URLS = [
    "https://jobvision.ir/jobs/keyword/%D8%B7%D8%B1%D8%A7%D8%AD%DB%8C-%D8%B3%D8%A7%DB%8C%D8%AA",
]


def _load_seen_ids() -> set:
    if Path(STATE_FILE).exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f).get("seen_job_ids", []))
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load state file")
    return set()


def _save_seen_ids(seen_ids: set) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"seen_job_ids": list(seen_ids)}, f, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to save state file")


def _matches_keywords(title: str) -> bool:
    return any(kw.lower() in title.lower() for kw in JOB_KEYWORDS)


def fetch_new_jobs() -> list[dict]:
    """لیست پروژه‌های جدیدی که قبلاً دیده نشدن و با کلمات کلیدی مچ می‌شن رو برمی‌گردونه."""
    seen_ids = _load_seen_ids()
    new_jobs: list[dict] = []

    for url in SEARCH_URLS:
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # این selector نمونه‌ست -- باید با بازرسی صفحه واقعی (Inspect Element) تنظیم بشه
            for card in soup.select("[data-job-id]"):
                job_id = card.get("data-job-id")
                title_el = card.select_one(".job-title, h2, h3")
                title = title_el.get_text(strip=True) if title_el else ""
                link_el = card.select_one("a[href]")
                link = link_el["href"] if link_el else url

                if not job_id or job_id in seen_ids:
                    continue
                if not _matches_keywords(title):
                    continue

                new_jobs.append({"id": job_id, "title": title, "link": link})
                seen_ids.add(job_id)

        except Exception:  # noqa: BLE001
            logger.exception("Failed to fetch jobs from %s", url)

    if new_jobs:
        _save_seen_ids(seen_ids)

    return new_jobs


def format_jobs_message(jobs: list[dict]) -> str:
    lines = ["🆕 پروژه‌های جدید پیدا شد:\n"]
    for j in jobs:
        lines.append(f"• {j['title']}\n  {j['link']}")
    return "\n\n".join(lines)
