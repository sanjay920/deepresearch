# Google Custom Search API Service

This service is a production-ready API wrapper around Google Custom Search. It exposes a `/search` endpoint that accepts a search query and returns a filtered JSON response—removing unnecessary metadata and formatting fields—so that downstream LLMs can more easily determine if the answer is contained in the snippet or the pagemap.

## Features

- **Custom Filtering:** Removes HTML formatted fields, technical metadata (e.g., `kind`, `cacheId`, `queries`, `searchInformation`, `context`, `formattedUrl`, `url`, `metatags`), and strips out the `width` and `height` attributes from `cse_thumbnail` entries.
- **FastAPI Powered:** Uses FastAPI for a high-performance, production-ready API.
- **Dockerized:** Containerized for easy deployment.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your machine.
- A valid **Google API Key** and **Custom Search Engine (CSE) ID**. These should be set as environment variables:
  - `GOOGLE_API_KEY`
  - `GOOGLE_CSE_ID`

## Building the Docker Image

   ```bash
   docker build -t google-search-api .
   ```

## Running the Service

Run the container while passing in your Google API credentials:

```bash
docker run -d --name google-search-api -p 8085:80 \
  -e GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY" \
  -e GOOGLE_CSE_ID="YOUR_GOOGLE_CSE_ID" \
  google-search-api
```

The service will be accessible at [http://localhost/](http://localhost/).

## Using the API

The API exposes a single endpoint:

### `GET /search`

**Query Parameters:**

- `q` (required): The search query string.

**Example Request:**

```bash
curl "http://localhost/search?q=nba+scores"
```

**Example Response:**

```json
{
  "items": [
    {
      "title": "NBA Scores, 2024-25 Season - ESPN",
      "link": "https://www.espn.com/nba/scoreboard",
      "displayLink": "www.espn.com",
      "snippet": "Live scores for every 2024-25 NBA season game on ESPN. Includes box scores ... Tuesday, February 4, 2025. Mavericks. 26-24. 76ers. 19-29. 4:00 PM. ESPN Bet.",
      "pagemap": {
        "cse_thumbnail": [
          {
            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSCLDJunBPBenMfKodlIioYo-9nP3J1e7qD9ciwbmtvKTr46Q3DT_4gOWM&s"
          }
        ],
        "cse_image": [
          {
            "src": "https://a.espncdn.com/i/teamlogos/leagues/500/nba.png"
          }
        ]
      }
    }
    // ... additional items
  ]
}
```

Only the essential fields (`title`, `snippet`, `link`, `displayLink`, and filtered `pagemap`) are returned.

## Local Development

If you prefer to run the service without Docker, follow these steps:

1. **Create a Virtual Environment & Install Dependencies:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set Environment Variables:**

   ```bash
   export GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
   export GOOGLE_CSE_ID="YOUR_GOOGLE_CSE_ID"
   ```

3. **Run the Service Using Uvicorn:**

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8085
   ```

   The service will be available at [http://localhost:8085/](http://localhost:8085/).
