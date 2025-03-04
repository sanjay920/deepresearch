# Gemini Webpage Researcher Microservice

This microservice leverages the Gemini model via Vertex AI to analyze webpage content and answer user queries based on the provided URL. It performs the following steps:

1. **Scrape the Webpage:** The service makes a synchronous HTTP request to retrieve the webpage content.
2. **Leverage Gemini via Vertex AI:** The scraped content and the user's query are sent to Gemini with a comprehensive system instruction tailored for webpage research.
3. **Return the Answer:** The Gemini model returns a markdown-formatted answer which is then provided as the service response.

## Features

- **Input:** A JSON payload with:
  - `query`: The question or task (e.g. "find the section that describes the product features").
  - `url`: The webpage URL to search.
- **Processing:**
  - Scrapes the content of the URL.
  - Calls Gemini via Vertex AI with the webpage content and query.
  - Takes advantage of Gemini's 2 million token context window.
- **Output:** A comprehensive markdown-formatted answer or structured JSON data.

## Environment Variables

- `SERVICE_ACCOUNT_FILE`: Path to your Google Cloud service account JSON file.
- `GCP_PROJECT_ID`: Your Google Cloud Project ID.
- `GCP_LOCATION`: Google Cloud region (default: us-central1).

Use the provided `.env.sample` file as a template.

## Running Locally

1. **Create a virtual environment & install dependencies:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set the environment variables:**

   ```bash
   export SERVICE_ACCOUNT_FILE="path/to/your-service-account.json"
   export GCP_PROJECT_ID="your-project-id"
   export GCP_LOCATION="us-central1"
   ```

3. **Run the service:**

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8085
   ```

   The service will be available at [http://localhost:8085/research](http://localhost:8085/research) and [http://localhost:8085/research_structured](http://localhost:8085/research_structured).

## Docker

1. **Build the Docker image:**

   ```bash
   docker build -t gemini-webpage-researcher .
   ```

2. **Run the Docker container:**

   ```bash
   docker run -d --name gemini-webpage-researcher -p 8090:80 \
     -e SERVICE_ACCOUNT_FILE="/app/service-account.json" \
     -e GCP_PROJECT_ID="your-project-id" \
     -e GCP_LOCATION="us-central1" \
     -v /path/to/your/service-account.json:/app/service-account.json \
     gemini-webpage-researcher
   ```

   The service will be accessible at [http://localhost:8085/research](http://localhost:8085/research) and [http://localhost:8085/research_structured](http://localhost:8085/research_structured).

## API Endpoints

### 1. `/research` (POST)

Extract information from a webpage based on a query.

**Request Body:**

```json
{
  "query": "What are the key features of the product?",
  "url": "https://example.com/product-page"
}
```

**Response:**

```json
{
  "answer": "# Product Features\n\n## Key Features\n- Feature 1: Description...",
  "correlation_id": "uuid-string",
  "url": "https://example.com/product-page",
  "query": "What are the key features of the product?"
}
```

### 2. `/research_structured` (POST)

Extract structured data from a webpage based on a query.

**Request Body:**

```json
{
  "query": "Extract the product specifications",
  "url": "https://example.com/product-page"
}
```

**Response:**

```json
{
  "structured_data": {
    "answer": "Product specifications extracted",
    "extracted_data": ["Spec 1: Value", "Spec 2: Value"],
    "confidence": 0.95
  },
  "correlation_id": "uuid-string",
  "url": "https://example.com/product-page",
  "query": "Extract the product specifications"
}
```

## Key Features

1. **Vertex AI Integration**: Uses Google Cloud's Vertex AI to access Gemini models.

2. **Massive Context Window**: Takes advantage of Gemini 2.0's 2 million token context window, allowing for analysis of very large webpages.

3. **Intelligent Token Management**: Counts tokens accurately and only truncates content when absolutely necessary.

4. **Comprehensive Responses**: Generates detailed, well-structured answers with proper formatting, headings, and relevant links.
