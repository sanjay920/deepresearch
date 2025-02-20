import requests


def scrape_urls_call(urls, use_cache=True):
    """
    Calls the Tavily Extract service by making a POST request to:
      http://localhost:8089/scrape_urls

    Translates the parameter 'use_cache' into 'force_fetch' expected by the API.
    """
    api_url = "http://localhost:8089/scrape_urls"
    payload = {
        "urls": urls,
        "force_fetch": not use_cache,  # When use_cache is True, we do not force fetch.
    }

    response = requests.post(api_url, json=payload)
    response.raise_for_status()
    # Return the JSON response (which includes the markdown text)
    return response.json()
