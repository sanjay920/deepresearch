# Webpage Researcher Microservice

This microservice leverages the GPT‑4o model to analyze webpage content and answer user queries based on the provided URL. It performs the following steps:

1. **Scrape the Webpage:** The service makes a synchronous HTTP request to retrieve the webpage content.
2. **Leverage GPT‑4o:** The scraped content and the user's query are sent to GPT‑4o (via the latest OpenAI SDK) with a developer instruction tailored for webpage research.
3. **Return the Answer:** The GPT‑4o model returns a markdown-formatted answer which is then provided as the service response.

## Features

- **Input:** A JSON payload with:
  - `query`: The question or task (e.g. "find the section that describes the product features").
  - `url`: The webpage URL to search.
- **Processing:**
  - Scrapes the content of the URL.
  - Calls GPT‑4o with the webpage content and query.
- **Output:** A markdown-formatted answer.

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key.

Use the provided `.env.sample` file as a template.

## Running Locally

1. **Create a virtual environment & install dependencies:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set the environment variable:**

   ```bash
   export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
   ```

3. **Run the service:**

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8004
   ```

   The service will be available at [http://localhost:8004/research](http://localhost:8004/research).

## Docker

1. **Build the Docker image:**

   ```bash
   docker build -t webpage-researcher .
   ```

2. **Run the Docker container:**

   ```bash
   docker run -d --name webpage-researcher -p 8087:80 -e OPENAI_API_KEY="YOUR_OPENAI_API_KEY" webpage-researcher
   ```

   The service will be accessible at [http://localhost:8087/research](http://localhost:8087/research).
