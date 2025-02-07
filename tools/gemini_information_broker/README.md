# Gemini Microservice

This service is a FastAPI-based microservice that wraps the Gemini API. It accepts a prompt, calls the Gemini API to generate content, formats the returned text with inline citations (if grounding data is available), and returns the result.

## Features

- **Prompt Generation:** Send a prompt to the Gemini API and receive generated text.
- **Citation Formatting:** Inline citations and a sources list are added if grounding metadata is provided.
- **Dockerized:** Ready for containerized deployment.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your machine.
- A valid **Gemini API Key**. Set the API key as an environment variable:
  - `GEMINI_API_KEY`

## Environment Variables

Create a copy of the provided `.env.sample` and update the API key:

```bash
cp .env.sample .env
```

Then edit `.env` to set your `GEMINI_API_KEY`.

## Building the Docker Image

From the project directory, run:

```bash
docker build -t gemini-information-broker .
```

## Running the Service

Run the container while passing in your Gemini API credentials. For example, to run the container and map the container’s port 80 to your host’s port 8080:

```bash
docker run -d --name gemini-information-broker -p 8081:80 \
  -e GEMINI_API_KEY="YOUR_GEMINI_API_KEY" \
  gemini-information-broker
```

The service will be available at [http://localhost:8081/](http://localhost:8081/).

## API Endpoint

### `POST /generate`

**Request Body:**

```json
{
  "prompt": "Your prompt or question here"
}
```

**Example Request using curl:**

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain how the Gemini API works."}'
```

**Example Response:**

```json
{
  "response": "The Gemini API works by ... [1]\n\nSources:\n1. [Example Source](https://example.com)"
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
   export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
   ```

3. **Run the Service Using Uvicorn:**

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8081
   ```

   The service will be available at [http://localhost:8081/](http://localhost:8081/).

## Troubleshooting

- **Missing GEMINI_API_KEY:**  
  Ensure the `GEMINI_API_KEY` environment variable is set.

- **Port Conflicts:**  
  If you encounter port conflicts, change the host port when running the container (e.g., `-p 8080:80`).
