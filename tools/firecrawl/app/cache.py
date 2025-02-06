import sqlite3
import json
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "cache.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Added scraped_at column to store the timestamp as TEXT (ISO 8601 formatted)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS scrape_cache (
            url TEXT NOT NULL,
            formats TEXT NOT NULL,
            scrape_result TEXT NOT NULL,
            scraped_at TEXT NOT NULL,
            PRIMARY KEY (url, formats)
        );
        """
    )
    conn.commit()
    conn.close()


init_db()


def get_cached_result(url: str, formats: list[str]) -> dict | None:
    """
    Returns the cached Firecrawl result from the DB if it exists.
    Otherwise returns None.

    You can later extend this function to also return the scraped_at timestamp if needed.
    """
    # Normalize the formats so that the same set always produces the same key.
    formats_str = json.dumps(sorted(formats))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT scrape_result FROM scrape_cache WHERE url = ? AND formats = ?",
        (url, formats_str),
    )
    row = c.fetchone()
    conn.close()

    if row is None:
        return None

    # row[0] is the stored JSON string
    return json.loads(row[0])


def store_result(url: str, formats: list[str], data: dict):
    """
    Stores the Firecrawl scrape result in the DB.
    Overwrites existing entry for the same (url, formats) if present.
    Also stores the current UTC timestamp as scraped_at.
    """
    formats_str = json.dumps(sorted(formats))
    data_str = json.dumps(data)
    # Capture the current UTC time in ISO 8601 format.
    scraped_at = datetime.datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO scrape_cache (url, formats, scrape_result, scraped_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(url, formats) DO UPDATE SET
          scrape_result = excluded.scrape_result,
          scraped_at = excluded.scraped_at
        """,
        (url, formats_str, data_str, scraped_at),
    )
    conn.commit()
    conn.close()
