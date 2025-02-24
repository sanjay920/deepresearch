import logging
from typing import List, Dict, Any
from tools.google_search import google_search_call
from tools.scrape_urls import scrape_urls_call


class RetrievalAgent:
    """Agent responsible for retrieving information from external sources."""

    def __init__(self):
        self.cache: Dict[str, Any] = {}

    def search(self, query: str) -> List[Dict[str, str]]:
        """
        Perform a web search using the Google Custom Search API.
        If it fails, return an empty list or a special note instead of raising an exception.
        """
        if query in self.cache:
            logging.debug(f"Cache hit for search query: {query}")
            return self.cache[query]

        try:
            results = google_search_call(query)
            self.cache[query] = results
            logging.info(f"Retrieved search results for query: {query}")
            return results
        except Exception as e:
            logging.error(f"Search failed for query '{query}': {e}")
            error_result = [
                {
                    "title": "[Error]",
                    "link": "",
                    "snippet": f"No data found for '{query}' due to error: {str(e)}",
                }
            ]
            self.cache[query] = error_result
            return error_result

    def retrieve_webpage(self, url: str) -> str:
        """
        Retrieve the content of a single webpage using Firecrawl.
        Uses cache if available. If it fails or returns no data, returns a placeholder string.
        """
        if url in self.cache:
            logging.debug(f"Cache hit for URL: {url}")
            return self.cache[url]

        try:
            response = scrape_urls_call([url], use_cache=True)
            if response and "data" in response and len(response["data"]) > 0:
                content = response["data"][0].get("markdown", "")
                if not content:
                    content = f"[No data found from {url}]"
                    logging.warning(
                        f"No markdown content found at {url}. Using placeholder."
                    )
            else:
                content = f"[No content retrieved from {url}]"
                logging.warning(f"Empty response from Firecrawl for {url}.")

            self.cache[url] = content
            logging.info(f"Retrieved webpage content from: {url}")
            return content

        except Exception as e:
            logging.error(f"Webpage retrieval failed for URL '{url}': {e}")
            content = f"[Error retrieving {url}: {str(e)}]"
            self.cache[url] = content
            return content

    def retrieve_webpages(self, urls: List[str]) -> List[str]:
        """
        Retrieve the content of multiple webpages in a single batch call.
        Returns a list of markdown strings in the same order as the input URLs.
        Uses cache if possible for any URLs already retrieved.
        """
        to_fetch = [u for u in urls if u not in self.cache]

        if to_fetch:
            try:
                response = scrape_urls_call(to_fetch, use_cache=True)
                if (
                    response
                    and "data" in response
                    and len(response["data"]) == len(to_fetch)
                ):
                    for i, url in enumerate(to_fetch):
                        content = response["data"][i].get("markdown", "")
                        if not content:
                            content = f"[No data found from {url}]"
                            logging.warning(
                                f"No markdown content found at {url}. Using placeholder."
                            )
                        self.cache[url] = content
                else:
                    logging.warning(
                        "Batch scrape response length mismatch or empty response."
                    )
                    for url in to_fetch:
                        self.cache[url] = f"[No content retrieved from {url}]"
            except Exception as e:
                logging.error(f"Batch webpages retrieval failed: {e}")
                for url in to_fetch:
                    self.cache[url] = f"[Error retrieving {url}: {str(e)}]"

        results = []
        for url in urls:
            if url in self.cache:
                results.append(self.cache[url])
            else:
                results.append(f"[No content retrieved from {url}]")

        return results
