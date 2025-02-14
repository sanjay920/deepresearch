import sqlite3
import json
import os
import datetime

# Path to the cache database
DB_PATH = os.path.join(os.path.dirname(__file__), "cache.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS tavily_cache (
            url TEXT NOT NULL,
            options TEXT NOT NULL,
            scrape_result TEXT NOT NULL,
            scraped_at TEXT NOT NULL,
            PRIMARY KEY (url, options)
        );
        """
    )
    conn.commit()
    conn.close()


init_db()


def get_cached_result(url: str, options: dict) -> dict | None:
    """
    Returns the cached result (converted to markdown) if present.
    """
    options_str = json.dumps(options, sort_keys=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT scrape_result FROM tavily_cache WHERE url = ? AND options = ?",
        (url, options_str),
    )
    row = c.fetchone()
    conn.close()
    if row is None:
        return None
    return json.loads(row[0])


def store_result(url: str, options: dict, data: dict):
    """
    Stores the result in cache.
    """
    options_str = json.dumps(options, sort_keys=True)
    data_str = json.dumps(data)
    scraped_at = datetime.datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO tavily_cache (url, options, scrape_result, scraped_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(url, options) DO UPDATE SET
          scrape_result = excluded.scrape_result,
          scraped_at = excluded.scraped_at
        """,
        (url, options_str, data_str, scraped_at),
    )
    conn.commit()
    conn.close()
