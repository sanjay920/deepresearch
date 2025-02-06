import os
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from firecrawl import FirecrawlApp

from . import cache  # NEW - our caching module

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Firecrawl Microservice",
    description=(
        "A microservice API that wraps Firecrawl to scrape websites and "
        "convert them into LLM-ready markdown. It exposes two endpoints: one for "
        "scraping a single URL and another for batch scraping multiple URLs."
    ),
    version="1.0.0",
)

# Retrieve the Firecrawl API key from environment variables.
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
if not FIRECRAWL_API_KEY:
    logger.error("FIRECRAWL_API_KEY environment variable must be set")
    raise Exception("FIRECRAWL_API_KEY environment variable must be set")

# Instantiate the Firecrawl client
firecrawl_client = FirecrawlApp(api_key=FIRECRAWL_API_KEY)


class BatchScrapeRequest(BaseModel):
    urls: List[str]
    formats: Optional[List[str]] = ["markdown"]
    force_fetch: bool = False  # << NEW param for batch


@app.get("/scrape", summary="Scrape a single URL")
def scrape(
    url: str = Query(..., description="The URL to scrape"),
    formats: Optional[List[str]] = Query(
        ["markdown"], description="List of formats (e.g., markdown, html)"
    ),
    force_fetch: bool = Query(
        False,
        description="If true, do not use cache. Always fetch fresh results from Firecrawl.",
    ),
):
    """
    Scrape a single URL using Firecrawl and return the converted markdown.

    - **url**: The URL to scrape.
    - **formats**: A list of formats to return (default is ["markdown"]).
    - **force_fetch**: If true, bypass cache and fetch fresh data.
    """
    try:
        if not force_fetch:
            # Try reading from cache
            cached = cache.get_cached_result(url, formats)
            if cached is not None:
                logger.info(f"Cache hit for URL: {url}, formats={formats}")
                return cached

        # Either cache miss or force_fetch is True -> scrape from Firecrawl
        logger.info(f"Scraping fresh content for URL: {url}, formats={formats}")
        result = firecrawl_client.scrape_url(url=url, params={"formats": formats})

        # Store in cache
        cache.store_result(url, formats, result)

    except Exception as e:
        logger.exception("Error scraping URL")
        raise HTTPException(status_code=500, detail="Error scraping URL")
    return result


@app.post("/batch_scrape_urls", summary="Batch scrape multiple URLs")
def batch_scrape(request: BatchScrapeRequest):
    """
    Batch scrape multiple URLs using Firecrawl.

    - **urls**: A list of URLs to scrape.
    - **formats**: A list of formats to return (default is ["markdown"]).
    - **force_fetch**: If true, bypass cache and fetch fresh data for each URL.
    """
    try:
        # We'll accumulate results in the same shape Firecrawl returns:
        # { 'success': True, 'status': 'completed', 'data': [...], ... }
        # But we need to handle each URL individually in the cache.

        # If not force_fetch, try to see which URLs are in the cache
        if not request.force_fetch:
            all_cached = True
            results_data = []

            # We'll keep track of which URLs we still need to fetch from Firecrawl
            urls_to_fetch = []
            for url in request.urls:
                cached = cache.get_cached_result(url, request.formats or ["markdown"])
                if cached is not None:
                    # We have it in the cache
                    results_data.append(cached)
                else:
                    # We'll need to fetch this
                    all_cached = False
                    urls_to_fetch.append(url)

            if len(urls_to_fetch) > 0:
                # We do a batch scrape for those not found in cache
                logger.info(f"Scraping fresh content for these URLs: {urls_to_fetch}")
                batch_result = firecrawl_client.batch_scrape_urls(
                    urls_to_fetch, {"formats": request.formats}
                )

                # Firecrawl returns 'data': [ {...}, {...}, ... ] in batch_result
                # We'll store each item in the cache
                if batch_result.get("data"):
                    for idx, url in enumerate(urls_to_fetch):
                        cache.store_result(
                            url, request.formats, batch_result["data"][idx]
                        )
                        results_data.append(batch_result["data"][idx])

                # Merge any top-level keys Firecrawl normally returns
                # This is a simple approach: we'll preserve 'status', 'success', etc.
                # The only difference is our combined results_data
                combined_result = {
                    **batch_result,
                    "data": results_data,
                }
                return combined_result
            else:
                # If we had everything in the cache, build a Firecrawl-like response
                return {
                    "success": True,
                    "status": "completed",
                    "total": len(request.urls),
                    "completed": len(request.urls),
                    "data": results_data,
                }
        else:
            # force_fetch = True -> bypass cache altogether
            logger.info("Batch scraping with force_fetch=True (bypassing cache).")
            batch_result = firecrawl_client.batch_scrape_urls(
                request.urls, {"formats": request.formats}
            )

            # Store each item from Firecrawl in the cache
            if batch_result.get("data"):
                for idx, url in enumerate(request.urls):
                    cache.store_result(url, request.formats, batch_result["data"][idx])

            return batch_result
    except Exception:
        logger.exception("Error batch scraping URLs")
        raise HTTPException(status_code=500, detail="Error batch scraping URLs")
