"""
دریافت قیمت دلار و طلا در بازار ایران (از tgju.org) و قیمت ارزهای دیجیتال (از CoinGecko).

نکته مهم: tgju.org یک API رسمی و مستند عمومی نداره، برای همین اینجا از HTML صفحه
استخراج می‌کنیم (web scraping). اگه ساختار سایت تغییر کنه، ممکنه selectorها نیاز
به به‌روزرسانی داشته باشن. برای استفاده‌ی تجاری/پرحجم بهتره از یه سرویس API
رسمی و پولی (مثل navasan.net) استفاده کنید تا پایدارتر باشه و با قوانین سایت
مبدا در تضاد نباشه.
"""
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TGJU_URL = "https://www.tgju.org/"
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"


def get_iran_market_prices() -> dict:
    """قیمت دلار و طلای ۱۸ عیار رو از tgju.org برمی‌گردونه (به تومان)."""
    result = {"dollar": None, "gold_18k": None}
    try:
        resp = requests.get(TGJU_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        dollar_el = soup.select_one("#l-price_dollar_rl .info-price")
        if dollar_el:
            result["dollar"] = dollar_el.get_text(strip=True)

        gold_el = soup.select_one("#l-geram18 .info-price")
        if gold_el:
            result["gold_18k"] = gold_el.get_text(strip=True)

    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch tgju prices")

    return result


def get_top_crypto(limit: int = 5) -> list[dict]:
    """لیست چند ارز دیجیتال برتر رو با قیمت و تغییرات ۲۴ ساعته برمی‌گردونه.

    این تابع فقط داده‌ی بازار (قیمت، حجم، درصد تغییر) رو برمی‌گردونه و
    هیچ توصیه‌ی سرمایه‌گذاری تولید نمی‌کنه؛ تصمیم‌گیری بر عهده‌ی خود کاربره.
    """
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "price_change_percentage": "24h",
    }
    try:
        resp = requests.get(COINGECKO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "name": c["name"],
                "symbol": c["symbol"].upper(),
                "price_usd": c["current_price"],
                "change_24h_pct": c.get("price_change_percentage_24h"),
            }
            for c in data
        ]
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch crypto prices")
        return []


def format_price_report() -> str:
    """یک متن آماده برای ارسال در تلگرام می‌سازه."""
    fa = get_iran_market_prices()
    crypto = get_top_crypto()

    lines = ["📊 گزارش قیمت روزانه\n"]
    lines.append(f"💵 دلار: {fa['dollar'] or 'در دسترس نبود'} تومان")
    lines.append(f"🪙 طلا ۱۸ عیار: {fa['gold_18k'] or 'در دسترس نبود'} تومان")
    lines.append("")
    lines.append("💰 ارزهای دیجیتال برتر (فقط اطلاعات بازار، نه توصیه‌ی سرمایه‌گذاری):")
    for c in crypto:
        change = c["change_24h_pct"]
        change_str = f"{change:+.2f}%" if change is not None else "نامشخص"
        lines.append(f"- {c['name']} ({c['symbol']}): ${c['price_usd']:,} | 24h: {change_str}")

    return "\n".join(lines)
