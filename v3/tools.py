import requests
import logging
import json
from typing import Dict, Any


def google_search(q: str) -> Dict[str, Any]:
    """
    Performs a Google search via local microservice.

    Args:
        q: The search query string

    Returns:
        Dict containing search results or error
    """
    try:
        response = requests.get("http://localhost:8085/search", params={"q": q})
        response.raise_for_status()
        result = response.json()
        logging.info(
            f"Search for '{q}' returned {len(result.get('items', []))} results"
        )
        return result
    except Exception as e:
        logging.error(f"Search error: {e}")
        return {"error": str(e), "items": []}


def web_research(url: str, query: str) -> Dict[str, Any]:
    """
    Research a specific webpage to answer a question.
    Uses the web research microservice to do targeted extraction.

    Args:
        url: The URL to research
        query: The specific question to answer

    Returns:
        Dict containing the research result or error
    """
    try:
        response = requests.post(
            "http://localhost:8090/research", json={"url": url, "query": query}
        )
        response.raise_for_status()
        result = response.json()
        logging.info(f"Web research for '{query}' on {url} completed")
        return result
    except Exception as e:
        logging.error(f"Web research error: {e}")
        return {"error": str(e), "answer": f"Failed to research {url}: {str(e)}"}
