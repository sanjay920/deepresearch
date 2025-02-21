import requests


def scrape_urls_call(urls, use_cache=True):
    """
    Calls the Firecrawl service by making a POST request to:
      http://localhost:8084/batch_scrape_urls

    Parameters:
    - urls: List of URLs to scrape
    - use_cache: When True, uses cached results if available. When False, forces fresh fetches.
    """
    api_url = "http://localhost:8084/batch_scrape_urls"
    payload = {
        "urls": urls,
        "formats": ["markdown"],
        "force_fetch": not use_cache,  # When use_cache is True, we do not force fetch
    }

    print(payload)

    response = requests.post(api_url, json=payload)
    response.raise_for_status()
    return response.json()
