import requests


class TavilyClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.tavily.com/extract"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def extract(
        self, urls, include_images: bool = False, extract_depth: str = "basic"
    ) -> dict:
        """
        Call the Tavily Extract endpoint.
        Accepts a single URL (as a string) or a list of URLs.
        """
        payload = {
            "urls": urls,
            "include_images": include_images,
            "extract_depth": extract_depth,
        }
        response = requests.post(self.url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
