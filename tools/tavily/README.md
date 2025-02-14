# Tavily Microservice

This microservice is an API wrapper around the Tavily Extract API. It scrapes one or more URLs, converts the raw extracted content into markdown format, and caches the results in a local SQLite database.

## Features

- **Single & Batch Scraping:** Endpoints for scraping one URL (`GET /scrape`) or multiple URLs (`POST /batch_scrape_urls`).
- **Caching:** Uses a lightweight SQLite cache to avoid redundant API calls.
- **Markdown Conversion:** Converts raw HTML from Tavily into LLM-ready markdown using html2text.
- **Dockerized:** Easily deployable via Docker.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed.
- A valid **Tavily API Key**. Set this in the environment variable `TAVILY_API_KEY`.

## Getting Started

1. **Build the Docker Image:**

   ```bash
   docker build -t tavily-microservice .
   ```

2. **Run the Container:**
   ```bash
   # Run with environment variable
   docker run -d \
     --name tavily-microservice \
     -p 8089:80 \
     -e TAVILY_API_KEY="YOUR_TAVILY_API_KEY" \
     tavily-microservice

   # Or run with env file
   docker run -d \
     --name tavily-microservice \
     -p 8089:80 \
     --env-file ./.env \
     tavily-microservice
   ```

   The service will be available at [http://localhost:8089/](http://localhost:8089/).

## API Endpoints

### GET /scrape

Scrape a single URL.

**Query Parameters:**

- `url` (required): The URL to scrape.
- `include_images` (optional, default=`false`): Whether to include images.
- `extract_depth` (optional, default=`basic`): Extraction depth (`basic` or `advanced`).
- `force_fetch` (optional, default=`false`): If `true`, bypasses caching.

**Example Request:**

```bash
curl "http://localhost:8089/scrape?url=https://openai.com/&extract_depth=basic&include_images=false&force_fetch=true"
```

### POST /batch_scrape_urls

Scrape multiple URLs.

**Request Body:**

```json
{
  "urls": [
    "https://www.example.com/page1",
    "https://www.example.com/page2"
  ],
  "include_images": false,
  "extract_depth": "basic",
  "force_fetch": false
}
```

**Example Response:**

```json
{
  "success": true,
  "status": "completed",
  "data": [
    {"url": "https://www.example.com/page1", "markdown": "Converted markdown..."},
    {"url": "https://www.example.com/page2", "markdown": "Converted markdown..."}
  ]
}
```
