import logging
from typing import List, Dict, Any
from tools.google_search import google_search_call
from tools.scrape_urls import scrape_urls_call


class RetrievalAgent:
    """Agent responsible for retrieving information from external sources."""

    def __init__(self):
        self.cache: Dict[str, Any] = {}

    def search(self, query: str) -> List[Dict[str, str]]:
        """Perform a web search using the Google Custom Search API."""
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
            raise

    def retrieve_webpage(self, url: str) -> str:
        """Retrieve the content of a webpage using Firecrawl."""
        if url in self.cache:
            logging.debug(f"Cache hit for URL: {url}")
            return self.cache[url]

        try:
            response = scrape_urls_call([url], use_cache=True)
            if response and len(response) > 0:
                content = response[0].get("markdown", "")
                if content:
                    self.cache[url] = content
                    logging.info(f"Retrieved webpage content from: {url}")
                    return content
                else:
                    raise Exception("No markdown content found")
            else:
                raise Exception("No content retrieved from Firecrawl")
        except Exception as e:
            logging.error(f"Webpage retrieval failed for URL '{url}': {e}")
            raise
