#!/usr/bin/env python3
import os
import re
import time
import html
import sqlite3
import logging
from pathlib import Path
from typing import Any, Iterable

import requests
import feedparser
from dotenv import load_dotenv


load_dotenv()

RSS_URL = os.getenv("RSS_URL", "https://rss.nodeseek.com/")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "180"))

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "").strip()

DB_PATH = os.getenv("DB_PATH", "/opt/nodeseek-cr-rss/data/state.sqlite3")

INCLUDE_CATEGORIES = [
    x.strip().lower()
    for x in os.getenv("INCLUDE_CATEGORIES", "carpool,拼车,review,测评").split(",")
    if x.strip()
]

EXCLUDE_CATEGORIES = [
    x.strip().lower()
    for x in os.getenv("EXCLUDE_CATEGORIES", "").split(",")
    if x.strip()
]

PUSH_ON_FIRST_RUN = os.getenv("PUSH_ON_FIRST_RUN", "false").lower() == "true"
MAX_ITEMS_PER_POLL = int(os.getenv("MAX_ITEMS_PER_POLL", "20"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))

USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 NodeSeek-CR-RSS-Telegram-Bot/1.0"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

if not TG_BOT_TOKEN or not TG_CHAT_ID:
    raise SystemExit("TG_BOT_TOKEN 和 TG_CHAT_ID 不能为空，请检查 .env")

TELEGRAM_SEND_URL = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"


def init_db() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            entry_id TEXT PRIMARY KEY,
            first_seen_at INTEGER NOT NULL
        )
    """)
    conn.commit()
    return conn


def seen_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM seen").fetchone()
    return int(row[0])


def is_seen(conn: sqlite3.Connection, entry_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM seen WHERE entry_id = ? LIMIT 1",
        (entry_id,)
    ).fetchone()
    return row is not None


def mark_seen(conn: sqlite3.Connection, entry_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO seen(entry_id, first_seen_at) VALUES(?, ?)",
        (entry_id, int(time.time()))
    )
    conn.commit()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def entry_id(entry: Any) -> str:
    for key in ("id", "guid", "link", "title"):
        value = clean_text(entry.get(key))
        if value:
            return value
    return repr(entry)


def get_category_values(entry: Any) -> list[str]:
    values: list[str] = []

    category = clean_text(entry.get("category"))
    if category:
        values.append(category)

    category_detail = entry.get("category_detail")
    if isinstance(category_detail, dict):
        for key in ("term", "label"):
            value = clean_text(category_detail.get(key))
            if value:
                values.append(value)

    tags = entry.get("tags", [])
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict):
                for key in ("term", "label"):
                    value = clean_text(tag.get(key))
                    if value:
                        values.append(value)

    return values


def contains_category(values: Iterable[str], terms: list[str]) -> bool:
    if not terms:
        return True

    joined = " ".join(values).lower()

    for term in terms:
        if not term:
            continue

        if term in ("拼车", "测评", "交易"):
            if term in joined:
                return True
            continue

        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", joined):
            return True

    return False


def is_excluded(entry: Any) -> bool:
    categories = get_category_values(entry)

    # 如果设置了 INCLUDE_CATEGORIES，只允许指定版块
    if INCLUDE_CATEGORIES and not contains_category(categories, INCLUDE_CATEGORIES):
        logging.info(
            "跳过非目标版块：%s | categories=%s",
            clean_text(entry.get("title")),
            categories,
        )
        return True

    # 额外排除规则
    if EXCLUDE_CATEGORIES and contains_category(categories, EXCLUDE_CATEGORIES):
        logging.info(
            "跳过排除版块：%s | categories=%s",
            clean_text(entry.get("title")),
            categories,
        )
        return True

    return False


def fetch_feed() -> list[Any]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    }

    resp = requests.get(
        RSS_URL,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()

    parsed = feedparser.parse(resp.content)

    if getattr(parsed, "bozo", False):
        logging.warning("RSS 解析警告：%s", getattr(parsed, "bozo_exception", ""))

    return list(parsed.entries)


def format_message(entry: Any) -> str:
    """
    推送格式：
    1. 消息正文只显示帖子标题
    2. 标题本身带链接
    3. Telegram 自动显示链接预览卡片
    4. 不显示作者、板块、时间
    """
    title = clean_text(entry.get("title")) or "NodeSeek 新帖"
    link = clean_text(entry.get("link"))

    safe_title = html.escape(title)

    if not link:
        return safe_title

    safe_link = html.escape(link, quote=True)

    return f'<a href="{safe_link}">{safe_title}</a>'


def telegram_send(text: str) -> None:
    data = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    resp = requests.post(
        TELEGRAM_SEND_URL,
        data=data,
        timeout=REQUEST_TIMEOUT,
    )

    if resp.status_code == 429:
        try:
            retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
        except Exception:
            retry_after = 5

        logging.warning("Telegram 限流，等待 %s 秒后重试", retry_after)
        time.sleep(int(retry_after))

        resp = requests.post(
            TELEGRAM_SEND_URL,
            data=data,
            timeout=REQUEST_TIMEOUT,
        )

    if not resp.ok:
        logging.error("Telegram 返回错误：HTTP %s，响应：%s", resp.status_code, resp.text)

    resp.raise_for_status()


def process_once(conn: sqlite3.Connection, seed_only: bool = False) -> None:
    entries = fetch_feed()

    # 从旧到新推送
    entries.reverse()

    pending = []

    for entry in entries:
        eid = entry_id(entry)

        if is_seen(conn, eid):
            continue

        if is_excluded(entry):
            mark_seen(conn, eid)
            continue

        pending.append(entry)

    if not pending:
        logging.info("没有新的 carpool / review 帖子")
        return

    if seed_only:
        for entry in pending:
            mark_seen(conn, entry_id(entry))

        logging.info("首次运行，已记录 %s 条现有目标版块帖子，不推送", len(pending))
        return

    for entry in pending[:MAX_ITEMS_PER_POLL]:
        eid = entry_id(entry)
        title = clean_text(entry.get("title"))

        try:
            telegram_send(format_message(entry))
            mark_seen(conn, eid)
            logging.info("已推送：%s", title)
            time.sleep(1)
        except Exception as exc:
            logging.exception("推送失败：%s，错误：%s", title, exc)


def main() -> None:
    conn = init_db()

    first_run = seen_count(conn) == 0

    if first_run and not PUSH_ON_FIRST_RUN:
        process_once(conn, seed_only=True)

    while True:
        try:
            process_once(conn)
        except Exception as exc:
            logging.exception("本轮抓取失败：%s", exc)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
