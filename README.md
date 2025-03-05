# Deep Research

```mermaid
sequenceDiagram
    participant U as User
    participant CLI as cli.py
    participant Convo as conversation.py
    participant LLM as llm_client.py
    participant TD as tool_dispatcher.py
    participant O as orchestrator.py
    participant R as retrieval.py
    participant G as google_search.py
    participant SU as scrape_urls.py
    participant SP as switch_personas.py
    participant S as synthesis.py
    participant V as validation.py

    U->>CLI: "Create a 50-page research report on AI agent platforms..."
    CLI->>Convo: Store user message in conversation
    CLI->>LLM: Send conversation to LLM
    Note over LLM: LLM decides to plan a complex multi-step task
    LLM->>TD: Tool call: switch_personas(switch_to="thinker")
    TD->>SP: switch_personas_call("thinker", conversation)
    SP->>Convo: Retrieve conversation history
    SP-->>TD: Returns JSON plan with steps (e.g., google_search, scrape_urls)
    TD-->>LLM: Plan forwarded to LLM
    LLM->>CLI: Assistant message with tool call result
    CLI->>Convo: Store assistant message with plan

    Note over CLI: CLI processes thinker's plan steps
    CLI->>O: Add retrieval tasks from plan (e.g., google_search "AI agent platforms 2025")
    O->>R: Calls RetrievalAgent.search(query)
    R->>G: google_search_call(query)
    G-->>R: JSON search results
    R-->>O: Return search results
    CLI->>O: Add retrieval tasks (e.g., scrape_urls for Gartner pages)
    O->>R: Calls RetrievalAgent.retrieve_webpages(urls)
    R->>SU: scrape_urls_call(urls)
    SU-->>R: Markdown content
    R-->>O: Return scraped content

    Note over O: Orchestrator queues synthesis after retrievals
    O->>S: Calls SynthesisAgent.synthesize(query, retrieval_results)
    S->>LLM: Request summary generation
    LLM-->>S: JSON with status, summary, and possibly additional_tasks
    Note over S: If incomplete, suggest more retrievals
    S-->>O: Return synthesis result (e.g., incomplete with new tasks)
    O->>R: Add new retrieval tasks (e.g., scrape blogs, tweets)
    R->>SU: scrape_urls_call(new_urls)
    SU-->>R: New content
    R-->>O: Return new data

    Note over O: Second synthesis iteration
    O->>S: Synthesize again with all data
    S->>LLM: Generate final 50-page report summary
    LLM-->>S: JSON with status="complete", Markdown summary
    S-->>O: Return complete synthesis

    O->>V: Calls ValidationAgent.validate(summary)
    V->>LLM: Verify citations in summary
    LLM-->>V: Validation report
    V-->>O: Return validation result

    O-->>CLI: Final validated summary
    CLI->>U: Display 50-page report in Markdown
```

## Microservices

Deep Research uses several microservices to handle different aspects of the research process:

1. **Workspace Agent**: Manages markdown documents and provides a natural language interface for document operations.
2. **Google Search**: Wrapper around Google Custom Search API for retrieving search results.
3. **Firecrawl**: Converts websites into LLM-ready markdown for analysis.
4. **Website Researcher**: Uses Google's Gemini model to analyze webpage content and answer queries.

## Docker Compose Setup

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed
- API keys for the following services:
  - Anthropic Claude API
  - Google API (with Custom Search enabled)
  - Firecrawl API
  - Google Cloud Platform (with Vertex AI enabled)

### Configuration

The `docker-compose.yml` file has placeholder values that need to be replaced:

- `<YOUR_ANTHROPIC_API_KEY>`: Your Anthropic API key
- `<YOUR_GOOGLE_API_KEY>`: Your Google API key
- `<YOUR_GOOGLE_CSE_ID>`: Your Google Custom Search Engine ID
- `<YOUR_FIRECRAWL_API_KEY>`: Your Firecrawl API key
- `<YOUR_GCP_PROJECT_ID>`: Your Google Cloud Platform project ID

Also update the volume paths to match your local environment:

- `/path/to/your/workspace`: Local path to store workspace documents
- `/path/to/your/service-account.json`: Path to your GCP service account JSON file

### Building and Running

To build and start all services:

```bash
docker-compose up -d
```

This command will:

1. Build Docker images for all services if they don't exist
2. Create and start containers for each service
3. Run them in detached mode (-d flag)

### Managing Services

- **View logs for all services**:

  ```bash
  docker-compose logs -f
  ```

- **View logs for a specific service**:

  ```bash
  docker-compose logs -f workspace-agent
  ```

- **Stop all services**:

  ```bash
  docker-compose down
  ```

- **Rebuild a specific service after code changes**:

  ```bash
  docker-compose up -d --build workspace-agent
  ```

- **Restart a specific service**:

  ```bash
  docker-compose restart google-search
  ```

### Service Endpoints

Once running, the services will be available at:

- Workspace Agent: <http://localhost:8091>
- Google Search: <http://localhost:8085>
- Firecrawl (for scraping): <http://localhost:8084>
- Website Researcher: <http://localhost:8090>

## Getting Started with the CLI

### Prerequisites

Before running the CLI, make sure you have the following:

- Python 3.8+ installed
- API keys for the required services:
  - Anthropic Claude API
  - Google API (with Custom Search enabled)
  - Firecrawl API
  - Google Cloud Platform (with Vertex AI enabled)

### Installation

1. Clone the repository and navigate to the v3 directory:

   ```bash
   git clone <repository-url>
   cd <repository-name>/v3
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set Anthropic API Key Environment Variable

```bash
export ANTHROPIC_API_KEY="<YOUR_ANTHROPIC_API_KEY>"
```

### Running the CLI

To start a new chat session with the CLI:

```bash
python cli.py
```

#### Command-line Arguments

The CLI supports the following arguments:

- `--chat-id`: Specify a chat ID to continue from a previous session. If omitted, a new chat ID will be generated.

Example to continue an existing chat:

```bash
python cli.py --chat-id abc123de
```

#### CLI Commands

Once the CLI is running, you can use the following commands:

- `exit` or `quit`: Exit the application
- `thinking:on`: Show Claude's thinking process
- `thinking:off`: Hide Claude's thinking process
- `clear`: Clear the conversation history
