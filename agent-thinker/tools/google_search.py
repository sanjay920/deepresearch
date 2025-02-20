import requests


def google_search_call(q):
    """
    Calls the Google Custom Search API microservice at:
      http://localhost:8085/search

    It sends the search query 'q' as a GET parameter and returns the filtered JSON response.
    """
    api_url = "http://localhost:8085/search"
    params = {"q": q}
    response = requests.get(api_url, params=params)
    response.raise_for_status()
    return response.json()
