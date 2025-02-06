# Firecrawl Microservice

This service is a production-ready API wrapper around the Firecrawl service. It allows you to convert entire websites into LLM-ready markdown by exposing two endpoints:

- **GET /scrape**: Scrape a single URL.
- **POST /batch_scrape_urls**: Batch scrape multiple URLs.

## Features

- **Single & Batch Scraping:** Scrape one URL or multiple URLs at once.
- **Caching (New):** Uses a lightweight SQLite cache to avoid redundant scrapes and save Firecrawl credits.
- **FastAPI Powered:** Uses FastAPI for a high-performance API.
- **Dockerized:** Containerized for easy deployment.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your machine.
- A valid **Firecrawl API Key**. Set the API key as an environment variable:
  - `FIRECRAWL_API_KEY`

## Building the Docker Image

Run the following command in the project directory:

```bash
docker build -t firecrawl-microservice .
```

## Running the Service

You can run the container while passing in your Firecrawl API credentials. For example, to run the container and map the container’s port 80 to your host’s port 8080, run:

```bash
docker run -d --name firecrawl-microservice -p 8080:80 \
  -e FIRECRAWL_API_KEY="YOUR_FIRECRAWL_API_KEY" \
  firecrawl-microservice
```

This configuration makes the service accessible at [http://localhost:8080/](http://localhost:8080/).  
> **Note:** If you choose to map container port 80 to host port 80 (i.e. using `-p 80:80`), update your requests accordingly (e.g. `http://localhost/scrape?...`).

## Caching

This microservice uses a local [SQLite](https://www.sqlite.org/index.html) database (stored at `app/cache.db`) to cache scraped results:

- When you request a URL, the service looks up any previous result in the cache. If it exists, it returns the cached data instead of making a fresh request to Firecrawl.
- To force a fresh scrape from Firecrawl (ignoring the cache), set the `force_fetch` parameter to `true` on the relevant endpoint (see below).
- The cache uses `(url, formats)` as its unique key. If you request the same URL with different output formats, it is treated as a separate cache entry.

If you want to clear the cache entirely, stop the service and remove the `app/cache.db` file.

## API Endpoints

### `GET /scrape`

Scrapes a single URL.

**Query Parameters:**

- `url` (**required**): The URL to scrape.
- `formats` (**optional**): A list of output formats (default: `["markdown"]`).
- `force_fetch` (**optional**): If `true`, ignore cache and fetch fresh data from Firecrawl (default: `false`).

**Example Request:**

```bash
curl "http://localhost:8080/scrape?url=https://openai.com/index/&formats=markdown&force_fetch=true"
```

**Example Response:**

```json
{
  "markdown": "![...](...)\n\nYour scraped content in markdown..."
}
```

### `POST /batch_scrape_urls`

Scrapes multiple URLs in one request.

**Request Body:**

```json
{
  "urls": [
    "https://www.example.com/page1",
    "https://www.example.com/page2"
  ],
  "formats": ["markdown"],
  "force_fetch": false
}
```

**Behavior with `force_fetch`:**

- If `force_fetch = false`, the service will return cached results for any URLs already stored and only scrape new data for the ones not in the cache.
- If `force_fetch = true`, the service will ignore the cache for **all** URLs and fetch fresh data from Firecrawl.

**Example Response:**

```json
{
  "success": true,
  "status": "completed",
  "data": [
    {"markdown": "Scraped markdown for page1..."},
    {"markdown": "Scraped markdown for page2..."}
  ]
}
```

## Local Development

If you prefer running the service locally without Docker:

1. **Create a Virtual Environment & Install Dependencies:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set Environment Variables:**

   ```bash
   export FIRECRAWL_API_KEY="YOUR_FIRECRAWL_API_KEY"
   ```

3. **Run the Service Using Uvicorn:**

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The service will be available at [http://localhost:8000/](http://localhost:8000/).

## Troubleshooting

- **Port Conflicts:**  
  If you receive an error such as "port is already allocated," try mapping to a different host port (for example, using `-p 8080:80`).
- **Clearing Cache:**  
  If you suspect the cache is stale or you want to reset it, stop the service and remove `app/cache.db`.
- **Environment Variables:**  
  Ensure `FIRECRAWL_API_KEY` is set correctly before running.
