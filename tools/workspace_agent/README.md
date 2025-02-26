# Document Workspace Agent

A microservice that manages a workspace of markdown documents. It provides a natural language interface for creating, editing, and managing documents.

## Features

- Natural language interface for document operations
- Create and manage markdown documents
- Add, replace, remove, and rename sections
- Export documents to different formats (simulated)
- List documents and get workspace summaries

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | (required) |
| `WORKSPACE_DIR` | Directory to store workspace documents | `./workspace` |

## Running Locally

1. Clone the repository
2. Create a `.env` file based on `.env.sample`
3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Run the service:

   ```
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Running with Docker

1. Build the Docker image:

   ```
   docker build -t document-workspace-agent .
   ```

2. Run the container:

   ```
   docker run -p 8091:8000 \
     -e ANTHROPIC_API_KEY=your_api_key \
     -v /path/to/local/workspace:/app/workspace \
     document-workspace-agent
   ```

## API Endpoints

### Process a Natural Language Query
