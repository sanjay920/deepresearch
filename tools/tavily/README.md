# Tavily Microservice

A microservice API wrapper around Tavily Extract. It scrapes URLs and converts the content into markdown.

## Features

- URL content extraction using Tavily API
- Markdown conversion of extracted content
- Caching support for improved performance
- Support for single or batch URL processing

## Docker Setup

### Building the Image

```bash
docker build -t tavily-microservice .
```

### Running the Container

```bash
docker run -d \
  --name tavily-microservice \
  -p 8089:80 \
  -e TAVILY_API_KEY="your-api-key" \
  tavily-microservice
```

Replace `your-api-key` with your actual Tavily API key.

The service will be available at `http://localhost:8089`.
