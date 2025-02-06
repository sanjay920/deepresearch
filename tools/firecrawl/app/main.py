import os
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from firecrawl import FirecrawlApp

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


@app.get("/scrape", summary="Scrape a single URL")
def scrape(
    url: str = Query(..., description="The URL to scrape"),
    formats: Optional[List[str]] = Query(
        ["markdown"], description="List of formats (e.g., markdown, html)"
    ),
):
    """
    Scrape a single URL using Firecrawl and return the converted markdown.

    - **url**: The URL to scrape.
    - **formats**: A list of formats to return (default is ["markdown"]).
    """
    try:
        result = firecrawl_client.scrape_url(url=url, params={"formats": formats})
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
    """
    try:
        result = firecrawl_client.batch_scrape_urls(
            request.urls, {"formats": request.formats}
        )
    except Exception as e:
        logger.exception("Error batch scraping URLs")
        raise HTTPException(status_code=500, detail="Error batch scraping URLs")
    return result
