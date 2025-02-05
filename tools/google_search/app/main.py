import os
import logging
from fastapi import FastAPI, HTTPException, Query
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Google Custom Search API",
    description=(
        "A production-ready API wrapper around Google Custom Search that "
        "filters out non-essential metadata. Only the fields that help a downstream "
        "LLM decide whether the answer is in the snippet or the pagemap are retained."
    ),
    version="1.0.0",
)

# Retrieve environment variables for API credentials
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
    logger.error("Environment variables GOOGLE_API_KEY and GOOGLE_CSE_ID must be set")
    raise Exception(
        "GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables must be set"
    )

# Build the Google Custom Search service client
try:
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
except Exception as e:
    logger.exception("Failed to build Google Custom Search service")
    raise e

# Define keys to exclude from the final output.
# (Anything that is not needed for a downstream LLM to determine if the answer is in the snippet or pagemap.)
EXCLUDED_KEYS = {
    "kind",
    "cacheId",
    "queries",
    "searchInformation",
    "context",
    "formattedUrl",  # redundant with link
    "url",  # top-level URL metadata (template, etc.)
    "metatags",  # verbose metadata that is not essential
}


def filter_unwanted_fields(data):
    """
    Recursively removes keys that are not useful for downstream LLMs.

    This function removes:
      - Any key that starts with "html" (e.g. htmlTitle, htmlSnippet, htmlFormattedUrl)
      - Any key that appears in EXCLUDED_KEYS.
      - Additionally, for keys named "cse_thumbnail", it removes the "width" and "height" keys.

    The goal is to leave only fields (like title, snippet, link, displayLink, and useful parts of pagemap)
    that can help an LLM decide whether the answer lies in the snippet or in the pagemap.
    """
    if isinstance(data, dict):
        filtered = {}
        for k, v in data.items():
            if k.startswith("html") or k in EXCLUDED_KEYS:
                continue
            if k == "cse_thumbnail" and isinstance(v, list):
                new_thumbnails = []
                for thumb in v:
                    if isinstance(thumb, dict):
                        filtered_thumb = {
                            subk: filter_unwanted_fields(subv)
                            for subk, subv in thumb.items()
                            if subk not in ("width", "height")
                        }
                        new_thumbnails.append(filtered_thumb)
                    else:
                        new_thumbnails.append(filter_unwanted_fields(thumb))
                filtered[k] = new_thumbnails
            else:
                filtered[k] = filter_unwanted_fields(v)
        return filtered
    elif isinstance(data, list):
        return [filter_unwanted_fields(item) for item in data]
    else:
        return data


@app.get("/search", summary="Perform a Google Custom Search")
def search(q: str = Query(..., description="The search query string")):
    """
    Executes a search query using Google Custom Search and returns a filtered result.

    The returned JSON is stripped of any fields that are not useful for a downstream LLM to determine
    whether the answer is contained in the snippet or if additional details in the pagemap should be inspected.

    Specifically, we remove:
      - All keys starting with "html" (e.g. htmlTitle, htmlSnippet, htmlFormattedUrl)
      - Technical and metadata keys (e.g. kind, cacheId, queries, searchInformation, context, formattedUrl, url, metatags)
      - The "width" and "height" keys within any "cse_thumbnail" entries.

    - **q**: The search query string.
    """
    try:
        result = service.cse().list(q=q, cx=GOOGLE_CSE_ID).execute()
    except Exception as e:
        logger.exception("Error executing search query")
        raise HTTPException(status_code=500, detail="Error executing search query")

    filtered_result = filter_unwanted_fields(result)
    return filtered_result
