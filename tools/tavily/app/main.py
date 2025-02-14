import os
import logging
from typing import List, Optional, Union

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import requests

import cache
import markdown_converter
from tavily import TavilyClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Tavily Microservice",
    description="A microservice API wrapper around Tavily Extract. It scrapes URLs and converts the content into markdown.",
    version="1.0.0",
)

# Retrieve the Tavily API key from the environment variable.
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    logger.error("TAVILY_API_KEY environment variable must be set")
    raise Exception("TAVILY_API_KEY environment variable must be set")

# Instantiate Tavily API client.
tavily_client_instance = TavilyClient(api_key=TAVILY_API_KEY)


class ScrapeRequest(BaseModel):
    urls: Union[str, List[str]]
    force_fetch: bool = False


@app.post("/scrape_urls", summary="Scrape one or more URLs")
def scrape_urls(request: ScrapeRequest):
    """
    Scrapes one or more URLs using Tavily and returns the content in markdown.

    Request Body:
    - urls: Single URL string or list of URLs to scrape
    - force_fetch: If true, bypass the cache and fetch fresh data
    """
    # Convert single URL to list for consistent handling
    urls_to_process = [request.urls] if isinstance(request.urls, str) else request.urls

    options = {
        "include_images": False,
        "extract_depth": "advanced",
    }
    results_data = []
    urls_to_fetch = []

    # Check cache for each URL if not forcing fetch
    if not request.force_fetch:
        for url in urls_to_process:
            cached = cache.get_cached_result(url, options)
            if cached is not None:
                logger.info(f"Cache hit for URL: {url} with options: {options}")
                results_data.append(cached)
            else:
                urls_to_fetch.append(url)
    else:
        urls_to_fetch = urls_to_process

    if urls_to_fetch:
        logger.info(
            f"Fetching fresh content for URLs: {urls_to_fetch} with options: {options}"
        )
        try:
            response_data = tavily_client_instance.extract(
                urls=urls_to_fetch, include_images=False, extract_depth="advanced"
            )

            # Process each successful result
            if "results" in response_data:
                for result in response_data["results"]:
                    raw_content = result.get("raw_content", "")
                    markdown_output = markdown_converter.convert_html_to_markdown(
                        raw_content
                    )
                    final_result = {
                        "url": result.get("url"),
                        "markdown": markdown_output,
                    }
                    # Cache the result
                    cache.store_result(result.get("url"), options, final_result)
                    results_data.append(final_result)
            else:
                raise HTTPException(
                    status_code=404,
                    detail="No extraction results returned from Tavily.",
                )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [401, 403]:
                logger.error("Tavily API authentication failed")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "authentication_failed",
                        "message": "Tavily authentication failed. Please check your API key configuration.",
                    },
                )
            else:
                logger.exception("HTTP error during scraping")
                raise HTTPException(
                    status_code=502,
                    detail={
                        "error": "scraping_failed",
                        "message": f"Error scraping URLs: {str(e)}",
                    },
                )
        except Exception as e:
            logger.exception("Unexpected error during scraping")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "internal_error",
                    "message": f"Unexpected error: {str(e)}",
                },
            )

    # Return single result directly if input was single URL
    if isinstance(request.urls, str):
        return results_data[0] if results_data else None

    # Return batch response format for multiple URLs
    return {
        "success": True,
        "status": "completed",
        "total": len(urls_to_process),
        "completed": len(results_data),
        "data": results_data,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)
