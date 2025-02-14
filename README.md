# Deep Research

```mermaid
flowchart TD
    A[User inputs query] --> B[CLI]
    B --> C[Orchestrator Service - port 8080]
    C --> D{Is query complex?}
    D -- No --> E[Call Gemini Service]
    E --> F[Return simple answer]
    D -- Yes --> G[Generate research plan]
    G --> H[Execute plan steps]
    H --> I{Tool needed?}
    I -- Web scraping --> J[Call Firecrawl Service]
    J --> H
    I -- LLM query --> K[Call Gemini Service]
    K --> H
    I -- No --> L[Generate final response]
    L --> M[Return to user]

    %% Service ports
    subgraph Services
        direction LR
        Orchestrator[Orchestrator - :8080]
        Firecrawl[Firecrawl - :8084]
        Gemini[Gemini - :8081]
    end
```

## Quick Start

1. Set environment variables:

```bash
export OPENAI_API_KEY=your_key_here
export FIRECRAWL_API_KEY=your_key_here
export GEMINI_API_KEY=your_key_here
```

2. Start services:

```bash
docker compose up -d
```

3. Run CLI:

```bash
cd cli
pip install -r requirements.txt
python main.py
```
