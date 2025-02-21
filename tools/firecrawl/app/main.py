import os
import logging
from typing import List, Optional

import requests
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from firecrawl import FirecrawlApp
from . import cache  # our caching module

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
    force_fetch: bool = False  # Bypass cache if true


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
    Scrape a single URL using Firecrawl and return the converted result.
    Uses a cache when not forcing a fresh fetch.
    """
    try:
        if not force_fetch:
            # Try reading from cache
            cached = cache.get_cached_result(url, formats)
            if cached is not None:
                logger.info(f"Cache hit for URL: {url}, formats={formats}")
                return cached

        # Fetch fresh results from Firecrawl
        logger.info(f"Scraping fresh content for URL: {url}, formats={formats}")
        try:
            result = firecrawl_client.scrape_url(url=url, params={"formats": formats})
            # Store result in cache
            cache.store_result(url, formats, result)
            return result
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Firecrawl API key authentication failed")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "authentication_failed",
                        "message": "Firecrawl authentication failed. Please check API key configuration.",
                    },
                )
            else:
                logger.exception(f"HTTP error during scraping: {str(e)}")
                raise HTTPException(
                    status_code=502,
                    detail={
                        "error": "scraping_failed",
                        "message": f"Error scraping URL: {str(e)}",
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
    except Exception as e:
        logger.exception("Error in scrape endpoint")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Internal server error: {str(e)}",
            },
        )


@app.post("/batch_scrape_urls", summary="Batch scrape multiple URLs")
def batch_scrape(request: BatchScrapeRequest):
    """
    Batch scrape multiple URLs using Firecrawl.
    Automatically filters out unsupported URLs and continues with supported ones.
    """
    try:
        if not request.force_fetch:
            # Handle cached results as before...
            all_cached = True
            results_data = []
            urls_to_fetch = []
            for url in request.urls:
                cached = cache.get_cached_result(url, request.formats or ["markdown"])
                if cached is not None:
                    results_data.append(cached)
                else:
                    all_cached = False
                    urls_to_fetch.append(url)

            if urls_to_fetch:
                try:
                    batch_result = firecrawl_client.batch_scrape_urls(
                        urls_to_fetch, {"formats": request.formats}
                    )
                    if batch_result.get("data"):
                        for idx, url in enumerate(urls_to_fetch):
                            cache.store_result(
                                url, request.formats, batch_result["data"][idx]
                            )
                            results_data.append(batch_result["data"][idx])
                    return {
                        "success": True,
                        "status": "completed",
                        "total": len(request.urls),
                        "completed": len(results_data),
                        "data": results_data,
                    }
                except requests.exceptions.HTTPError as e:
                    # If we get an error for unsupported URLs, return what we have from cache
                    if hasattr(e, "response") and e.response.status_code == 400:
                        return {
                            "success": True,
                            "status": "partial",
                            "total": len(request.urls),
                            "completed": len(results_data),
                            "data": results_data,
                            "warning": "Some URLs could not be fetched as they are not supported",
                            "skipped_urls": urls_to_fetch,
                        }
                    raise
            else:
                # All results were cached
                return {
                    "success": True,
                    "status": "completed",
                    "total": len(request.urls),
                    "completed": len(results_data),
                    "data": results_data,
                }
        else:
            logger.info("Batch scraping with force_fetch=True (bypassing cache).")

            def get_supported_urls(urls, error_response):
                """Helper function to filter supported URLs based on error response"""
                unsupported_indices = set()
                if isinstance(error_response, list):
                    for error in error_response:
                        if (
                            "path" in error
                            and isinstance(error["path"], list)
                            and len(error["path"]) >= 2
                        ):
                            try:
                                unsupported_indices.add(int(error["path"][1]))
                            except (ValueError, TypeError):
                                continue

                supported_urls = []
                unsupported_urls = []
                for idx, url in enumerate(urls):
                    if idx in unsupported_indices:
                        unsupported_urls.append(url)
                    else:
                        supported_urls.append(url)

                return supported_urls, unsupported_urls

            try:
                # First attempt with all URLs
                batch_result = firecrawl_client.batch_scrape_urls(
                    request.urls, {"formats": request.formats}
                )
                return batch_result

            except requests.exceptions.HTTPError as e:
                if not hasattr(e, "response") or e.response.status_code != 400:
                    return {
                        "success": True,
                        "status": "error",
                        "total": len(request.urls),
                        "completed": 0,
                        "data": [],
                        "warning": f"Error during batch scrape: {str(e)}",
                        "skipped_urls": request.urls,
                    }

                try:
                    error_response = e.response.json()
                    supported_urls, unsupported_urls = get_supported_urls(
                        request.urls, error_response
                    )

                    logger.info(
                        f"Found {len(unsupported_urls)} unsupported URLs: {unsupported_urls}"
                    )
                    logger.info(
                        f"Retrying with {len(supported_urls)} supported URLs: {supported_urls}"
                    )

                    if not supported_urls:
                        return {
                            "success": True,
                            "status": "completed",
                            "total": len(request.urls),
                            "completed": 0,
                            "data": [],
                            "warning": "No supported URLs to process",
                            "skipped_urls": unsupported_urls,
                        }

                    # Retry with only supported URLs
                    batch_result = firecrawl_client.batch_scrape_urls(
                        supported_urls, {"formats": request.formats}
                    )

                    # If we get here, the retry was successful
                    return {
                        **batch_result,
                        "warning": "Some URLs were skipped as they are not supported",
                        "skipped_urls": unsupported_urls,
                    }

                except requests.exceptions.HTTPError as retry_error:
                    # If we get another 400 error, we need to filter again
                    if (
                        hasattr(retry_error, "response")
                        and retry_error.response.status_code == 400
                    ):
                        try:
                            retry_error_response = retry_error.response.json()
                            remaining_supported, newly_unsupported = get_supported_urls(
                                supported_urls, retry_error_response
                            )

                            if remaining_supported:
                                final_result = firecrawl_client.batch_scrape_urls(
                                    remaining_supported, {"formats": request.formats}
                                )
                                return {
                                    **final_result,
                                    "warning": "Some URLs were skipped as they are not supported",
                                    "skipped_urls": unsupported_urls
                                    + newly_unsupported,
                                }

                        except Exception:
                            pass

                    return {
                        "success": True,
                        "status": "error",
                        "total": len(request.urls),
                        "completed": 0,
                        "data": [],
                        "warning": f"Error processing supported URLs: {str(retry_error)}",
                        "skipped_urls": request.urls,
                    }

                except Exception as e:
                    logger.exception("Error processing URLs")
                    return {
                        "success": True,
                        "status": "error",
                        "total": len(request.urls),
                        "completed": 0,
                        "data": [],
                        "warning": f"Error processing URLs: {str(e)}",
                        "skipped_urls": request.urls,
                    }

    except Exception as e:
        logger.exception("Error batch scraping URLs")
        return {
            "success": True,
            "status": "error",
            "total": len(request.urls),
            "completed": 0,
            "data": [],
            "warning": f"Unexpected error: {str(e)}",
            "skipped_urls": request.urls,
        }
